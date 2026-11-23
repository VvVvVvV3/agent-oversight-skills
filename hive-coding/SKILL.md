---
name: "hive-coding"
description: "Run a coding hive on a repo: orchestrator plus parallel worktree agents, shared board, frozen contracts, merge and verify loop. Use on \"hive\", \"swarm this repo\", \"fan out the build\"."
---

# Hive Coding

A hive is one orchestrator (the queen) and a set of worker agents building one codebase in parallel. Workers never coordinate with each other directly. They coordinate through two files the queen owns: the board and the contracts. The hive is a true loop (multi-agent-loopcraft Level 1, with Level 2 fresh context per worker): dispatch, merge, verify, re-queue, until a multi-signal exit is met.

The bottleneck in every hive is integration, not generation. Every rule below exists to make merging boring. The second bottleneck is ambiguity: a worker that guesses silently produces code that merges cleanly and is still wrong. The warden exists for that.

## Gate 0: does this need a hive?

Run before anything else. State the verdict in one line.

Hive only if all four hold:
1. At least three work units that can each be verified alone (own tests, own build target, or a checkable output).
2. The interfaces between units can be written down in advance, one sentence each.
3. Units can be given disjoint file ownership. If two units must edit the same file, they are one unit.
4. A test or build command exists, or can be created first, that judges the whole.

If any fail, run a single agent with hard-task-method and say why. Tightly coupled logic (a core algorithm, a state machine, a refactor through one module) is single agent work. A hive on coupled code produces agents that keep invalidating each other.

## Roles

| Role | Who | Writes code? | Model |
|---|---|---|---|
| Queen | the main session | No feature code. Owns board, contracts, shared files, merges, scaffolding, worktrees | session model |
| Worker | Agent tool, in its own worktree | Yes, only files it owns | sonnet |
| Warden | fresh Agent per wave (agent-warden skill) | No. Audits specs before dispatch and reports before merge | sonnet |
| Verifier | fresh Agent that never saw the work being produced | No. Runs, attacks, reports | sonnet |
| Specialist | a worker with a persona from the-agency | Yes, only files it owns | sonnet |

Model routing is CJ's standing rule: workers, wardens and verifiers on Sonnet by default. Opus only for a genuinely complex unit and only after CJ approves. Fable only on rare occasions, also with approval. If the plan wants anything above Sonnet, ask once, up front, before fan out.

## Shared state

Two files in the repo root, committed on main before fan out.

**HIVE.md** (the board). One block per task:

```
## T03 api: listings endpoint
status: queued | running | review | merged | failed | blocked
owner: worker-3
worktree: ../repo-wt/T03 (branch hive/T03)
owns: src/api/listings/**, tests/api/listings/**
data: data/T03/** (or: reads data/shared/** read-only)
depends: T01
done_when: `npm test -- listings` green; response matches CONTRACTS.md#Listing
warden: clear | resolved: <one line> | blocked
attempts: 0/2
notes:
```

**CONTRACTS.md** (frozen interfaces). Types, endpoint shapes, function signatures, env vars, folder layout, data paths, a glossary of any term the warden flagged as ambiguous, and the commands: install, build, test, lint. Frozen at fan out. Workers may not change it. A worker that needs a contract change stops and returns `CONTRACT_CHANGE` with what and why. The queen decides, edits the contract, and re-dispatches every task that depends on it.

Raw transcripts are never state. The board holds one line per attempt, nothing more.

## The loop

### 1. Scout (ground truth)
Read the repo. Run install, build and the full test suite. Record the baseline on the board: what passes, what already fails, and the baseline commit sha. Pre-existing failures are noted so no worker is blamed for them. If there are no tests, the first task is a test harness, built before any fan out.

### 2. Contracts first
Write CONTRACTS.md. Scaffold shared types and empty modules on main so every worktree starts from the same skeleton. This is the load-bearing step: a vague contract is the most common cause of a failed hive.

### 3. Decompose by ownership, then warden pre-flight
Split by dependency and file ownership, not by topic. Every task gets an `owns` glob and globs never overlap. Shared files (package.json, lockfiles, routers, barrel exports, migration index, CI config) belong to the queen, who applies worker requests to them during merge.

Ownership covers runtime state, not just source. Caches, downloaded data, databases, state files, checkpoints and logs collide just as badly as code. Each task gets its own data path, or reads a shared input that is read-only for the whole wave.

A non-code task (reading terms, researching an API, auditing docs) still owns exactly one output file, such as `notes/T05-terms.md`, so it merges like any other task.

Then dispatch one warden (agent-warden checkpoint 1) over the whole wave: every task spec plus CONTRACTS.md. It returns clear, resolvable or blocked per task, checking missing goals, missing premises, ambiguous terms and permission-adjacent readings. The queen writes every resolution into the board or the contracts glossary before fan out. Blocked items go to CJ in one batched question. A wave of fewer than 3 tasks skips pre-flight unless a task is permission-adjacent.

