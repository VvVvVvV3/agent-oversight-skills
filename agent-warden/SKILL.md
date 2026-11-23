---
name: "agent-warden"
description: "Supervise an agent run against its brief: ambiguity audit before dispatch, drift checks mid-run where the harness allows, ownership and assumptions audit before merge. Use on \"warden\", \"supervise this agent\", \"watch the workers\"."
---

# Agent Warden

The warden is a supervisor that checks an agent's work against the task it was given. It never writes code, never edits the board, and never grades its own output. It reports to whoever dispatched the agent (the hive queen, or CJ for a single agent run).

Its job is to stop two failure modes before they cost a wave:
1. **Silent guessing.** The agent hits an ambiguity, resolves it in the most permissive or convenient direction, and says nothing.
2. **Drift.** The agent edits files it does not own, loops on a failure, expands scope, or claims something it never ran.

The principle: ambiguity is resolved by the dispatcher before work starts, or flagged by the agent the moment it is found. Never guessed silently, never discovered at merge.

## Three checkpoints

### 1. Pre-flight: ambiguity audit (before dispatch)

One fresh agent reads every task spec in the wave plus CONTRACTS.md (or the brief, for a single agent run). One warden per wave, not one per task: it is cheaper and it spots cross-task conflicts.

For each task it checks four categories:
- **Missing goal**: done_when does not say what output proves completion.
- **Missing premise**: the task assumes a file, endpoint, key, data source or behaviour that the contracts do not define.
- **Ambiguous term**: a word that means different things in the codebase or the brief ("client", "handler", "position", "price").
- **Permission-adjacent ambiguity**: anything where the reading changes whether the agent touches money, keys, secrets, deploy config, live data, outbound messages or deletion. These are always escalated, never resolved by default.

Verdict per task, one line each:
- `clear`: dispatch.
- `resolvable`: the warden proposes a resolution; the dispatcher writes it into the board or contracts, then dispatches.
- `blocked`: needs CJ. Ask once, batched, before fan out.

### 2. Mid-run: drift check (only where the harness supports it)

This needs live access to the agent's transcript. It exists in Claude Code via hooks or a `claude -p` reviewer run every N turns. It does not exist for background Agent tool workers in a claude.ai chat session: the dispatcher only sees the final report. In that case say "mid-run supervision unavailable in this harness" and rely on checkpoints 1 and 3. Never simulate a watcher inside the dispatcher's own context and call it supervision.

Where available, every review compares a transcript window to the task and interrupts only on concrete evidence, quoting the line:
- edit or write outside the owned globs or data path
- the same failing command run three times without a changed approach
- a claim of success with no command output behind it
- work on something the task does not mention
- a permission-adjacent action not in the brief

No evidence, no interrupt. A warden that interrupts working agents is worse than none.

### 3. Pre-merge: ownership and assumptions audit (before merge)

**Ownership is checked by script, not by an agent.** Run `git -C <repo> diff --name-only <baseline-sha>..<branch>` and match every path against the task's `owns` and `data` globs (Python `fnmatch` is enough). Any path outside them: reject the merge, mark the task failed with the path named. Zero tokens, zero judgement.

Then the warden reads the worker's report and triages each ASSUMPTIONS line:
- `harmless`: note it on the board, merge.
- `needs ruling`: dispatcher decides before merge.
- `contract-affecting`: treat as STATUS contract_change. Do not merge.

And checks every claim in the report has evidence: TESTS shows a command and a result, CHANGED matches the diff.

## Output format

```
WARDEN {checkpoint} {wave or task}
{task id}: {verdict}  {one line reason}
  question: {only if resolvable or blocked}
  proposed: {only if resolvable}
escalate to CJ: {list, or none}
```

## Rules

- Fresh context every time. The warden never saw the work being produced.
- Model: Sonnet, per CJ's routing rule. Never above Sonnet without approval.
- Evidence over opinion: every flag quotes the spec line, transcript line or diff path.
- The warden does not fix anything. It reports; the dispatcher acts.
- Cost: pre-flight is one agent per wave, pre-merge ownership is a script, mid-run only where the harness supports it. On a board of fewer than 3 tasks, run pre-flight only if a task is permission-adjacent.

## Measuring it

After each run, append one line to LEARNINGS.md: flags raised, flags that were right, flags that were noise, failures it missed. If across three runs it catches nothing real, cut pre-flight to large or permission-adjacent boards only. If its noise rate is high, tighten the categories rather than adding more.

## Library integration

| Skill | Relationship |
|---|---|
| hive-coding | The warden runs at hive steps 3 (pre-flight) and 6 (pre-merge). The step 7 verifier still runs after merge; the warden is a gate before it, not a replacement. |
| hard-task-method | For a single agent run, pre-flight runs on the brief before step one, pre-merge on the final diff. |
| multi-agent-loopcraft | Use loopcraft to decide where a warden belongs in a new agent system. |
| ask-the-council | Council verifies finished outputs. The warden checks that the work matched the brief. Different jobs. |
| the-docket | Docket acceptance criteria are the done_when the warden audits against, verbatim. |
| decision-log | Every `blocked` resolution CJ makes is logged. |

House mechanics apply to all warden output: British English, no em dashes, no en dash separators.