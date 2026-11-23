---
name: the-docket
description: "The step between review and fix: rank findings by consequence, write what actually fixed would look like before the fix exists, test the artefact's own claims, and aim verification at the remedy, not the fault. Use after the-panel, ask-the-council, a guard skill, web-qa, a code review or any list of problems, and on docket this, open the docket, triage these findings, is this actually fixed, panel then docket then council."
---

# The Docket

A docket is an ordered list of matters, each with an owner and a disposition, and none of them leaves the list without one. That is what this skill is.

The panel produces. The council verifies. Between them sits the decision about what gets fixed, what "fixed" means, and how anyone will know. Without that middle, a review pipeline reliably certifies remedies that make the symptom disappear while leaving the defect in place.

---

## Why this exists, and the evidence for it

A real sequence, on a real repository, in one session:

1. The panel found that seven of twelve integrity checks in a console passed a literal `false` as their break condition. They could never go red, while the page claimed they were verified.
2. The fix rewrote every check to compare two values. A headless verifier drove all twelve faults and asserted each turned its own check red. The verifier was itself mutation tested and proven able to fail.
3. Everything was green. It was ready to ship.
4. The council, pointed at the **remedy** rather than the artefact, found the remedy was cosmetic. The second side of every check was the first side perturbed by the selected fault. One number compared to itself. A check could be turned red on command and could not be turned red by reality. One check's break condition was literally the state of a dropdown.

Nothing in the panel or the council was at fault. The gap was that no one wrote down, before the fix existed, what observable evidence would prove the finding closed. "All twelve can go red" was satisfiable by theatre. "A check goes red because the data diverged, with no control set" was not, and it was never written.

That is the whole argument for this skill.

---

## Position in the pipeline

| Stage | Skill | Question it answers |
|---|---|---|
| Staff | `the-agency` | Who should look at this? |
| Generate | `the-panel` | What is wrong, from angles a linear pass would miss? |
| **Decide** | **`the-docket`** | **Which of those matter, what would closure look like, and did we get it?** |
| Verify | `ask-the-council` | Does the remedy survive attack? |

`panel then docket then council` is the full sequence. The docket is what makes the council's aim correct, which is the difference between the council stopping a bad fix and rubber stamping one.

---

## Activation

| Trigger | Behaviour |
|---|---|
| "docket this" / "open the docket" | Run the full protocol on the findings at hand |
| "panel then docket then council" | Full pipeline, findings routed through triage and criteria before verification |
| "is this actually fixed" | Run steps 4 and 5 only, against an existing remedy |
| "claim sweep" | Run step 3 only, against an artefact |
| "close the docket" | Force every open item to a disposition and report it |
| "docket off" | Deactivate |

Session scope: once open, the docket stays open. Findings accumulate to it until closed.

---

## The protocol, six moves

### 1. Intake and dedup

Collect every finding from every source into one list. Merge duplicates. Where two reviewers disagree, **record the disagreement as an item**, do not average it. Surfaced tension is signal; a blended verdict is noise wearing a suit.

Findings arrive with a claimed severity. Ignore it for now. An agent writing CRITICAL has made a claim, not a ranking.

### 2. Rank by consequence, not by tone

Score each item on what it actually costs, in this order:

1. **Misleads a decision maker.** A wrong number, or a true number presented so it reads as something else. Highest, always. A defect that produces a confident false impression outranks one that produces an obvious break.
2. **Cannot be detected by the people who own it.** A silent failure outranks a loud one of the same size.
3. **Costs a developer days.** Something that will be discovered painfully on day three of handover.
4. **Costs a reader trust.** Broken layout, contradicted claim, unexplained jargon.
5. **Costs polish.** Everything else.

Anything at 1 or 2 is a blocker. Say the word "blocker" and mean it, or the ranking is decoration.

### 3. The self-claim sweep

**The highest yield move in this skill.** Extract every assertion the artefact makes about itself and turn each into a testable proposition.

Look in: on-screen copy, headings and subheadings, tooltips, `alt` and `aria-label` text, code comments, README and handover documents, commit messages, and anything of the form "verified", "tested", "every", "always", "never", "each", "all N".

For each, write the observation that would prove or refute it, then run it.

A false self-claim is worse than a missing feature, because a missing feature is visible and a false claim actively spends the reader's trust. In the worked example, three of the highest severity items in the whole review were self-claims: a register that said "each declaring two distinct source systems" when six did not, an image label calling a side panel "the accessible equivalent" when that panel could not be operated by keyboard, and a handover document crediting a pre-commit hook with a guarantee its own engineering notes said it could not provide.

Claims of the form "we already checked X" deserve special attention. In the same review, a stylesheet comment recorded a clipping bug found and fixed at one viewport width; the identical bug was live two rules below at a different width, never checked, because the comment made it feel handled.

### 4. Write the acceptance criterion before the remedy

For every docketed item, before any fix is attempted, write what observable evidence would prove it closed.

The criterion must:

* **Describe an observation, not a code change.** "R1 compares two records" is a code change. "Mutating the estate record with no fault selected turns R1 red" is an observation. Only the second can be run.
* **Be falsifiable.** If you cannot describe the state of the world in which the criterion fails, it is not a criterion.
* **Survive the theatre test.**

