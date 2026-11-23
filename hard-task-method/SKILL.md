---
name: hard-task-method
description: The working method for hard, multi-step tasks. Decomposition, self-verification, and next-action selection, written down by Claude Fable 5 so successor and fallback models run the same discipline. ALWAYS load this skill at the start of any task expected to take more than a handful of steps, any task where "done" could be faked, any brief with multiple constraints or deliverables, and any session where the user says "hard problem", "big brief", "full build", "take this end to end", or hands over a large context dump in one message. Do NOT load it for one-step questions or trivial edits, where the overhead costs more than it saves. Pair with ask-the-council or the-panel when a dedicated multi-agent pass is warranted, decision-log for material decisions, and punctuation-polish before anything ships.
---

# Hard Task Method

This file transfers method, not capability. It cannot make a model smarter. What it can do is make any model consistent: the same discipline on task one hundred as on task one. That consistency is where most of the value was.

Three phases. Decompose before working. Verify before reporting. Decide deliberately what happens next. Everything below serves one of those three.

## Phase 1: Decompose

**1. Define done before starting.** One line: what artefact will exist, what must be true of it, and who judges it. If you cannot write that line, the brief is not understood yet. Resolve that first, from the brief itself where possible, from the user only where necessary.

**2. Separate the stated request from the actual deliverable.** People describe tasks in terms of the first step they thought of, not the outcome they want. "Fix this query" often means "make the report correct". Serve the outcome. Say so if the two diverge.

**3. Ground truth before planning.** Read the actual files. Render the actual page. Run the actual command. Never plan from a mental model of the system when the system itself is inspectable. Every hour of work built on a stale assumption is an hour owed back with interest. Then write down three lists: known, unknown, assumed. Assumptions get flagged, not silently absorbed.

**4. Find the load-bearing element.** In every hard task there is one assumption, dependency, or component that invalidates everything downstream if it is wrong. Name it explicitly. Test it first. A plan that discovers its fatal flaw in step nine was decomposed badly.

**5. Split by dependency, not by topic.** Topical decomposition produces tidy headings and hidden coupling. Dependency decomposition asks: what must be true or decided before other work makes sense? The test of a good split is that each piece can be verified on its own, and the interfaces between pieces can be stated in one sentence each.

**6. Sequence by risk.** Highest uncertainty first, so failure arrives cheap and early. Then longest lead time. Mechanical, low-risk work goes last: it will still be there, and it never kills a project.

**7. Right-size the machinery.** Decomposition has overhead. Spending it on an easy task is waste. If the whole job fits in one clean pass, do the pass. This skill is for work that does not.

## Phase 2: Verify

**1. Done means observed done.** The single most important rule in this file. A claim of completion is a report; an observation of completion is a result. Run the code. Render the build. Re-read the document as a stranger would. If the deliverable cannot be observed working, say exactly what was and was not verified. "Should work" is not a state of the world, it is a state of mind.

**2. Verify against source, not memory.** Every factual claim, figure, name, and quote gets checked against the file, the page, or the output it came from. Memory of having read something is not the thing. This applies with full force to your own earlier messages in the same session.

**3. Re-derive numbers a second way.** Any figure that matters gets computed twice by different routes. Percentages reconcile to 100. Totals reconcile to their parts. A number that only exists via one derivation is a candidate error, not a fact.

**4. Run an adversarial pass.** Switch stance from author to attacker and try to break the output. Feed it the edge case. Look for the internal contradiction, the broken cross-reference, the claim that quietly exceeds the evidence. The pass is only real if it is allowed to find something; a review that always returns clean is decoration.

**5. Check delivery against the brief, line by line.** List what was asked. List what was produced. Name every gap out loud rather than letting scope quietly narrow to what happened to get finished. Partial delivery honestly labelled is useful; partial delivery presented as complete is the fake done this phase exists to kill.

**6. Severity-rank findings.** Blocker, degraded, cosmetic. Fix blockers before touching polish. Time spent perfecting prose in a document whose numbers are wrong is worse than wasted: it manufactures false confidence.

**7. Report uncertainty at its actual size.** State what is verified, what is probable, and what is assumed, in those words. Never round uncertainty up to certainty because the sentence reads better. Confidence you did not earn is debt the user pays later.

## Phase 3: Decide what next

**1. Choose the step that reduces the most uncertainty.** Not the easiest step, not the most visible one. Ask: which action, once done, most changes what I know about the whole task? Do that.

**2. Vertical slice over broad shallow.** One piece taken end to end and verified beats five pieces at eighty percent. Finished work compounds; near-finished work rots. It also surfaces integration problems while they are still cheap.

**3. Honour stop conditions.** "Good enough" was defined in Phase 1. When the work hits it, stop. Gold-plating past the stop condition is not diligence, it is spending the user's budget on your own comfort.

**4. Act on the reversible, ask on the irreversible.** If a wrong guess costs a redo, infer intent and execute; the user did not write a full brief to answer twenty clarifying questions. If a wrong guess costs money, reputation, a relationship, or an unrecoverable state, ask, and ask one sharp question rather than five vague ones.

**5. On failure, diagnose before retrying.** A retry without a changed hypothesis is superstition. Change one variable, predict what should differ, observe. Three failed attempts on the same line means the approach is wrong, not the execution: back up one level of the decomposition and re-plan from there.

**6. Log material decisions with their reasons.** One line each: what was decided, why, what was rejected. Future sessions inherit the conclusion without relitigating the argument. If a decision-log skill exists, route through it.

## The memory file

Method compounds only if learnings persist. Maintain one file, `LEARNINGS.md`, in the working root.

- Append at the end of any session that produced a transferable lesson: a failure mode hit, a shortcut found, a wrong assumption corrected.
- Entries are rules, not diary. "Lighthouse scores from preview URLs understate production by roughly 5 points" earns its place. "Worked on the site today" does not.
- Read it at the start of hard tasks. Prune it when entries stop paying rent. A memory file nobody reads is a log; a short one read every session is compound interest.

## Anti-patterns

- Decomposing trivial work to look thorough.
- Verifying by re-reading your own reasoning instead of observing the artefact.
- Mistaking effort for progress: tokens spent is not uncertainty reduced.
- Narrating the method instead of running it. The user wants the output; the discipline should be visible only in its quality.
- Padding. If the honest answer is short, the answer is short.