Large or risky boards go to CJ before fan out: more than 8 tasks, or anything touching auth, payments, live data migrations, secrets or deploy config. Small boards proceed without asking.

### 4. Isolate and probe
Set up isolation before any real work (see Worktrees below). Then dispatch the single lowest-risk task of the wave alone, as a probe. The probe's first action is `git rev-parse --show-toplevel` and `git branch --show-current`, and it reports both. Only when they match the board does the rest of the wave go out. A probe costs one worker. A blind wave can cost five.

### 5. Fan out in waves
Dispatch every task whose dependencies are merged and whose warden line is clear or resolved, in parallel, in one message. Wave cap: 5 workers. Each worker gets the template below and nothing else from the session. Fresh context is the point.

Workers in this harness run in the background and the queen sees only their final report, so there is no live mid-run supervision. Do not pretend otherwise. The worker template's `clarify` status is the substitute: workers are told to stop and ask rather than guess.

### 6. Warden gate, then merge in dependency order
For each returned worker, before any merge:

1. **Ownership gate (script, not agent).** `git -C <repo> diff --name-only <baseline-sha>..hive/<id>`; match every path against the task's `owns` and `data` globs. Any path outside: reject, mark failed with the path named. This is a task failure.
2. **Report check.** BRANCH and TOPLEVEL match the board, CHANGED matches the diff, TESTS shows a real command and result.
3. **Assumptions triage.** If ASSUMPTIONS is not `none`, the warden (checkpoint 3) classifies each line: harmless (note on board, merge), needs ruling (queen decides first), contract-affecting (treat as contract_change, do not merge). Batch all returned workers of a wave into one warden call.

Then merge its branch to main, apply its REQUESTS to shared files, run the full suite. Green: mark merged. Red: revert that merge, mark failed with a one-line cause, carry on with the next. Merge one at a time. Never batch merge and debug the pile.

A worker returning `clarify`: the queen answers from the contracts or asks CJ, writes the answer onto the board, and re-dispatches. A clarify does not consume an attempt.

### 7. Verify
After each wave, dispatch a fresh verifier against main: run everything, push edge cases, check each merged task against its done_when and against CONTRACTS.md, look for duplicated logic and dead code. It ranks findings blocker, degraded, cosmetic. Blockers become new tasks on the board. The warden checks work matched the brief; the verifier checks the merged whole works. Both run.

### 8. Re-queue or re-plan
First classify the failure:

- **Infrastructure failure**: the worker never reached the right repo, branch or tools. Wrong toplevel, missing worktree, tool error before any code ran. These do not consume an attempt. If several tasks in one wave fail the same way at the same time, it is the environment: stop the wave, fix isolation, re-probe, then re-dispatch.
- **Clarification**: the worker returned `clarify`. No attempt consumed. Answer, record, re-dispatch.
- **Task failure**: the worker ran and the work is wrong, or failed the ownership gate. This consumes an attempt, and the re-dispatch needs a changed hypothesis written on the board.

Two failed attempts on one task: stop retrying. Either the queen takes it single agent, or the decomposition was wrong and the affected tasks are re-planned. A retry without a new hypothesis is superstition.

Back to step 5 until exit.

## Exit (all five must hold)

1. Every task merged, or explicitly dropped with CJ's agreement.
2. Full build green and full test suite green against the baseline: no new failures.
3. Lint and typecheck clean, if the repo has them.
4. A final verifier pass returns no blockers.
5. Brief coverage: everything CJ asked for exists, checked line by line.

## Hard caps

Max 4 waves, max 5 workers per wave, max 2 task-failure attempts per task, max 2 clarify rounds per task (a third means the spec is wrong: re-plan it). Hitting any cap escalates to CJ with the board state and the queen's diagnosis, not another wave. Never push to a remote, open a PR, deploy, or run a destructive migration without CJ saying so in chat.

## Worker prompt template

```
You are worker-{n} in a coding hive. Task {id}: {title}.
Your worktree: {abs_worktree_path}. Your branch: {branch}.
First run `git rev-parse --show-toplevel` and `git branch --show-current`.
If either does not match the above, stop and return STATUS: blocked
with what you saw. Do not cd outside your worktree.

Read first: CONTRACTS.md (including the glossary), and the HIVE.md
entry for {id}, including its warden line.
You own ONLY: {owns}. Your data path: {data}. Do not edit or write
any other file or directory. If you need a change outside your
ownership (shared config, router, package.json), list it under
REQUESTS instead of making it.
Contracts are frozen. If one is wrong or missing, stop and return
STATUS: contract_change with what and why.

If you hit an ambiguity where the reading changes what you build,
or whether you touch money, keys, secrets, deploy config, live data
or deletion, stop as soon as you find it and return STATUS: clarify
with the question and the readings you see. Do not guess. Minor
guesses that change nothing outside your files go under ASSUMPTIONS.

Done when: {done_when}. Run {test_cmd} yourself before reporting.
Commit your work on your branch.

Return exactly:
STATUS: done | blocked | contract_change | clarify
TOPLEVEL: <output of git rev-parse --show-toplevel>
BRANCH: <name>
CHANGED: <files>
TESTS: <command run, result>
REQUESTS: <edits needed in files you do not own, or none>
ASSUMPTIONS: <anything you guessed, or none>
QUESTION: <only if STATUS is clarify>
```

