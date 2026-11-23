#!/usr/bin/env python3
"""
verify_map.py - prove the map still describes the code.

This is the thing that stops the map becoming a lie. It does not read the map and
nod along; it checks every claim against the filesystem and against git.

Checks
  STRUCTURE   required fields, unique ids, valid group and edge references, enums
  ANCHORS     every source path exists, line ranges are in range, symbols are present
  COVERAGE    every code file under roots is claimed by some node
  DRIFT       files changed since the map's commit, and which nodes they implicate
  LOGIC       loop flows with no exit condition, flow hops with no matching edge,
              orphan nodes, edges with no source anchor
  MECHANICS   no em dashes or en dashes, no implementation jargon in what_it_does

Usage
  python3 verify_map.py                       # uses docs/system-map/system-map.json
  python3 verify_map.py path/to/map.json --repo .
  python3 verify_map.py --strict              # warnings also fail
  python3 verify_map.py --json                # machine-readable, for hooks and CI

Exit codes
  0  clean (warnings allowed unless --strict)
  1  errors found
  2  the map file is missing or unparseable
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".java", ".kt",
            ".cs", ".php", ".ex", ".exs", ".scala", ".swift", ".c", ".cc", ".cpp",
            ".h", ".hpp", ".sql", ".sh", ".mjs", ".cjs", ".vue", ".svelte"}
DEFAULT_IGNORE = ["**/node_modules/**", "**/.git/**", "**/dist/**", "**/build/**",
                  "**/__pycache__/**", "**/.venv/**", "**/venv/**", "**/vendor/**",
                  "**/*.min.js", "**/target/**", "**/.next/**"]
VALID_STATE = {"ok", "partial", "stub", "dead", "not_wired"}
VALID_KIND = {"entrypoint", "process", "store", "queue", "job", "model",
              "external", "config"}
VALID_EDGE = {"data", "control", "async", "conditional", "error"}
JARGON = re.compile(r"(\.py\b|\.ts\b|\.js\b|\.go\b|\.rs\b|/|::|\(\)|_[a-z]+_|"
                    r"\bclass\b|\bfunction\b|\bmodule\b|\bSQL\b|\bAPI\b)")


class Report(object):
    def __init__(self):
        self.errors = []
        self.warns = []
        self.info = {}

    def err(self, code, msg):
        self.errors.append({"code": code, "message": msg})

    def warn(self, code, msg):
        self.warns.append({"code": code, "message": msg})


def git(repo, *args):
    try:
        out = subprocess.run(["git", "-C", repo] + list(args),
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def ignored(rel, patterns):
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch("/" + rel, p)
               for p in patterns)


def under_roots(rel, roots):
    """The map only claims to cover `roots`. Everything else is out of scope, and
    drifting there is not the map's problem."""
    rel = rel.replace(os.sep, "/")
    for r in roots:
        r = r.replace(os.sep, "/")
        while r.startswith("./"):
            r = r[2:]
        r = r.strip("/")
        if r in ("", "."):
            return True
        if rel == r or rel.startswith(r + "/"):
            return True
    return False


# ---------------------------------------------------------------------- structure

