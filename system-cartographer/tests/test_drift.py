#!/usr/bin/env python3
"""Checks what verify_map.py and the hooks really catch, in a throwaway git repository.

    python system-cartographer/tests/test_drift.py

It builds a two-file repository in a temp folder, maps it, then drifts it in the ways
the documentation talks about. It asserts the catches, and it asserts the known limit:
the drift check compares the commit recorded in the map with HEAD, so it cannot see
uncommitted edits, and the pre-commit hook lets through the commit that makes the map
stale. If that limit is ever removed, the "known limit" cases fail and the
documentation has to change with them. The tests check behaviour. They do not check
the wording of any document.

Needs Python 3.8 or later and git. The hook cases also need bash and are skipped
without it. Exit 0 if every case passes, 1 if not.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
VERIFY = os.path.join(SKILL, "scripts", "verify_map.py")
RENDER = os.path.join(SKILL, "scripts", "render_map.py")
PRE_COMMIT = os.path.join(SKILL, "assets", "pre-commit")
CHECK_MAP = os.path.join(SKILL, "assets", "check_map.sh")
EXAMPLE = os.path.join(SKILL, "templates", "system-map.example.json")
MAP_REL = "docs/system-map/system-map.json"

RESULTS = []
TEMP_DIRS = []


def record(name, problems, show=None):
    RESULTS.append((name, not problems, "; ".join(problems), show))


def sh(cwd, args, stdin=None, env=None):
    proc = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          input=stdin, env=env)
    text = proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
    return proc.returncode, text


def git(repo, *args):
    code, out = sh(repo, ["git"] + list(args))
    if code != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), out))
    return out.strip()


def write(repo, rel, text):
    path = os.path.join(repo, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def append(repo, rel, text):
    with open(os.path.join(repo, *rel.split("/")), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


BILLING = "src/billing.py"


def the_map(commit, roots, billing=BILLING):
    return {
        "schema": "system-map/v1",
        "repo": "throwaway",
        "title": "Order Taking",
        "subtitle": "a two-file repository built by the test",
        "commit": commit,
        "generated": "2026-01-01",
        "roots": roots,
        "ignore": ["scripts/**"],
        "summary": {
            "what_this_is": "Takes an order from a customer and works out what to charge.",
            "how_to_read": "Two boxes and one arrow.",
        },
        "stats": [],
        "groups": [{"id": "core", "label": "THE WHOLE THING", "order": 1}],
        "nodes": [
            {"id": "A", "label": "ORDER INTAKE", "group": "core", "kind": "entrypoint",
             "what_it_does": "Takes the basket a customer has confirmed and turns it "
                             "into an order that the billing step can charge for.",
             "how_its_built": "One function, take_order, in src/orders.py.",
             "condition": "", "state": "ok",
             "source": [{"path": "src/orders.py", "symbol": "take_order", "lines": "1-2"}]},
            {"id": "B", "label": "BILLING", "group": "core", "kind": "process",
             "what_it_does": "Works out what the customer owes for the order that the "
                             "intake step has just handed over.",
             "how_its_built": "One function, charge, in src/billing.py.",
             "condition": "", "state": "ok",
             "source": [{"path": billing, "symbol": "charge", "lines": "1-2"}]},
        ],
        "edges": [{"from": "A", "to": "B", "label": "the new order", "kind": "data",
                   "source": [{"path": "src/orders.py", "lines": "1-2"}]}],
        "flows": [],
        "unknowns": [],
    }


def write_map(repo, commit, roots, billing=BILLING):
    write(repo, MAP_REL, json.dumps(the_map(commit, roots, billing), indent=2) + "\n")


def build_repo(roots, billing=BILLING):
    """A committed two-file repo with a map that is true at HEAD."""
    repo = tempfile.mkdtemp(prefix="sysmap-test-")
    TEMP_DIRS.append(repo)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "core.autocrlf", "false")
    write(repo, "src/orders.py", "def take_order(basket):\n    return {'items': basket}\n")
    write(repo, billing, "def charge(order):\n    return len(order['items'])\n")
    write(repo, "NOTES.txt", "outside the mapped roots\n")
    write(repo, "tools/helper.py", "def helper():\n    return 1\n")
    os.makedirs(os.path.join(repo, "scripts"))
    shutil.copy(VERIFY, os.path.join(repo, "scripts", "verify_map.py"))
    shutil.copy(RENDER, os.path.join(repo, "scripts", "render_map.py"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "code")
    write_map(repo, git(repo, "rev-parse", "--short", "HEAD"), roots, billing)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "map")
    return repo


def verify(repo, *extra, **kw):
    return sh(repo, [sys.executable, os.path.join("scripts", "verify_map.py"), MAP_REL,
                     "--repo", "."] + list(extra), env=kw.get("env"))


def commit_code_change(repo, rel="src/orders.py", no_verify=True):
    append(repo, rel, "# changed\n")
    git(repo, "add", rel)
    args = ["commit", "-q", "-m", "change code only"]
    if no_verify:
        args.append("--no-verify")
    git(repo, *args)


def expect(name, code, text, want_exit, must_contain=(), must_not_contain=(), show=None):
    problems = []
    if "Traceback" in text:
        problems.append("Python traceback")
    if want_exit is not None and code != want_exit:
        problems.append("exit %d, wanted %d" % (code, want_exit))
    for needle in must_contain:
        if needle.lower() not in text.lower():
            problems.append("output does not mention %r" % needle)
    for needle in must_not_contain:
        if needle.lower() in text.lower():
            problems.append("output mentions %r" % needle)
    shown = None
    if show:
        shown = [l.strip() for l in text.splitlines() if show.lower() in l.lower()]
    record(name, problems, shown)


# ------------------------------------------------------------------- the verifier

def verifier_cases():
    repo = build_repo(["src"])
    code, text = verify(repo)
    expect("a map that matches the code passes", code, text, 0)
    code, text = verify(repo, "--strict")
    expect("and it passes --strict, so the test map carries no warnings of its own",
           code, text, 0)

    commit_code_change(repo)
    code, text = verify(repo)
    expect("a committed change to a mapped file, with no map update, fails as drift",
           code, text, 1, ["[DRIFT] node A is stale", "src/orders.py"], show="[DRIFT]")

    # The documented update procedure: commit the code, point the map at that commit,
    # verify, then commit the map.
    write_map(repo, git(repo, "rev-parse", "--short", "HEAD"), ["src"])
    code, text = verify(repo)
    expect("documented procedure: after the code is committed and the map points at "
           "that commit, the verifier passes", code, text, 0)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "update map", "--no-verify")
    code, text = verify(repo)
    expect("documented procedure: it still passes once the map itself is committed, "
           "which is the state CI sees", code, text, 0)

    append(repo, "src/orders.py", "# edited, not committed\n")
    code, text = verify(repo)
    expect("known limit: an uncommitted edit to a mapped file does not fail the check, "
           "and the verifier says so by name", code, text, 0,
           ["uncommitted", "src/orders.py"])
    code, text = verify(repo, "--strict")
    expect("with --strict the same uncommitted edit does fail", code, text, 1,
           ["uncommitted"])
    git(repo, "add", "src/orders.py")
    code, text = verify(repo)
    expect("known limit: the same holds when the edit is staged", code, text, 0,
           ["uncommitted", "src/orders.py"])

    for roots in (["src/"], ["./src"], ["."], ["src//"], ["././src"]):
        repo = build_repo(roots)
        commit_code_change(repo)
        code, text = verify(repo)
        expect("committed drift is caught when roots is written %r" % roots[0],
               code, text, 1, ["[DRIFT] node A is stale"])

    # A file name with an accent and a space in it. Git quotes such names by default.
    odd = "src/caf\u00e9 billing.py"
    repo = build_repo(["src"], billing=odd)
    commit_code_change(repo, rel=odd)
    code, text = verify(repo)
    expect("committed drift is caught in a file whose name has an accent and a space",
           code, text, 1, ["[DRIFT] node B is stale"])
    code, text = verify(repo, env=dict(os.environ, PYTHONIOENCODING="ascii"))
    expect("and reporting it does not crash a console that cannot encode the name",
           code, text, 1, ["[DRIFT] node B is stale"])
    repo = build_repo(["src"], billing=odd)
    append(repo, odd, "# edited, not committed\n")
    code, text = verify(repo)
    expect("an uncommitted edit to that file is named in the warning", code, text, 0,
           ["uncommitted", "billing.py"])

    repo = build_repo(["src"])
    git(repo, "mv", "src/orders.py", "src/intake.py")
    code, text = verify(repo)
    expect("an uncommitted rename of a mapped file is named by its new path",
           code, text, None, ["uncommitted", "src/intake.py"])

    repo = build_repo(["src"])
    append(repo, "tools/helper.py", "# edited, not committed\n")
    code, text = verify(repo)
    expect("an uncommitted edit outside roots raises no warning", code, text, 0,
           must_not_contain=["uncommitted"])

    # The project sits in a subfolder of a bigger repository. Git reports paths from the
    # top of that repository, so the check cannot work from here and must say so.
    inner = build_repo(["src"])
    outer = tempfile.mkdtemp(prefix="sysmap-outer-")
    TEMP_DIRS.append(outer)
    shutil.copytree(inner, os.path.join(outer, "proj"),
                    ignore=shutil.ignore_patterns(".git"))
    git(outer, "init", "-q")
    git(outer, "config", "user.email", "test@example.invalid")
    git(outer, "config", "user.name", "test")
    git(outer, "config", "commit.gpgsign", "false")
    git(outer, "add", "-A")
    git(outer, "commit", "-q", "-m", "project in a subfolder")
    proj = os.path.join(outer, "proj")
    write_map(proj, git(outer, "rev-parse", "--short", "HEAD"), ["src"])
    git(outer, "add", "-A")
    git(outer, "commit", "-q", "-m", "map")
    append(proj, "src/orders.py", "# changed\n")
    git(outer, "add", "-A")
    git(outer, "commit", "-q", "-m", "change code only")
    code, text = verify(proj)
    expect("run from a subfolder of a bigger repository, the verifier fails and says "
           "why, where it used to pass in silence", code, text, 1, ["top level"])

    repo = build_repo(["src"])
    write(repo, "src/extra.py", "def extra():\n    return 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "new code file, no map update")
    code, text = verify(repo)
    expect("a committed new code file that no node claims fails", code, text, 1,
           ["src/extra.py", "belongs to no node"])


# ---------------------------------------------------------------------- the hooks

def install_pre_commit(repo):
    dst = os.path.join(repo, ".git", "hooks", "pre-commit")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(PRE_COMMIT, dst)
    os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def try_commit(repo, rel):
    append(repo, rel, "# another change\n")
    git(repo, "add", rel)
    return sh(repo, ["git", "commit", "-q", "-m", "attempt"])


def hook_cases():
    for roots in (["src"], ["src/"], ["./src"], ["."], ["src//"], ["././src"]):
        tag = "roots %r" % roots[0]
        repo = build_repo(roots)
        install_pre_commit(repo)
        code, text = try_commit(repo, "src/orders.py")
        expect("known limit, %s: the commit that makes the map stale is not blocked"
               % tag, code, text, 0)
        code, text = try_commit(repo, "src/billing.py")
        expect("pre-commit, %s: the next commit that touches mapped code is blocked"
               % tag, code, text, 1, ["stale"])
        if roots == ["src"]:
            missing = [p for p in sorted(set(re.findall(r"scripts/\w+\.py", text)))
                       if not os.path.isfile(os.path.join(repo, *p.split("/")))]
            problems = ["names %s, which the documented install does not put there" % m
                        for m in missing]
            if "git add docs/system-map" not in text:
                problems.append("does not tell the reader to git add the map files")
            record("pre-commit, %s: every script the blocked message names is installed, "
                   "and it says to add the map files before committing them" % tag, problems)
            git(repo, "reset", "-q", "--hard")
            code, text = try_commit(repo, "NOTES.txt")
            expect("pre-commit, %s: a commit that touches nothing under roots is allowed "
                   "even while the map is stale" % tag, code, text, 0)
            git(repo, "rm", "-q", BILLING)
            code, text = sh(repo, ["git", "commit", "-q", "-m", "delete a mapped file"])
            expect("pre-commit, %s: deleting a mapped file counts as touching mapped code"
                   % tag, code, text, 1, ["stale"])
        if roots == ["."]:
            git(repo, "reset", "-q", "--hard")
            code, text = try_commit(repo, "NOTES.txt")
            expect("pre-commit, %s: with the whole repository as roots, every commit "
                   "counts, a notes file included" % tag, code, text, 1, ["stale"])

    repo = build_repo(["src"])
    install_pre_commit(repo)
    commit_code_change(repo)
    git(repo, "mv", BILLING, "tools/billing.py")
    code, text = sh(repo, ["git", "commit", "-q", "-m", "move a mapped file out of roots"])
    expect("pre-commit: moving a mapped file out of roots counts as touching mapped code",
           code, text, 1, ["stale"])

    odd = "src/caf\u00e9 billing.py"
    repo = build_repo(["src"], billing=odd)
    install_pre_commit(repo)
    commit_code_change(repo)
    code, text = try_commit(repo, odd)
    expect("pre-commit: a staged change to a file with an accent in its name counts",
           code, text, 1, ["stale"])

    # The Stop-hook wrapper, installed where the documentation says.
    repo = build_repo(["src"])
    os.makedirs(os.path.join(repo, ".claude", "scripts"))
    shutil.copy(CHECK_MAP, os.path.join(repo, ".claude", "scripts", "check_map.sh"))
    shutil.copy(VERIFY, os.path.join(repo, ".claude", "scripts", "verify_map.py"))
    wrapper = [shutil.which("bash"), os.path.join(".claude", "scripts", "check_map.sh")]
    code, text = sh(repo, wrapper, stdin=b"{}")
    expect("Stop hook wrapper: exits 0 when the map matches the code", code, text, 0)
    commit_code_change(repo)
    code, text = sh(repo, wrapper, stdin=b"{}")
    expect("Stop hook wrapper: exits 2 when committed code has drifted from the map",
           code, text, 2, ["stale"])
    code, text = sh(repo, wrapper, stdin=b'{"stop_hook_active": true}')
    expect("Stop hook wrapper: stands down when a Stop hook has already blocked the turn",
           code, text, 0)


# ------------------------------------------------------- the example and the renderer

def example_cases():
    with open(EXAMPLE, encoding="utf-8") as fh:
        example = json.load(fh)
    kinds = [n.get("kind") for n in example["nodes"]]
    stats = {s["label"]: s["value"] for s in example.get("stats", [])}
    problems = []
    for label, kind in (("ENTRYPOINTS", "entrypoint"), ("EXTERNAL DEPS", "external")):
        if label in stats and str(stats[label]) != str(kinds.count(kind)):
            problems.append("%s says %s, the map has %d nodes of kind %s"
                            % (label, stats[label], kinds.count(kind), kind))
    record("example map: the header counts match the nodes in the map", problems)

    out = tempfile.mkdtemp(prefix="sysmap-render-")
    TEMP_DIRS.append(out)
    code, text = sh(None, [sys.executable, RENDER, EXAMPLE, "--out", out])
    problems = [] if code == 0 and "Traceback" not in text else ["exit %d" % code]
    for name in ("system-map.html", "system-map.md"):
        if not os.path.isfile(os.path.join(out, name)):
            problems.append("%s was not written" % name)
    record("render_map.py renders the example to HTML and Mermaid", problems)

    for key in ("generated", "summary", "groups"):
        trimmed = dict(example)
        trimmed.pop(key, None)
        path = os.path.join(out, "trimmed-%s.json" % key)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(trimmed, fh)
        code, text = sh(None, [sys.executable, RENDER, path, "--out",
                               os.path.join(out, "trimmed-" + key)])
        record("render_map.py does not crash with a traceback when %r is missing" % key,
               ["Python traceback"] if "Traceback" in text else [])

    for label, body in (("an empty file", ""), ("null", "null"), ("a list", "[]")):
        path = os.path.join(out, "unusable.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        code, text = sh(None, [sys.executable, RENDER, path, "--out",
                               os.path.join(out, "unusable")])
        problems = ["Python traceback"] if "Traceback" in text else []
        if code == 0:
            problems.append("exit 0 for a file it cannot render")
        record("render_map.py fails cleanly on %s" % label, problems)

    broken = []
    no_label = json.loads(json.dumps(example))
    del no_label["nodes"][0]["label"]
    broken.append(("a node with no label", no_label))
    no_to = json.loads(json.dumps(example))
    del no_to["edges"][0]["to"]
    broken.append(("an edge with no end", no_to))
    text_nodes = json.loads(json.dumps(example))
    text_nodes["nodes"] = ["A", "B"]
    broken.append(("nodes that are not objects", text_nodes))
    for label, obj in broken:
        path = os.path.join(out, "broken.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        code, text = sh(None, [sys.executable, RENDER, path, "--out",
                               os.path.join(out, "broken")])
        problems = ["Python traceback"] if "Traceback" in text else []
        if code == 0:
            problems.append("exit 0 for a map it cannot render")
        record("render_map.py fails cleanly on %s" % label, problems)
    code, text = sh(None, [sys.executable, RENDER, os.path.join(out, "no-such-map.json")])
    problems = ["Python traceback"] if "Traceback" in text else []
    if code == 0:
        problems.append("exit 0 for a file that is not there")
    record("render_map.py fails cleanly on a path that does not exist", problems)


def main():
    if shutil.which("git") is None:
        print("SKIPPED: git is not installed, so nothing was tested.")
        return 1
    try:
        verifier_cases()
        if shutil.which("bash"):
            hook_cases()
        else:
            print("note: bash not found, hook cases skipped")
        example_cases()
    finally:
        for d in TEMP_DIRS:
            shutil.rmtree(d, ignore_errors=True)

    failed = 0
    for name, ok, detail, show in RESULTS:
        print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  <- " + detail) if not ok else ""))
        for line in show or []:
            print("        the verifier printed: %s" % line)
        failed += 0 if ok else 1
    print("")
    print("%d cases, %d failed" % (len(RESULTS), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
