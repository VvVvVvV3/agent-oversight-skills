---
name: multi-agent-loopcraft
description: >
  Design, review, and optimise multi-agent systems that genuinely loop: an orchestrator dynamically selects specialist agents, executes, evaluates, and re-loops until a defined exit condition is met. ALWAYS use when architecting, debugging, or auditing any multi-agent system, agent swarm, orchestrator, router, subagent team, or Claude Code agent pipeline that iterates until done. Trigger on "multi-agent", "orchestrator", "agent loop", "Ralph loop", "swarm", "routing layer", "software factory", "autoresearch", "loop until complete", or any request to design a system of agents for VESTN, Vexiom, client work, or Claude Code routines. Also use to audit whether an "agentic" build is a true loop or just a pipeline. Do NOT use to run ask-the-council, the-panel, or the-agency (each has its own skill), but DO use when redesigning those frameworks as systems. Pair with the-agency for rosters, hard-task-method for execution discipline, and decision-log for material choices.
---

# Multi-Agent LoopCraft

Expertise for designing multi-agent systems built around true loops: dynamic agent selection, execution with feedback, and iteration until a defined completion state. The job is always to produce an architecture that is a real loop, correctly levelled, properly bounded, and cheaper per unit of progress than a linear pass.

---

## Core Discriminator: Loop vs Pipeline

A multi-agent system is only a loop if it has iteration plus feedback that drives progress toward a defined exit condition. One-shot dispatch then aggregate (basic agentic MapReduce) is a pipeline, not a loop. A true multi-agent loop requires all four:

1. Dynamic agent selection
2. Execution plus evaluation
3. State update and shared memory
4. Re-selection or re-execution until the exit condition is met

Give the loop-or-pipeline verdict before doing anything else. Most "agentic" builds that underperform are pipelines wearing loop language, and naming that early saves the whole engagement. Pipelines are not wrong, they are just a different, cheaper tool; the failure is mislabelling one as the other.

---

## The Zeroth Question: Does This Need Multiple Agents At All?

Before designing agent selection, challenge the premise. A single agent with good tools, a tight prompt, and a retry loop beats a badly coordinated swarm on cost, latency, and debuggability. Escalate to multi-agent only when at least one of these genuinely holds:

- **Context partition**: the work slices exceed or should not share one context window
- **Register split**: specialisations too different for one prompt to hold both well
- **Real parallelism**: concurrent execution buys meaningful wall-clock time
- **Adversarial separation**: producer and verifier must not share bias

If none hold, recommend the single-agent loop and say so plainly. Recommending fewer agents is a feature of this skill, not a failure of it.

---

## The Loop Taxonomy (reference canon)

Treat this five-level stack as this skill's internal reference model. It is a working canon, not a claimed industry standard: use it to level problems consistently, and name which level a problem lives at.

**1. Multi-Agent Execution Loop** (the most common design)
Orchestrator picks the right specialists for the current sub-task. Agents execute (sequentially, in parallel, or hierarchically). Results are aggregated and evaluated against progress. The loop repeats with updated state until the task-level exit condition is satisfied. This is the classic execution loop with dynamic routing added.

**2. Multi-Agent Task Loop** (Ralph style)
Fresh context or fresh agent instances per major iteration. The orchestrator re-selects agents from the original spec plus current failures. Repeats until the artifact meets spec and tests. The fresh-context discipline is the point: it prevents accumulated garbage from steering later iterations.

**3. Multi-Agent Product Loop** (software factory)
Specialist agents or whole agent teams own lifecycle stages: triage, spec, implementation, review, monitoring. The loop runs continuously across a codebase or backlog, with agents activated by incoming signals (new issues, alerts, deploys).

**4. Multi-Agent System Loop** (autoresearch)
One team works the user-facing task. A separate meta-team continuously improves the system itself: prompts, routing logic, selection rules, evals, tools. Only justify this level once the lower loops are stable and instrumented.

**5. Oversight Loop** (human, or high-level agent with a human gate)
Sets goals, decides which loops to activate, allocates compute and budget, culls failing patterns, and sets the autonomy dial on everything below. Never design a system without this layer, even if it is just one person and a dashboard.

---

## Design Checklist

Cover every letter explicitly when designing or auditing. Skipping a letter is how loops fail in production.

**A. Agent selection and routing**
Mechanism (rule-based, LLM router, embedding similarity, learned policy). Selection once at start vs re-selection every iteration (default to per-iteration; it is what makes the system adaptive). Support for activating multiple agents in parallel within one step.

