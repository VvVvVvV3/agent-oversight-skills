# Agent oversight skills

Seven Claude skills I use to supervise AI agents doing real work. Each one is a `SKILL.md` file: plain instructions that Claude loads before a task. Two of them ship with code you can run, and that code has tests.

They all deal with the same problem. An agent reporting that a task is finished is a claim, and the claim needs checking by something that did not do the work.

## What is here

| Skill | What it does |
|---|---|
| [agent-warden](agent-warden/SKILL.md) | Supervises an agent run against its brief. It audits every task spec for ambiguity before dispatch, checks for drift mid-run where the harness allows it, and audits file ownership and stated assumptions before anything is merged. The warden never writes code and never grades its own output. |
| [the-docket](the-docket/SKILL.md) | The step between review and fix. Findings are ranked by consequence, the acceptance criterion is written before the fix exists, and verification is aimed at the remedy, not the original fault. Includes a [worked example](the-docket/references/worked-example.md) of a fix that passed every test and was still wrong. |
| [hive-coding](hive-coding/SKILL.md) | One orchestrator and several worker agents building one codebase in parallel. Each worker has its own git worktree and its own files. Interfaces are frozen before work starts, file ownership is checked mechanically before every merge (a git diff matched against the paths each task owns), and a fresh verifier checks the merged result. |
| [graph-engineering](graph-engineering/SKILL.md) | Writes down the shape of an agent system before it is built: which nodes exist, which handoffs are allowed, who owns each step, where a human sits, and when it stops. A verifier is never the producer of what it checks. Ships with a validator and a renderer. |
| [system-cartographer](system-cartographer/SKILL.md) | Keeps a map of what a codebase actually does: each part in plain English, how it is built, and what is currently wrong with it. A verifier checks the map against the files and against git, and fails when committed code has changed and the map has not. Ships with the verifier, a renderer, a pre-commit hook and a CI job. |
| [multi-agent-loopcraft](multi-agent-loopcraft/SKILL.md) | Designs and audits multi-agent loops: whether the work needs more than one agent at all, how agents are selected, what the exit condition is, where the human gate sits, and what the spend cap is. |
| [hard-task-method](hard-task-method/SKILL.md) | The working method under the others: define done before starting, test the load-bearing assumption first, and treat "done" as something observed, not reported. |

## Run the validator

`graph-engineering` includes a structural check for an agent system's spec. It needs Python 3.8 or later and nothing else. On macOS and Linux the command is usually `python3`.

```
python graph-engineering/scripts/validate_graph.py graph-engineering/templates/graph-spec.example.json
```

On the worked example it prints:

```
vestn-daily-intel-brief: 0 errors, 0 warnings, 8 nodes, 11 edges
```

It fails a spec where a verifier reads its own output, where an irreversible action has no human gate upstream, where two nodes write the same state with no merge rule, or where there is no exit condition. To see it fail, edit the example so the verifier lists `verdict` among its inputs and run it again.

To draw the same spec as a Mermaid diagram:

```
python graph-engineering/scripts/render_graph.py graph-engineering/templates/graph-spec.example.json
```

## Run the system map tools

`system-cartographer` includes a renderer and a drift check. Python 3.8 or later, and git for the drift check.

```
python system-cartographer/scripts/render_map.py system-cartographer/templates/system-map.example.json --out out
```

That writes `out/system-map.html`, an explorer you can open in a browser, and `out/system-map.md`, a Mermaid version.

The drift check runs inside a git repository that has a map. Copy `system-cartographer/scripts/verify_map.py` into that repository's `scripts` folder, then run:

```
python scripts/verify_map.py docs/system-map/system-map.json --repo .
```

It passes while the map matches the committed code. Commit a change to a mapped file without updating the map and it fails with a line such as:

```
ERROR  [DRIFT] node A is stale: src/orders.py changed since the map was written
```

You can see that line without writing a map. The drift test below builds a throwaway repository, maps it, drifts it, and prints what the verifier said.

## Run the tests

```
python graph-engineering/tests/test_validator.py
python system-cartographer/tests/test_drift.py
```

The first breaks the worked example in one way at a time and checks the validator's answer against the rules table in `graph-engineering/references/graph-spec.md`: 55 cases. The second builds a small git repository in a temp folder, maps it, and drifts it: 53 cases. They need Python and git. The hook cases also need bash and are skipped without it.

## Known limits

- The drift check sees committed changes only. It compares the commit recorded in the map with HEAD, so it does not see uncommitted edits, though the verifier prints a warning naming any tracked mapped file that has them. The pre-commit hook therefore lets through the commit that makes the map stale and blocks the next one that touches mapped code. CI on the pull request is the check that holds. The drift test asserts this limit alongside the catches. The tests check behaviour, not the wording of these documents.
- The map, the scripts and the hooks belong at the top level of the git repository. Pointed at a subfolder of a bigger repository, the verifier fails and says so.
- The map names a commit. A squash or rebase merge that removes that commit breaks the drift check until the map is pointed at the new one.
- The validator fails an irreversible action that has no human gate upstream. It does not check that every route to that action crosses the gate.
- The validator does not judge wording. It cannot tell that an agent node should have been a plain function. `graph-spec.md` lists what the script checks and what is left to a reader.
- The ownership check in `hive-coding` and `agent-warden` is a procedure, a git diff matched against the paths each task owns. No script for it ships here.
- Not tested in this review: the Stop hook inside a live Claude Code session, the GitHub Actions workflow on a real pull request, and anything on Windows. The tests ran on Linux, on Python 3.8 to 3.13.

These limits were written down on 23 November 2026, when I ran the docket in this repository over the repository itself. An independent reviewer agent tested 90 claims the package made about itself and refuted 10. The fixes and the two test files came out of that review.

## How they fit together

1. Graph engineering writes the spec: nodes, handoffs, owners, gates and stop rules.
2. Loopcraft designs any loop inside it, with an exit condition and a spend cap.
3. The warden audits the task specs before any agent starts.
4. The hive dispatches workers, each in its own worktree.
5. The warden checks ownership and assumptions before each merge.
6. Findings go to the docket, where the acceptance criterion is written before the fix.
7. Verification is aimed at the fix, by an agent that did not produce it.
8. Once the code exists, the system map records what it does, and the drift check stops the map going stale.

## How they were made

I wrote these with Claude, from my own working sessions. I set the rules and supplied the cases, and Claude drafted the files and the code. They refer to other skills in my private library (for example `ask-the-council`, `the-panel` and `decision-log`) which are not published here.

These are my working copies, so they carry my own terms. CJ is me. VvV is my notes vault. VESTN, Vexiom, PCS, Velmure and Mensfortis are my own ventures, used as examples. The model routing rule (Sonnet by default, anything larger only with my approval) is mine. The long `description` at the top of each skill is trigger text: Claude reads it to decide when to load the skill.

## Where I have used them

- A five-reviewer audit of six internal documents on 18 August 2026, which produced 55 findings.
- A multi-agent coding session on a research repository.
- The rollout of three production agents at my renovation business, behind sending guards.

## Author

Craig Jenkinson (CJ), Edinburgh. [linkedin.com/in/craig-jenkinson-b1464827b](https://www.linkedin.com/in/craig-jenkinson-b1464827b)