def check_structure(m, r):
    for key in ("schema", "repo", "title", "commit", "roots", "nodes", "edges"):
        if key not in m:
            r.err("STRUCT", "missing top-level key: %s" % key)
    if m.get("schema") != "system-map/v1":
        r.err("STRUCT", "schema must be 'system-map/v1'")

    ids, groups = set(), {g["id"] for g in m.get("groups", [])}
    for n in m.get("nodes", []):
        nid = n.get("id", "?")
        if nid in ids:
            r.err("STRUCT", "duplicate node id: %s" % nid)
        ids.add(nid)
        for f in ("id", "label", "group", "kind", "what_it_does",
                  "how_its_built", "state", "source"):
            if not n.get(f):
                r.err("STRUCT", "node %s is missing %s" % (nid, f))
        if n.get("state") not in VALID_STATE:
            r.err("STRUCT", "node %s has invalid state %r" % (nid, n.get("state")))
        if n.get("kind") not in VALID_KIND:
            r.err("STRUCT", "node %s has invalid kind %r" % (nid, n.get("kind")))
        if groups and n.get("group") not in groups:
            r.err("STRUCT", "node %s references unknown group %r" % (nid, n.get("group")))

    for e in m.get("edges", []):
        for side in ("from", "to"):
            if e.get(side) not in ids:
                r.err("STRUCT", "edge %s>%s has unknown %s endpoint"
                      % (e.get("from"), e.get("to"), side))
        if e.get("kind") not in VALID_EDGE:
            r.err("STRUCT", "edge %s>%s has invalid kind %r"
                  % (e.get("from"), e.get("to"), e.get("kind")))
        if not e.get("label"):
            r.warn("STRUCT", "edge %s>%s has no label, so nobody knows what moves along it"
                   % (e.get("from"), e.get("to")))
    return ids


# ------------------------------------------------------------------------ anchors

def check_anchors(m, repo, r):
    charted = set()
    dead = 0
    for n in m.get("nodes", []):
        for s in n.get("source", []):
            p = s.get("path", "")
            full = os.path.join(repo, p)
            if not os.path.isfile(full):
                r.err("ANCHOR", "node %s points at %s, which does not exist" % (n["id"], p))
                dead += 1
                continue
            charted.add(os.path.normpath(p))
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except Exception:
                continue
            total = text.count("\n") + 1
            if s.get("lines"):
                mm = re.match(r"^(\d+)\s*-\s*(\d+)$", str(s["lines"]).strip())
                if not mm:
                    r.warn("ANCHOR", "node %s has malformed line range %r"
                           % (n["id"], s["lines"]))
                elif int(mm.group(2)) > total:
                    r.err("ANCHOR", "node %s claims %s lines %s but the file has %d"
                          % (n["id"], p, s["lines"], total))
            if s.get("symbol") and s["symbol"] not in text:
                r.err("ANCHOR", "node %s claims symbol %r in %s, which is not there"
                      % (n["id"], s["symbol"], p))
    for e in m.get("edges", []):
        for s in e.get("source", []):
            if not os.path.isfile(os.path.join(repo, s.get("path", ""))):
                r.err("ANCHOR", "edge %s>%s points at %s, which does not exist"
                      % (e["from"], e["to"], s.get("path")))
            else:
                charted.add(os.path.normpath(s["path"]))
    r.info["dead_anchors"] = dead
    return charted


# ----------------------------------------------------------------------- coverage