**B. Loop mechanics**
Explicit state representation: blackboard, structured task object, or conversation history with rolling summaries. Never let raw transcripts be the state; summarise aggressively or the loop chokes on its own history. Iteration logic: while not complete, select agents, execute, aggregate, evaluate progress, update state. Max iterations and timeouts as hard safeguards. Both early exits (solved sooner than expected) and late exits (diminishing returns detected).

**C. Exit condition design (critical)**
Define what complete actually means in concrete terms: tests passing, eval score threshold, human approval, production metric, user confirmation. Multi-signal exits beat single signals; a loop that exits on one self-graded score will flatter itself.

**D. Feedback and learning inside the loop**
How iteration N results improve selection and behaviour at N+1. Failure pattern detection with automatic prompt or memory updates. Cross-agent communication protocols, defined rather than emergent.

**E. Autonomy dial per component**
Selection, execution, evaluation, and the continue-or-stop decision each get their own autonomy setting. They do not have to match. Ratchet autonomy up as evidence accumulates, never as a starting assumption.

**F. Human oversight placement**
Where the human stays: initial goal setting, reviewing agent selections, approving major iterations, final sign-off, ambiguous cases. Expose an ask-a-human tool as a first-class agent capability so escalation is a designed path, not a crash.

**G. Observability and debugging**
Full trace across orchestrator and every selected agent. Clustering of failure modes across iterations. Visualisation of which agents get chosen over time; routing drift is an early warning signal.

**H. Budget and blast radius**
Hard token and spend caps per iteration and per loop. Tool permission scoping per agent (the review agent does not need deploy rights). A kill switch above the loop. The loop must be cheaper per unit of progress than a linear pass, or its complexity is not earning its keep.

---

## Canonical Deliverable: The Loop Design Doc

Deliver every architecture in this fixed shape, so designs are comparable across projects:

1. **Classification**: taxonomy level plus the loop-or-pipeline verdict
2. **Zeroth answer**: single-agent vs multi-agent, and why
3. **Orchestrator**: routing logic in one paragraph or pseudocode
4. **Roster**: each specialist, its remit, its input slice
5. **State**: what is shared, where it lives, how it is summarised
6. **Loop**: iteration logic, max iterations, timeouts
7. **Exit**: the exit conditions, multi-signal where possible
8. **Autonomy map**: dial setting per component (A through E)
9. **Human gates**: where and why
10. **Budget**: caps, permission scoping, kill switch
11. **Nesting**: how this loop sits inside higher loops

Prefer pseudocode over prose wherever it is tighter. Flag any component the user has not specified rather than inventing it silently.

**Skeleton every design reduces to:**

```
while not exit_met(state):
    agents  = router.select(state)            # per-iteration, not once
    results = execute(agents, slices(state))  # parallel where independent
    state   = evaluate_and_update(state, results)
    if state.iterations > MAX or state.spend > CAP:
        escalate_to_human(state)
```

---

## Pitfalls (warn about these unprompted)

- **Pipeline dressed as a loop**: no feedback, no re-selection, just staged dispatch
- **Over-agentification**: multi-agent where one agent plus tools wins on every axis
- **Context bloat**: state as raw accumulated transcripts instead of summaries
- **Unaggregated conflict**: agents disagree and nothing is responsible for resolving it
- **Over-automation too early**: start with human checkpoints, ratchet up with evidence
- **Selection as bottleneck**: an expensive router called every step; cache and batch
- **Unbounded spend**: a loop without caps has an invoice as one of its failure modes

---

## Response Protocol

When a goal or an existing system arrives:

1. Map it to the taxonomy and give the loop-or-pipeline verdict
2. Answer the zeroth question: single agent or multi-agent, and why
3. Locate where agent selection and iteration happen, or are missing
4. Produce the Loop Design Doc (all eleven sections)
5. State how the loop nests upward (Task, Product, System) and where the human sits

Stay precise, structured, and practical. Always distinguish pipelines from true loops. Push dynamic selection and iteration into well-designed loops with proper feedback and exit conditions, and push back when the right answer is fewer agents.

---

## Library and House Integration

- **Boundary**: this skill designs and audits systems; it never runs the in-session frameworks. ask-the-council is a live convergent verification loop, the-panel is a live divergent decompose-dispatch-synthesise pattern, the-agency is a roster source. Cite them as worked instances; redesign them with this skill only when asked.
- **Rosters**: when an architecture needs named specialists, pull personas from the-agency rather than inventing new ones.
- **Decisions**: log material architecture choices via decision-log.
- **Mechanics**: no em dashes or en dashes in any output this skill produces; run punctuation-polish as the final pass on anything that ships.
