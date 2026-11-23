#!/usr/bin/env python3
"""Validate a graph-spec.json against the structural rules in references/graph-spec.md.

Usage: python validate_graph.py path/to/graph-spec.json
Exit 0: no errors (warnings allowed).
Exit 1: at least one error, including a file that cannot be read, is not JSON, is not a
        JSON object, or has a malformed shape. The script never prints a traceback.
Exit 2: wrong usage (not exactly one argument).
"""
import json
import sys
from collections import defaultdict

# Output must never raise on encoding (lone surrogates, consoles that cannot encode).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="backslashreplace")
    except Exception:
        pass

NODE_TYPES = {"agent", "function", "router", "join", "verifier", "gate", "sink", "source"}
MERGE_RULES = {"last-write-wins", "owner-wins", "human-resolves", "reject"}
STEP0_VERDICTS = {"graph", "pipeline", "single-agent"}
TRIGGER_PREFIXES = ("on-complete", "on-approve", "on-reject", "on-condition:", "on-schedule:", "on-event:")
TRIGGER_EXACT = ("on-complete", "on-approve", "on-reject")
TRIGGER_WITH_ARG = ("on-condition:", "on-schedule:", "on-event:")


def trigger_ok(trig):
    if trig in TRIGGER_EXACT:
        return True
    for prefix in TRIGGER_WITH_ARG:
        if trig.startswith(prefix) and trig[len(prefix):].strip():
            return True
    return False


class Malformed(Exception):
    pass


def is_str(x):
    return isinstance(x, str)


def good_merge(x):
    return is_str(x) and x in MERGE_RULES


def name_list(n, key):
    """A node's inputs or outputs: a list of strings, or absent."""
    v = n.get(key, [])
    if not isinstance(v, list) or not all(is_str(x) for x in v):
        raise Malformed("node %s: %r must be a list of strings" % (n.get("id"), key))
    return v