def walk_code(repo, roots, patterns):
    files = []
    for root in roots:
        base = os.path.join(repo, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.normpath(os.path.relpath(full, repo))
                if os.path.splitext(fn)[1].lower() not in CODE_EXT:
                    continue
                if ignored(rel, patterns):
                    continue
                files.append(rel)
    return sorted(files)


def check_coverage(m, repo, charted, r):
    patterns = DEFAULT_IGNORE + list(m.get("ignore", []))
    files = walk_code(repo, m.get("roots", []), patterns)
    if not files:
        r.warn("COVER", "no code files found under roots %r; is 'roots' right?"
               % m.get("roots"))
        return []
    uncharted = [f for f in files if f not in charted]
    pct = 100.0 * (len(files) - len(uncharted)) / len(files)
    r.info["coverage_pct"] = round(pct, 1)
    r.info["files_total"] = len(files)
    r.info["files_uncharted"] = len(uncharted)
    if uncharted:
        r.warn("COVER", "%d of %d code files are not claimed by any node (%.0f%% covered)"
               % (len(uncharted), len(files), pct))
    return uncharted


# -------------------------------------------------------------------------- drift

def warn_uncommitted(m, repo, r):
    """Uncommitted edits to mapped files are invisible to the drift check. Say so."""
    try:
        out = subprocess.run(["git", "-C", repo, "status", "--porcelain", "-z"],
                             capture_output=True, timeout=30)
    except Exception:
        return
    if out.returncode != 0:
        return
    fields = out.stdout.decode("utf-8", errors="replace").split("\0")
    patterns = DEFAULT_IGNORE + list(m.get("ignore", []))
    found = []
    i = 0
    while i < len(fields):
        line = fields[i]
        i += 1
        if len(line) < 4:
            continue
        if "R" in line[:2] or "C" in line[:2]:
            i += 1  # the old path of a rename or copy
        if line.startswith("??"):
            continue
        path = line[3:]
        path = os.path.normpath(path).replace(os.sep, "/")
        if (os.path.splitext(path)[1].lower() in CODE_EXT
                and under_roots(path, m.get("roots", []))
                and not ignored(path, patterns)):
            found.append(path)
    if found:
        r.warn("DRIFT", "%d mapped files have uncommitted changes, which this check cannot "
                        "see: %s. Commit them, then update the map."
               % (len(found), ", ".join(found)))


def check_drift(m, repo, r):
    head = git(repo, "rev-parse", "--short", "HEAD")
    if head is None:
        r.warn("DRIFT", "not a git repo, or git unavailable; drift check skipped")
        return []
    prefix = git(repo, "rev-parse", "--show-prefix")
    if prefix:
        r.err("DRIFT", "--repo is a subfolder (%s) of the git repository, not its top "
                       "level. Run the verifier from the top level; drift cannot be "
                       "checked from a subfolder." % prefix)
        return []
    r.info["head"] = head
    r.info["map_commit"] = m.get("commit")
    warn_uncommitted(m, repo, r)
    if m.get("commit") == head:
        r.info["drift"] = "none"
        return []
    if git(repo, "cat-file", "-e", "%s^{commit}" % m.get("commit", "")) is None:
        r.err("DRIFT", "map commit %r is not in this repo's history; the map cannot be "
                       "trusted" % m.get("commit"))
        return []
    try:
        diff = subprocess.run(["git", "-C", repo, "diff", "--name-only", "-z",
                               "%s..HEAD" % m["commit"]],
                              capture_output=True, timeout=30)
        changed = diff.stdout.decode("utf-8", errors="replace") if diff.returncode == 0 else ""
    except Exception:
        changed = ""
    changed = [os.path.normpath(c) for c in changed.split("\0") if c.strip()]
    changed = [c for c in changed
               if os.path.splitext(c)[1].lower() in CODE_EXT
               and under_roots(c, m.get("roots", []))
               and not ignored(c, DEFAULT_IGNORE + list(m.get("ignore", [])))]
    if not changed:
        r.info["drift"] = "no code changed"
        return []

    owner = {}
    for n in m.get("nodes", []):
        for s in n.get("source", []):
            owner.setdefault(os.path.normpath(s.get("path", "")), []).append(n["id"])

    suspect, orphan = {}, []
    for c in changed:
        if c in owner:
            for nid in owner[c]:
                suspect.setdefault(nid, []).append(c)
        else:
            orphan.append(c)

    r.info["drift"] = "%d code files changed since %s" % (len(changed), m["commit"])
    r.info["suspect_nodes"] = sorted(suspect)
    for nid, fs in sorted(suspect.items()):
        r.err("DRIFT", "node %s is stale: %s changed since the map was written"
              % (nid, ", ".join(fs[:4]) + (" and %d more" % (len(fs) - 4) if len(fs) > 4 else "")))
    for c in orphan:
        r.err("DRIFT", "%s changed and belongs to no node; either map it or add it to ignore" % c)
    return changed


# -------------------------------------------------------------------------- logic

def check_logic(m, ids, r):
    edgeset = {(e.get("from"), e.get("to")) for e in m.get("edges", [])}
    touched = set()
    for e in m.get("edges", []):
        touched.add(e.get("from"))
        touched.add(e.get("to"))
    for nid in sorted(ids - touched):
        r.warn("LOGIC", "node %s has no edges at all; is it really connected, or is it dead?"
               % nid)

    for f in m.get("flows", []):
        path = f.get("path", [])
        for p in path:
            if p not in ids:
                r.err("LOGIC", "flow %s walks through unknown node %r" % (f.get("id"), p))
        for a, b in zip(path, path[1:]):
            if (a, b) not in edgeset:
                r.err("LOGIC", "flow %s hops %s>%s but no such edge exists"
                      % (f.get("id"), a, b))
        if f.get("loop") and not f.get("exit"):
            r.err("LOGIC", "flow %s loops but defines no exit condition; nobody knows when "
                           "it is meant to stop" % f.get("id"))
        if f.get("loop") and len(path) > 1 and path[0] != path[-1]:
            r.warn("LOGIC", "flow %s is marked as a loop but its path does not return to "
                            "its start" % f.get("id"))

    no_src = [(e["from"], e["to"]) for e in m.get("edges", []) if not e.get("source")]
    if no_src:
        r.warn("LOGIC", "%d edges have no source anchor, so they are claims nobody checked: %s"
               % (len(no_src), ", ".join("%s>%s" % t for t in no_src[:6])))

    for st in ("stub", "dead", "not_wired"):
        got = [n["id"] for n in m.get("nodes", []) if n.get("state") == st]
        if got:
            r.info.setdefault("states", {})[st] = got


# ----------------------------------------------------------------------- mechanics

def check_mechanics(m, r):
    def walk(obj, trail):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, trail + "." + str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, "%s[%d]" % (trail, i))
        elif isinstance(obj, str):
            if "\u2014" in obj or "\u2013" in obj:
                r.warn("MECH", "long dash in %s; house style forbids em and en dashes" % trail)

    walk(m, "map")
    for n in m.get("nodes", []):
        w = n.get("what_it_does", "")
        if JARGON.search(w):
            r.warn("MECH", "node %s: what_it_does reads like implementation detail, move it "
                           "to how_its_built" % n.get("id"))
        if len(w.split()) < 6:
            r.warn("MECH", "node %s: what_it_does is too thin to be useful" % n.get("id"))


