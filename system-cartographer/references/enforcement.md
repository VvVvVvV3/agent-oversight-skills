# Enforcement: keeping the map from rotting

The skill contract says the map gets updated. Enforcement is what makes that true on the
day someone is in a hurry. Install at least one of these at cold start, and tell the user
which one and how to remove it.

Where the files live in a mapped repository: `scripts/verify_map.py` and
`scripts/render_map.py`. The Stop hook additionally needs `check_map.sh` and a copy of
`verify_map.py` in `.claude/scripts/`. Every path below and in the hook messages assumes
this layout.
The map, the `scripts/` folder and the hooks belong at the top level of the git
repository, and the verifier fails if `--repo` points at a subfolder of a bigger
repository. Commit the `scripts/` folder, and the workflow file if CI is used, so that a
fresh clone and CI have the verifier.

Every layer below runs the same check: it compares the commit recorded in the map with
HEAD. That means it sees committed drift only. See "What the drift check cannot see".

Pick by who you are defending against:

| Layer | Catches | Cost |
|---|---|---|
| Claude Code `Stop` hook | An agent finishing a session when committed code has drifted from the map. Does not see uncommitted edits | Zero setup for the user, local only |
| `pre-commit` hook | A human committing mapped code while the map is already stale. Lets through the commit that first makes it stale | One command to install, local only |
| CI on pull requests | Committed drift in the branch, wherever the work was done. This is the check that holds | Needs repo write access |

Belt and braces is the Stop hook plus CI. The Stop hook gives the fast feedback loop
during a session; CI is the thing that actually holds.

---

## 1. Claude Code Stop hook

Merge `assets/claude-hook-settings.json` into `.claude/settings.json` in the repo, which
is project scoped and safe to commit. It runs the verifier when an agent tries to finish.
Exit code 2 makes Claude keep working instead of ending the turn, and hands the
verifier's stderr back as the reason, which is everything the agent needs to fix the map
without the user saying a word.

`check_map.sh` is called by the `Stop` and `SubagentStop` hooks and by nothing else; CI
runs `verify_map.py` directly. `assets/claude-hook-settings.json` wires up both hooks.

`Stop` and `SubagentStop` take no `matcher`, so the block is just a `hooks` array.
`timeout` is in seconds.

```jsonc
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/scripts/check_map.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Copy `assets/check_map.sh` to `.claude/scripts/check_map.sh` and
`scripts/verify_map.py` to `.claude/scripts/verify_map.py`. The wrapper exits 0 when
there is no map at all, so the hook is harmless in repos that have not been mapped.

Guard against a loop: the hook must not fire again on the continuation it just caused.
The payload on stdin carries a boolean `stop_hook_active`, true when a Stop hook has
already blocked this turn. The wrapper reads it and stands down, so the agent gets one
clear instruction to fix the map rather than an endless nudge.

---

## 2. pre-commit hook for humans

```bash
cp assets/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

It only complains when the commit touches a file under `roots`. It counts any staged file
under `roots`, code or not, and deletions too; a file moved out of `roots` counts as well.
Commits that touch nothing under `roots` pass straight through, and with `roots` set to `.`
every commit counts. Known limit: a file name containing a double quote, a backslash or a
newline is printed quoted by git and is not counted. It checks whether the map is already stale against
committed code, so it lets through the commit that first makes the map stale and blocks
the next commit that touches mapped code. When it blocks, the stale code is already
committed: update the map for that code, commit the map files on their own, then commit
the change you were making. `git commit --no-verify` is the escape hatch; say so when
installing it, because an unbypassable hook gets deleted rather than obeyed.

For repos already using the `pre-commit` framework, add instead:

```yaml
- repo: local
  hooks:
    - id: system-map
      name: system map is current
      entry: python3 scripts/verify_map.py docs/system-map/system-map.json --repo .
      language: system
      pass_filenames: false
```

---

## 3. CI on pull requests

Copy `assets/github-workflow-system-map.yml` to
`.github/workflows/system-map.yml`. It needs full history, so `fetch-depth: 0` is not
optional: the verifier resolves the map's recorded commit against the repo's history and
will report the map as untrustworthy on a shallow clone.

The workflow also re-renders and fails if the committed HTML or Mermaid differs from
what the JSON produces, which is what stops hand-edited renders.

GitLab equivalent:

```yaml
system-map:
  image: python:3.11
  variables: { GIT_DEPTH: 0 }
  script:
    - python3 scripts/verify_map.py docs/system-map/system-map.json --repo .
```

---

## What the drift check cannot see

The check compares the commit recorded in the map with HEAD. Three consequences.

- It does not see uncommitted edits, staged or not. `verify_map.py` prints a warning that
  names the mapped files with uncommitted changes, but it is a warning and does not fail
  the check. Only `--strict` makes warnings fail, and the hooks do not pass it.
- So the `pre-commit` hook lets through the commit that first makes the map stale, and
  blocks the next commit that touches mapped code. The Stop hook blocks a clean finish
  when committed code has drifted from the map, and does not block on uncommitted edits.
- The warning about uncommitted edits is visible when `verify_map.py` is run directly and
  in CI logs. `check_map.sh` prints nothing when the verifier passes, so the Stop hook
  does not show it.

CI on the pull request is the check that holds.

One more limit, of naming a commit. If a branch is squashed or rebased when it merges,
the commit the map names no longer exists on the main branch, and the verifier reports
that the map commit is not in history. Use merge commits for a mapped repository, or
re-point the map at the squashed commit afterwards.

---

## Tuning the strictness

Default: errors fail, warnings inform. Two dials.

- `--strict` makes warnings fail too. Reasonable once a map is mature; hostile on day
  one, when uncharted files are still normal.
- `ignore` globs in the map itself remove files from coverage. Legitimate for generated
  code, migrations and vendored trees. Not legitimate for "the bit I did not read", and
  widening `ignore` to make CI green is the one move that quietly destroys the value of
  the whole system.

If CI is failing constantly on a fast-moving repo, the fix is a smaller `roots`, not a
disabled check. A map that honestly covers the three subsystems that matter beats a map
that claims the whole repo and is ignored.

---

## Removing it

Tell the user this at install time, in one line, because a check they cannot find how to
remove is a check they will resent:

```bash
rm .git/hooks/pre-commit                       # human hook
rm .github/workflows/system-map.yml            # CI
# and delete the Stop block from .claude/settings.json
```