## Environment notes

- **Worktrees**: the Agent tool's built-in `isolation: "worktree"` creates the worktree from the session's own working directory. It only works when the repo IS that directory. If the repo sits in a subfolder, or the session root is not a git repo, built-in isolation silently starts workers outside the repo and the whole wave fails together. Default to queen-made worktrees whenever there is any doubt:
  ```
  git -C <repo> worktree add <repo>/../<repo>-wt/T01 -b hive/T01 <baseline-sha>
  ```
  One per task, created from the baseline sha, outside the repo directory so they never appear in the repo's own tree. Pass each worker its absolute path. After exit, `git worktree remove` each one and delete merged `hive/*` branches.
- **Mid-run supervision**: available only in Claude Code (hooks or a `claude -p` reviewer). If running the hive there, agent-warden checkpoint 2 can watch workers live. In a claude.ai chat session it cannot; say so and rely on pre-flight, clarify and the merge gate.
- **No git**: run `git init` and commit a baseline first. If that is not acceptable, fall back to disjoint directories with strict ownership, and say the hive is running without isolation. The ownership gate then compares file lists before and after instead of a git diff.
- **No Agent tool**: there is no hive. Run the same board sequentially with one agent and say so. Never simulate parallel workers inside one context and call it a hive.
- **Cost**: a hive spends several times the tokens of a single agent and earns it only in wall-clock time on wide work. If the widest wave has fewer than 3 tasks, the hive is not paying for itself; say so. The warden adds roughly one Sonnet call per wave at pre-flight and one at pre-merge; the ownership gate is free.

## Pitfalls

- Fanning out before contracts exist: workers invent incompatible shapes.
- Fanning out on unaudited specs: workers resolve the same ambiguous term five different ways.
- Trusting built-in isolation without a probe: five workers, zero in the repo.
- Overlapping ownership: merge conflicts eat the time parallelism saved.
- Shared runtime state: two workers writing one cache or state file corrupt each other quietly.
- Workers editing shared config: the queen owns every shared file.
- Self-graded done: a worker's own test run is a report; the verifier's run against merged main is the result.
- Merging on a green suite without the ownership gate: a stray edit outside `owns` can pass every test.
- Ignoring ASSUMPTIONS: a contract-affecting guess merged as harmless.
- Batch merging: one red suite, five suspects.
- Counting infrastructure failures or clarifications as attempts: burns the cap on problems no worker caused.
- Retrying unchanged: same prompt, same failure.
- Pipeline dressed as a hive: one wave, no verify, no re-queue. That is a fan out and should be called one.

## Reporting to CJ

During the run: the task list only, no narration. Blocked warden items and clarify questions go to CJ immediately, batched. At the end: one line plus the final board. Waves run, tasks merged, final test result, warden flags raised and how many were real, every dropped or blocked task named, and what was not verified. Example: "Hive: 3 waves, 9/9 merged, suite 142/142 green, verifier clean, warden 4 flags (3 real); Stripe webhook untested, no test key available."

Append transferable lessons to LEARNINGS.md (per hard-task-method), including the warden's hit and noise counts. Log material calls (contract changes, scope cuts, dropped tasks, CJ's rulings on blocked items) via decision-log.

## Library integration

| Skill | Relationship |
|---|---|
| agent-warden | Supervision layer. Pre-flight at step 3, merge gate at step 6, live watching only in Claude Code. |
| multi-agent-loopcraft | Designs and audits agent systems. hive-coding runs one specific system on a repo. Use loopcraft to redesign the hive, never to run it. |
| hard-task-method | The single agent fallback when Gate 0 fails, and the source of the LEARNINGS.md rule. |
| the-agency | Personas for specialist workers (security, database, frontend). House rules override personas. |
| ask-the-council | Replaces the step 7 verifier on high stakes builds: client deliverables, anything handling money or personal data. |
| the-docket | Where a task's done_when comes from a docket, the docket's acceptance criteria are copied verbatim, not paraphrased. |
| system-cartographer | If the repo has system-map.json, update it after exit. |
| godmode | Under godmode, Gate 0 is the OODA orient step and the exit list feeds the L99 gate. |
| decision-log | Contract changes, scope cuts, dropped tasks, rulings on blocked items. |

House mechanics apply to everything the hive writes outside code: British English, no em dashes, no en dash separators.