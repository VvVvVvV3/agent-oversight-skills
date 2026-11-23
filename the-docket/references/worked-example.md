# Worked example: an operations console, August 2026

The session that produced this skill. Included because the protocol is only
persuasive with the actual sequence attached, and because every anti-pattern in
`SKILL.md` was committed here first.

---

## Setting

Two HTML artefacts about to be handed to developers: an operations console and a
system map. Both had already been through an adversarial review and a rebuild.
The handover document claimed a specific property, in bold, in three places:

> A check that has never been seen red is unverified. Every reconciliation in
> this repository has a mutation test that proves it can fail.

---

## Round one, the panel finds the defect

Three lenses, one artefact each pass. The adversarial lens read the console's
reconciliation function and found that seven of its twelve checks passed a
literal `false` as their break condition:

```js
chk("R4","Reserve balance", ..., false, usdC(m.ownBalance), ["readerB"]),
chk("R5","Distribution to income", ..., false, ...),
chk("R6","Holder eligibility", ..., false, ...),
```

They could reach `not_run` through a source outage, and `pass`, and nothing
else. The fault selector offered faults for only five of the twelve, so no
interaction with the page could reveal the gap.

This was the same defect the previous rebuild had existed to remove, back at a
different ratio. Reading the file had missed it twice.

**Note what did not happen.** The panel did not rank this against the other
seven findings, assign an owner, or say what closure would look like. That is
not a criticism of the panel. It is not the panel's job.

---

## Round two, the fix that would have shipped

Every check rewritten to compare two values:

```js
var resA=m.ownBalance, resB=f==="reserve"? m.ownBalance-3.2 : m.ownBalance;
...
broken: Math.abs(resA-resB)>1
```

A headless verifier driving all twelve fault settings, asserting each turned its
own check red and no other. The verifier proven falsifiable by reverting one
break condition to `false` and watching it exit 1 naming that check.

Every gate green. Documents updated. Committed.

**The implicit acceptance criterion was "all twelve checks can go red."** It was
never written down, which is why nobody noticed it was satisfiable by theatre.

---

## Round three, the council attacks the remedy

Pointed at the fix rather than the artefact, with the instruction to attack it:

> Is `recons()` genuinely two sided, or are several of them the same variable
> compared to itself with a fault term subtracted?

Findings:

* Every one of the twelve. `B := fault === X ? f(A) : A`. When no fault is
  selected A and B are the same value in memory, not two systems agreeing.
* R7's break condition was `f === "ring"`, the state of a dropdown. The original
  bug wearing a different hat.
* R6 and R10 both read `SERIES.investors`, so they rendered the same figure in
  the pass state and gave the shared source away to anyone reading the two rows
  side by side.
* The page meanwhile claimed twelve checks "each declaring two distinct source
  systems", and rejected same source checks by name.

The verifier could not have caught any of this. Given `B := fault==X ? f(A) : A`,
"selecting fault X reddens check X and only X" is true by construction.

---

## Round four, closure

The honest criterion, written this time before the second fix:

> A check goes red because the two sides disagree, with no control set.

Which forced an honest split rather than a uniform fix:

* Six checks compare static estate facts. A separate `LEDGER` record was written
  as literals, with nothing computing it from the estate. Those six now redden
  when either record drifts and no fault is selected, proven by mutating the
  estate at runtime through a declared test seam.
* Six checks track figures that move with the interactive controls. **No static
  second record can follow them**, so the criterion was unmeetable. They are
  tagged `1 model` on screen, the copy was corrected to say six of the twelve
  are not reconciliations in this build, and the page names the file where all
  twelve genuinely are two sided.

The divergence test was then proven falsifiable in its own right: reverting one
B side to derive from A produced

```
FAIL
  divergence: after `SERIES[0].tokens -= 7` with no fault selected, R1 stayed
  PASS. Its two sides are not independent.
```

Which is the exact defect the council found, now caught automatically.

---

## The self-claim sweep, run late

Run after the fact, it found three more, all of them assertions the artefacts
made about themselves:

| Claim | Where | Reality |
|---|---|---|
| "each declaring two distinct source systems" | console copy | six did not |
| side panel is "the accessible equivalent" of the diagram | SVG `aria-label` | panel was mouse only, no keyboard path to any node |
| "a pre-commit hook refuses a commit that lets it go stale" | handover document | the engineering notes in the same repository said the hook reads HEAD and catches drift one commit late |

Two further items came from a comment claiming prior diligence. A stylesheet
noted a clipping bug found and fixed at 390px. The identical `white-space:nowrap`
defect was live two rules below at 768px, unchecked, because the comment made
the area feel handled.

Had the sweep run at intake it would have produced the reconciliation finding on
its own, from the copy alone, without anyone reading the function.

---

## Counted in, counted out

| | |
|---|---|
| Findings in | 8 panel, 11 council, 5 self-claim sweep |
| Blockers | 6 |
| Closed with evidence | 19 |
| Closed by truthful labelling rather than by fix | 2 |
| Rejected | 1 |
| Carried open with an owner | 2, both written into the repository backlog |
| Criteria rewritten after the theatre test | 1, and it was the one that mattered |
| Gates proven falsifiable | 3 |

---

## What this example is actually evidence for

Not that adversarial review works. That was already known.

**That a review which stops when the reported defect is closed will certify
theatre.** The panel found the defect. The fix was competent, tested, documented
and wrong. Only a pass aimed specifically at the remedy caught it, and that pass
happened by accident rather than by protocol.

The protocol exists so it stops being an accident.