def check(spec, path):
    errors, warnings = [], []
    if not isinstance(spec, dict):
        raise Malformed("top level is not a JSON object")
    raw_nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    if not isinstance(raw_nodes, list) or not all(isinstance(n, dict) for n in raw_nodes):
        raise Malformed("'nodes' must be a list of objects")
    if not isinstance(edges, list) or not all(isinstance(e, dict) for e in edges):
        raise Malformed("'edges' must be a list of objects")

    nodes = {}
    for i, n in enumerate(raw_nodes):
        nid = n.get("id")
        if nid is None or nid == "":
            errors.append(f"node {i}: missing 'id'")
        elif not is_str(nid):
            raise Malformed("node %d: 'id' must be text" % i)
        elif nid in nodes:
            errors.append(f"node {nid}: duplicate id")
        else:
            nodes[nid] = n

    verdict = spec.get("step0_verdict")
    if not (is_str(verdict) and verdict in STEP0_VERDICTS):
        errors.append("step0_verdict missing or not one of graph, pipeline, single-agent: answer 'does this earn a graph' before anything else")

    for i, n in enumerate(raw_nodes):
        nid = n.get("id") if is_str(n.get("id")) and n.get("id") else f"#{i}"
        t = n.get("type")
        if not is_str(t) or t not in NODE_TYPES:
            errors.append(f"node {nid}: type missing or unknown: {t!r}")
        if not n.get("does"):
            errors.append(f"node {nid}: missing 'does' (plain English responsibility)")
        if t == "join" and not good_merge(n.get("merge_rule")):
            errors.append(f"join {nid}: merge_rule missing or invalid")
        if t == "gate" and not n.get("gate_actions"):
            errors.append(f"gate {nid}: gate_actions missing")
        if t == "verifier":
            outs = set(name_list(n, "outputs"))
            ins = set(name_list(n, "inputs"))
            if outs & ins:
                errors.append(f"verifier {nid}: reads its own outputs {sorted(outs & ins)} (self-certification)")

    def ntype(nid):
        t = nodes[nid].get("type")
        return t if is_str(t) else None

    incoming, outgoing = defaultdict(list), defaultdict(list)
    for i, e in enumerate(edges):
        src, dst = e.get("from"), e.get("to")
        if not (is_str(src) and is_str(dst) and src in nodes and dst in nodes):
            errors.append(f"edge {i} ({src} -> {dst}): references a node that does not exist")
            continue
        if not e.get("payload"):
            errors.append(f"edge {src} -> {dst}: payload missing")
        trig = e.get("trigger", "")
        if not is_str(trig) or not trigger_ok(trig):
            errors.append(f"edge {src} -> {dst}: trigger missing or not one of {TRIGGER_PREFIXES}")
        if "owner" in e and not (is_str(e["owner"]) and e["owner"] in nodes):
            errors.append(f"edge {src} -> {dst}: owner {e['owner']!r} is not a node id")
        incoming[dst].append(src)
        outgoing[src].append(dst)
        if ntype(dst) == "verifier" and src == dst:
            errors.append(f"verifier {dst}: edge from itself")

    for nid in nodes:
        t = ntype(nid)
        if t != "source" and not incoming[nid]:
            errors.append(f"node {nid}: no incoming edge (orphan, nobody hands it work)")
        if t not in {"sink", "gate"} and not outgoing[nid]:
            errors.append(f"node {nid}: no outgoing edge (its output goes nowhere)")
        if t == "gate" and not outgoing[nid]:
            warnings.append(f"gate {nid}: no outgoing edge; a terminal gate is unusual")
        if t == "router" and len(outgoing[nid]) < 2:
            warnings.append(f"router {nid}: fewer than two outgoing edges, not really a router")

    # Verifier independence: a verifier must not be the sole producer of what it verifies
    producers = defaultdict(set)
    for nid, n in nodes.items():
        for k in name_list(n, "outputs"):
            producers[k].add(nid)
    for nid, n in nodes.items():
        if ntype(nid) == "verifier":
            for k in name_list(n, "inputs"):
                if producers.get(k) == {nid}:
                    errors.append(f"verifier {nid}: sole producer of its own input {k}")

    # Irreversible sinks need a gate upstream on some path
    def has_gate_upstream(target, seen=None):
        seen = seen or set()
        for src in incoming[target]:
            if src in seen:
                continue
            seen.add(src)
            if nodes[src].get("type") == "gate" or has_gate_upstream(src, seen):
                return True
        return False

    for nid, n in nodes.items():
        if ntype(nid) == "sink" and n.get("irreversible") is True:
            if not has_gate_upstream(nid) and not n.get("gate_reason_absent"):
                errors.append(f"sink {nid}: irreversible with no gate upstream and no gate_reason_absent")

    # State merge rules
    state = spec.get("state", {})
    if not isinstance(state, dict):
        raise Malformed("'state' must be an object")
    keys = state.get("keys", {})
    if not isinstance(keys, dict):
        raise Malformed("'state.keys' must be an object")
    for k, meta in keys.items():
        if not isinstance(meta, dict):
            raise Malformed("state key %s must be an object" % k)
        writers = meta.get("written_by", [])
        if not isinstance(writers, list):
            raise Malformed("state key %s: 'written_by' must be a list" % k)
        if len(writers) > 1 and not good_merge(meta.get("merge_rule")):
            errors.append(f"state key {k}: {len(writers)} writers and no valid merge_rule")
        for w in writers:
            if not (is_str(w) and w in nodes):
                errors.append(f"state key {k}: writer {w} is not a node")

    # Stop rules
    sr = spec.get("stop_rules", {})
    if not isinstance(sr, dict):
        raise Malformed("'stop_rules' must be an object")
    ec = sr.get("exit_condition")
    if not ec:
        errors.append("stop_rules.exit_condition missing")
    elif not is_str(ec):
        errors.append("stop_rules.exit_condition must be text")
    elif "score" in ec.lower() and " and " not in ec.lower():
        warnings.append("exit_condition appears to be a single score; multi-signal exits are safer")
    for key in ("max_spend", "timeout"):
        if not sr.get(key):
            warnings.append(f"stop_rules.{key} missing")

    # Oversight layer
    if not any(ntype(nid) == "gate" for nid in nodes) and not spec.get("gate_reason_absent"):
        errors.append("no gate node and no top-level gate_reason_absent: every system has an oversight layer")

    if not spec.get("feedback_layers"):
        warnings.append("feedback_layers block missing; declare gaps rather than leaving them undeclared")

    agent_count = sum(1 for nid in nodes if ntype(nid) == "agent")
    if agent_count > 8:
        warnings.append(f"{agent_count} agent nodes; revisit Step 0")

    return errors, warnings, len(nodes), len(edges), spec.get("name", path)


def main(path):
    try:
        with open(path, encoding="utf-8") as f:
            spec = json.load(f)
    except Exception as exc:
        print(f"ERROR cannot read {path} as JSON: {exc}")
        return 1
    try:
        errors, warnings, n_nodes, n_edges, name = check(spec, path)
    except Exception as exc:
        print(f"ERROR spec is malformed: {exc}")
        return 1
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{name}: {len(errors)} errors, {len(warnings)} warnings, {n_nodes} nodes, {n_edges} edges")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
