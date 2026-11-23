# The Feedback Graph

A single feedback loop has four parts: a variable you care about, a target, a way to measure the gap, and an action that closes it. On its own it drifts. Evals built from synthetic data keep scoring higher while live traffic gets worse. A cost loop optimises tokens until quality collapses and nobody notices because quality is not measured. Graph engineering wires loops so they watch, constrain, and correct one another.

## Four layers

| Layer | Watches | Typical signals | Who acts |
|---|---|---|---|
| Operational | The task | success per run, latency, tokens per outcome, spend | the routine itself, or its stop rules |
| Quality | The output | verifier rejection rate, eval score, error rate, gate edit rate | the-docket triage, prompt or node changes |
| Governance | The targets | who sets thresholds, who may move them, roll-out cadence | CJ, recorded in decision-log |
| Audit | The metrics | does the eval still track real use; does "success" still mean what it meant | periodic human review, quarterly minimum |

## How they constrain each other

- Operational cannot move its own thresholds. Governance owns them. A routine that lowers its own bar to pass is the failure mode this prevents.
- Quality gates operational changes. A cost optimisation that raises the verifier rejection rate is rejected, regardless of the saving.
- Audit can invalidate quality. If the eval set no longer resembles live traffic, quality scores are void until the set is refreshed.
- Governance is the only layer a human must occupy. The others can be automated once evidence justifies it.

## Declaring layers in a spec

Every `graph-spec.json` has a `feedback_layers` block. Most of CJ's routines start with operational only. That is acceptable. What is not acceptable is leaving the other three undeclared, because an undeclared gap is one nobody plans to close. Declare `present: false` and a one-line `gap`.

## Minimum viable feedback for a routine

1. Operational: tokens per run and success flag, logged per run (inference-economics owns the telemetry format)
2. Quality: gate edit rate. If CJ edits the output more than a declared fraction of the time, the routine is flagged
3. Governance: the thresholds live in the spec, not in the prompt, and changing them bumps the version
4. Audit: a calendar entry, quarterly, to read ten recent outputs cold and ask whether "good" still means good

## Signs the feedback graph is missing or broken

- A metric that only goes up
- A routine that has never been changed since it was written
- Thresholds that live in a prompt
- Nobody can say when the eval set was last refreshed
- Cost went down and nobody checked what else did