> **The theatre test.** Can this criterion be satisfied by making the symptom disappear without changing the underlying property? If yes, it is the wrong criterion. Rewrite it.

Apply the test literally. In the worked example, "all twelve checks can go red" passes with a dropdown wired straight to the break condition. "A check goes red because the two sides disagree, with no control set" does not. Same defect, two criteria, and only one of them would have caught the cosmetic fix.

Where the honest criterion cannot be met, that is a finding in itself. Six of the twelve checks tracked figures that no second record could follow, so no criterion could make them genuinely two sided in that artefact. The correct disposition was not to fake it and not to drop it, but to **label them on screen as what they are** and record why. Truthful labelling is a legitimate closure. Quiet deletion is not.

### 5. Point the verification at the remedy

Hand the verifier three things: the finding, the acceptance criterion, and the fix. Instruct it explicitly:

> Attack the fix, not the original fault. Does this close the finding, or does it make the symptom go away? If the fix introduces a test, is the test independent of the implementation, or was it written from the code it checks and therefore true by construction?

That last question earns its place. A test whose expectations were copied out of the implementation agrees with it by definition and can never catch a divergence between what the code does and what the artefact claims. Write test expectations from the **stated behaviour**, not from the source. In the worked example, rewriting a dependency table from the labels shown on screen rather than from the arrays in the code immediately exposed a check declaring a dependency it did not have.

And before trusting any new gate: **prove the gate falsifiable.** Reintroduce the original defect, run the gate, watch it fail, restore. A gate you have never seen fail is worth exactly as much as a check you have never seen red.

### 6. Disposition, for every item

Each item ends in exactly one of three states, and none of them is silence:

* **CLOSED**, with the evidence attached. Not "fixed". The command that was run and what it printed.
* **OPEN**, with a named owner, a reason, and where it is recorded so it survives this session. An open item with no owner is a closed item pretending.
* **REJECTED**, with the argument. Reviewers are wrong sometimes and saying so is part of the job.

**A finding that disappears between review and delivery is the failure this step exists to prevent.** Count the items in and count them out. If the numbers differ, something was dropped, and dropping is a decision that must be visible.

---

## Standing rules

Four, earned rather than asserted.

**Reddening on command is not reconciling.** Generalised: a remedy that satisfies only the test written for it has not been verified, it has been fitted. The gate must be independent of the thing it gates.

**A rule with no executable gate decays back to whatever is convenient.** The same defect appeared twice in one file across two rewrites, both times invisible to reading, both times obvious to running. The rule was written down in three documents on both occasions. Prose does not hold a line. Only something that fails does.

**Attack the remedy, not just the fault.** A review that stops when the reported defect is closed will certify theatre. Budget a pass specifically for the fix.

**Cheap by design.** This skill is protocol first. Steps 1, 2, 4 and 6 cost nothing but thought and should be done inline. Spend agents only on step 3, where mechanical extraction across a large artefact benefits from a dedicated pass, and step 5, where genuine independence from the author is the entire point. Two agents, not five. If a docket is running up a large bill, it has turned into a second panel and should be stopped.

---

## Output format

```
[DOCKET, N in, N out]

Blockers
  1. [finding] · criterion: [observable] · CLOSED: [evidence] / OPEN: [owner, reason]
  2. ...

Material
  3. ...

Accepted as is
  8. [finding] · REJECTED: [argument]

Self-claims tested:  [n] found, [n] refuted, [n] corrected
Criteria rewritten after the theatre test: [n]
Gates proven falsifiable: [list, or "none, and that is a gap"]
Carried open: [n, and where they are recorded]
```

Count in, count out, and show the two numbers. That single discipline catches more quiet dropping than any amount of process.

---

## Anti-patterns

* **Fixing before the criterion is written.** The single failure this skill exists to prevent. The fix will satisfy whatever criterion is written afterwards, because it was written by someone looking at the fix.
* **Closing on "the tests pass".** Which tests, written by whom, and have they been observed failing?
* **Averaging two reviewers who disagree.** Docket the disagreement.
* **Severity inherited from the reviewer's adjectives.** Rank by consequence, always.
* **Treating a truthful label as a cop out.** Labelling something as what it is, when it cannot be made into what was claimed, is a real closure and usually the honest one. What is not acceptable is deleting the awkward thing silently, which teaches nobody.
* **Running a docket for two findings.** Overhead exceeds value. Triage inline and move on.

---

## Pairing

* `the-panel` upstream. The docket is what its findings should land in.
* `ask-the-council` downstream, re-aimed. The docket supplies the aim.
* `cap-table-guard`, `legal-docs-guard`, `web-qa` produce findings; route them here rather than straight into a fix.
* `hard-task-method` for the execution discipline once items are docketed.
* `decision-log` for any REJECTED item that reflects a material judgement call, so it is not relitigated.
* `system-cartographer` when a closed item changed how a back end process works, because the map is part of the evidence.

---

## House mechanics

British English. No em dashes and no en dash separators anywhere, including in criteria and dispositions. Use commas or restructure.