# ------------------------------------------------------------------------- report

def emit(r, as_json, strict):
    if as_json:
        print(json.dumps({"errors": r.errors, "warnings": r.warns, "info": r.info},
                         indent=2))
    else:
        print("system map verification")
        print("=" * 58)
        for k in ("map_commit", "head", "drift", "coverage_pct", "files_total",
                  "files_uncharted", "dead_anchors"):
            if k in r.info:
                print("  %-16s %s" % (k, r.info[k]))
        if r.info.get("states"):
            for st, ids in r.info["states"].items():
                print("  %-16s %s" % (st, ", ".join(ids)))
        print("")
        for e in r.errors:
            print("  ERROR  [%s] %s" % (e["code"], e["message"]))
        for w in r.warns:
            print("  warn   [%s] %s" % (w["code"], w["message"]))
        print("")
        if r.errors:
            print("FAIL: %d errors, %d warnings. The map no longer describes the code."
                  % (len(r.errors), len(r.warns)))
        elif r.warns and strict:
            print("FAIL (strict): 0 errors, %d warnings." % len(r.warns))
        else:
            print("PASS: %d warnings." % len(r.warns))
    if r.errors or (strict and r.warns):
        return 1
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("map", nargs="?", default=os.environ.get(
        "SYSTEM_MAP", "docs/system-map/system-map.json"))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(a.map):
        print("no system map at %s. Run the cold-start mapping pass first." % a.map,
              file=sys.stderr)
        return 2
    try:
        with open(a.map, "r", encoding="utf-8") as fh:
            m = json.load(fh)
    except Exception as exc:
        print("map is not valid JSON: %s" % exc, file=sys.stderr)
        return 2

    r = Report()
    ids = check_structure(m, r)
    charted = check_anchors(m, a.repo, r)
    check_coverage(m, a.repo, charted, r)
    check_drift(m, a.repo, r)
    check_logic(m, ids, r)
    check_mechanics(m, r)
    return emit(r, a.json, a.strict)


if __name__ == "__main__":
    sys.exit(main())
