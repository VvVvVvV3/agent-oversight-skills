#!/usr/bin/env python3
"""Checks that validate_graph.py does what references/graph-spec.md says it does.

    python graph-engineering/tests/test_validator.py

Each case breaks the worked example in one way and states what the validator must do
with it. The expectations come from the rules table in graph-spec.md, not from the
script, so a rule that is documented and not enforced shows up here as a failure.

Needs Python 3.8 or later and nothing else. Exit 0 if every case passes, 1 if not.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
VALIDATE = os.path.join(SKILL, "scripts", "validate_graph.py")
RENDER = os.path.join(SKILL, "scripts", "render_graph.py")
EXAMPLE = os.path.join(SKILL, "templates", "graph-spec.example.json")

with open(EXAMPLE, encoding="utf-8") as fh:
    BASE = json.load(fh)

RESULTS = []


def run(script, path, env=None):
    proc = subprocess.run([sys.executable, script, path], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env)
    text = proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
    return proc.returncode, text


def write_tmp(obj=None, text=None):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        if text is not None:
            fh.write(text)
        else:
            json.dump(obj, fh, ensure_ascii=False)
    return path


def record(name, problems):
    RESULTS.append((name, not problems, "; ".join(problems)))


def judge(text, code, want_exit, level, keyword, absent):
    problems = []
    if "Traceback" in text:
        problems.append("Python traceback instead of a message")
    if want_exit is not None and code != want_exit:
        problems.append("exit %d, wanted %d" % (code, want_exit))
    lines = text.splitlines()
    if level:
        hit = [l for l in lines if l.startswith(level) and keyword.lower() in l.lower()]
        if not hit:
            problems.append("no %s line mentioning %r" % (level, keyword))
    if absent:
        bad = [l for l in lines if l.startswith("ERROR") and absent.lower() in l.lower()]
        if bad:
            problems.append("unexpected line: " + bad[0])
    return problems


def case(name, mutate, want_exit, level=None, keyword=None, absent=None):
    """Break a copy of the example with `mutate`, run the validator, judge the result."""
    spec = copy.deepcopy(BASE)
    out = mutate(spec)
    spec = spec if out is None else out
    path = write_tmp(spec)
    try:
        code, text = run(VALIDATE, path)
    finally:
        os.remove(path)
    record(name, judge(text, code, want_exit, level, keyword, absent))


def raw_case(name, text, want_exit):
    """Feed the validator a file that is not a usable spec at all."""
    path = write_tmp(text=text)
    try:
        code, out = run(VALIDATE, path)
    finally:
        os.remove(path)
    record(name, judge(out, code, want_exit, None, None, None))


def node(spec, nid):
    return next(n for n in spec["nodes"] if n.get("id") == nid)


def drop_edges(spec, pred):
    spec["edges"] = [e for e in spec["edges"] if not pred(e)]


def edge(src, dst, payload="x", trigger="on-complete", **extra):
    e = {"from": src, "to": dst, "payload": payload, "trigger": trigger}
    e.update(extra)
    return e


# ------------------------------------------------------------------ the example itself

def example_checks():
    code, text = run(VALIDATE, EXAMPLE)
    want = "%s: 0 errors, 0 warnings, %d nodes, %d edges" % (
        BASE["name"], len(BASE["nodes"]), len(BASE["edges"]))
    problems = []
    if code != 0:
        problems.append("exit %d, wanted 0" % code)
    if want not in text:
        problems.append("summary line is not %r" % want)
    record("the worked example passes with no errors and no warnings", problems)

    # The gate's own description says briefs with nothing flagged pass on verifier
    # acceptance, and the exit condition says "no FLAG items OR cj-gate approves".
    # That needs a route from the verifier to the sink that does not cross the gate.
    reach, frontier = set(), ["verify-brief"]
    while frontier:
        here = frontier.pop()
        for e in BASE["edges"]:
            if e["from"] == here and e["to"] != "cj-gate" and e["to"] not in reach:
                reach.add(e["to"])
                frontier.append(e["to"])
    record("example: an unflagged brief can reach the sink without crossing the gate, "
           "as the gate's description and the exit condition say",
           [] if "write-vault" in reach else ["no route from verify-brief to write-vault "
                                              "that avoids cj-gate"])

    versions = [c.get("version") for c in BASE.get("changelog", [])]
    record("example: the spec version has a changelog entry (its own rule)",
           [] if BASE.get("version") in versions and BASE.get("version") == max(versions)
           else ["version %r, changelog versions %r" % (BASE.get("version"), versions)])

    code, text = run(RENDER, EXAMPLE)
    problems = []
    if code != 0 or "Traceback" in text:
        problems.append("renderer exit %d" % code)
    if "flowchart" not in text:
        problems.append("no Mermaid flowchart in the output")
    missing = [n["id"] for n in BASE["nodes"] if n["id"] not in text]
    if missing:
        problems.append("nodes missing from the render: %s" % ", ".join(missing))
    record("render_graph.py draws every node of the example", problems)


# --------------------------------------------------------------- rules that must fail

def m_missing_id(s):
    del node(s, "classify")["id"]


def m_duplicate_id(s):
    s["nodes"].append(copy.deepcopy(node(s, "classify")))


def m_missing_type(s):
    del node(s, "classify")["type"]


def m_unknown_type(s):
    node(s, "classify")["type"] = "wizard"


def m_missing_does(s):
    del node(s, "classify")["does"]


def m_join_no_merge(s):
    node(s, "dedupe")["type"] = "join"


def m_gate_no_actions(s):
    del node(s, "cj-gate")["gate_actions"]


def m_verifier_reads_own_output(s):
    node(s, "verify-brief")["inputs"].append("verdict")


def m_verifier_self_edge(s):
    s["edges"].append(edge("verify-brief", "verify-brief", "verdict"))


def m_edge_unknown_node(s):
    s["edges"].append(edge("classify", "nowhere"))


def m_edge_no_payload(s):
    del s["edges"][2]["payload"]


def m_edge_bad_trigger(s):
    s["edges"][2]["trigger"] = "whenever"


def m_edge_trigger_lookalike(s):
    s["edges"][2]["trigger"] = "on-completely"


def m_edge_trigger_empty_condition(s):
    s["edges"][2]["trigger"] = "on-condition:"


def m_edge_owner_unknown(s):
    s["edges"][2]["owner"] = "nobody"


def m_edge_owner_known(s):
    s["edges"][2]["owner"] = "dedupe"


def m_no_incoming(s):
    drop_edges(s, lambda e: e["to"] == "classify")


def m_no_outgoing(s):
    drop_edges(s, lambda e: e["from"] == "classify")


def ensure_direct_route(s):
    if not any(e["from"] == "verify-brief" and e["to"] == "write-vault" for e in s["edges"]):
        s["edges"].append(edge("verify-brief", "write-vault", "draft",
                               "on-condition:verdict.accepted"))
        node(s, "write-vault")["inputs"] = ["approved_draft", "draft"]


def m_irreversible_gate_on_some_path(s):
    ensure_direct_route(s)
    node(s, "write-vault")["irreversible"] = True


def m_irreversible_no_gate(s):
    ensure_direct_route(s)
    node(s, "write-vault")["irreversible"] = True
    drop_edges(s, lambda e: e["from"] == "cj-gate")


def m_irreversible_no_gate_with_reason(s):
    m_irreversible_no_gate(s)
    node(s, "write-vault")["gate_reason_absent"] = "overwritten on the next run"


def m_two_writers(s):
    s["state"]["keys"]["draft"]["written_by"].append("classify")


def m_two_writers_with_rule(s):
    m_two_writers(s)
    s["state"]["keys"]["draft"]["merge_rule"] = "owner-wins"


def m_writer_not_a_node(s):
    s["state"]["keys"]["draft"]["written_by"] = ["ghost"]


def m_no_exit_condition(s):
    del s["stop_rules"]["exit_condition"]


def m_no_step0(s):
    del s["step0_verdict"]


def m_bad_step0(s):
    s["step0_verdict"] = "banana"


def m_no_gate(s):
    ensure_direct_route(s)
    s["nodes"] = [n for n in s["nodes"] if n["id"] != "cj-gate"]
    drop_edges(s, lambda e: "cj-gate" in (e["from"], e["to"]))
    s["state"]["keys"].pop("approved_draft", None)
    node(s, "write-vault")["inputs"] = ["draft"]
    s["stop_rules"]["on_breach"] = "halt"


def m_no_gate_with_reason(s):
    m_no_gate(s)
    s["gate_reason_absent"] = "single reader, reversible output"


def m_nodes_hold_a_number(s):
    s["nodes"].append(7)


def m_edges_hold_a_number(s):
    s["edges"].append(7)


# ------------------------------------------------------- rules that must only warn

def m_router_one_exit(s):
    node(s, "classify")["type"] = "router"


def m_single_score_exit(s):
    s["stop_rules"]["exit_condition"] = "score above 8"


def m_no_max_spend(s):
    del s["stop_rules"]["max_spend"]


def m_no_timeout(s):
    del s["stop_rules"]["timeout"]


def m_no_feedback_layers(s):
    del s["feedback_layers"]


def m_nine_agents(s):
    for i in range(7):
        nid = "extra-agent-%d" % i
        s["nodes"].append({"id": nid, "type": "agent", "does": "Scores one more signal.",
                           "inputs": ["scored_items"], "outputs": ["extra_%d" % i]})
        s["edges"].append(edge("classify", nid, "scored_items"))
        s["edges"].append(edge(nid, "draft-brief", "extra_%d" % i))


def m_gate_no_exit(s):
    drop_edges(s, lambda e: e["from"] == "cj-gate")


def main():
    example_checks()

    E, W = "ERROR", "WARN"
    case("a node with no id fails", m_missing_id, 1, E, "missing 'id'")
    case("two nodes with the same id fail", m_duplicate_id, 1, E, "duplicate")
    case("a node with no type fails, with a message", m_missing_type, 1, E, "type")
    case("a node with an unknown type fails", m_unknown_type, 1, E, "type")
    case("a node with no 'does' fails", m_missing_does, 1, E, "'does'")
    case("a join with no merge_rule fails", m_join_no_merge, 1, E, "merge_rule")
    case("a gate with no gate_actions fails", m_gate_no_actions, 1, E, "gate_actions")
    case("a verifier that reads its own output fails", m_verifier_reads_own_output, 1, E,
         "verifier")
    case("an edge from a verifier to itself fails", m_verifier_self_edge, 1, E, "itself")
    case("an edge to a node that does not exist fails", m_edge_unknown_node, 1, E,
         "does not exist")
    case("an edge with no payload fails", m_edge_no_payload, 1, E, "payload")
    case("an edge with an unknown trigger fails", m_edge_bad_trigger, 1, E, "trigger")
    case("a trigger that only starts like a known one fails", m_edge_trigger_lookalike, 1,
         E, "trigger")
    case("a conditional trigger with no condition after the colon fails",
         m_edge_trigger_empty_condition, 1, E, "trigger")
    case("an edge whose owner is not a node fails", m_edge_owner_unknown, 1, E, "owner")
    case("an edge whose owner is a node passes", m_edge_owner_known, 0)
    case("a node nobody hands work to fails", m_no_incoming, 1, E, "no incoming")
    case("a node whose output goes nowhere fails", m_no_outgoing, 1, E, "no outgoing")
    case("an irreversible sink with no gate upstream fails", m_irreversible_no_gate, 1, E,
         "irreversible")
    case("the same sink passes that rule once gate_reason_absent is given",
         m_irreversible_no_gate_with_reason, 0, absent="irreversible")
    case("known limit: an irreversible sink passes when a gate sits on some path to it, "
         "even though another path goes round the gate",
         m_irreversible_gate_on_some_path, 0)
    case("a state key with two writers and no merge_rule fails", m_two_writers, 1, E,
         "merge_rule")
    case("the same key passes once it declares a merge_rule", m_two_writers_with_rule, 0)
    case("a state key written by something that is not a node fails", m_writer_not_a_node,
         1, E, "not a node")
    case("a spec with no exit condition fails", m_no_exit_condition, 1, E,
         "exit_condition")
    case("a spec with no step0_verdict fails", m_no_step0, 1, E, "step0_verdict")
    case("a step0_verdict outside the three allowed values fails", m_bad_step0, 1, E,
         "step0_verdict")
    case("a spec with no gate and no reason for its absence fails", m_no_gate, 1, E,
         "gate")
    case("the same spec passes once gate_reason_absent is given", m_no_gate_with_reason, 0)
    case("a nodes list holding something that is not a node fails cleanly",
         m_nodes_hold_a_number, 1)
    case("an edges list holding something that is not an edge fails cleanly",
         m_edges_hold_a_number, 1)

    raw_case("a file that is not JSON fails cleanly", "{not json", 1)
    raw_case("a JSON file that is a list, not a spec, fails cleanly", "[]", 1)
    code, text = run(VALIDATE, os.path.join(tempfile.gettempdir(), "no-such-spec-file.json"))
    record("a path that does not exist fails cleanly",
           judge(text, code, 1, None, None, None))

    case("a router with one way out warns and still passes", m_router_one_exit, 0, W,
         "router")
    case("an exit condition that is a single score warns and still passes",
         m_single_score_exit, 0, W, "score")
    case("a missing spend cap warns and still passes", m_no_max_spend, 0, W, "max_spend")
    case("a missing timeout warns and still passes", m_no_timeout, 0, W, "timeout")
    case("a missing feedback_layers block warns and still passes", m_no_feedback_layers,
         0, W, "feedback_layers")
    case("more than eight agents warns and still passes", m_nine_agents, 0, W,
         "agent nodes")
    case("a gate with no way out warns", m_gate_no_exit, None, W, "gate")

    # Windows and some servers do not default to UTF-8. A spec with a pound sign or an
    # accent in it must still load.
    spec = copy.deepcopy(BASE)
    spec["purpose"] = "Costs \u00a32 a run. Caf\u00e9 test."
    path = write_tmp(spec)
    env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
    try:
        for label, script in (("validate_graph.py", VALIDATE), ("render_graph.py", RENDER)):
            code, text = run(script, path, env)
            record("%s reads a UTF-8 spec when the system default is not UTF-8" % label,
                   judge(text, code, 0, None, None, None))
    finally:
        os.remove(path)

    # A console that cannot encode a character must not crash either script.
    spec = copy.deepcopy(BASE)
    spec["name"] = "caf\u00e9-brief"
    path = write_tmp(spec)
    env = dict(os.environ, PYTHONIOENCODING="ascii")
    try:
        for label, script in (("validate_graph.py", VALIDATE), ("render_graph.py", RENDER)):
            code, text = run(script, path, env)
            record("%s does not crash when the console cannot encode a character" % label,
                   judge(text, code, 0, None, None, None))
    finally:
        os.remove(path)

    # The renderer is meant to run after the validator, but it must still fail cleanly.
    for label, text in (("an empty file", ""), ("null", "null"), ("a list", "[]"),
                        ("nodes that are not a list", '{"nodes": "x"}'),
                        ("a node with nothing in it", '{"nodes": [{}]}')):
        path = write_tmp(text=text)
        try:
            code, out = run(RENDER, path)
        finally:
            os.remove(path)
        problems = judge(out, code, 1, None, None, None)
        if not any(l.startswith("ERROR") for l in out.splitlines()):
            problems.append("no ERROR line")
        record("render_graph.py fails cleanly on %s" % label, problems)

    code, out = run(RENDER, os.path.join(tempfile.gettempdir(), "no-such-spec-file.json"))
    problems = judge(out, code, 1, None, None, None)
    if not any(l.startswith("ERROR") and "cannot read" in l for l in out.splitlines()):
        problems.append("no ERROR line saying the file cannot be read")
    record("render_graph.py says a missing file cannot be read, not that it is a bad spec",
           problems)

    width = max(len(n) for n, _, _ in RESULTS)
    failed = 0
    for name, ok, detail in RESULTS:
        print("%s  %s%s" % ("PASS" if ok else "FAIL", name.ljust(width) if not ok else name,
                            ("  <- " + detail) if not ok else ""))
        failed += 0 if ok else 1
    print("")
    print("%d cases, %d failed" % (len(RESULTS), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
