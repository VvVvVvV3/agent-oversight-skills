---
name: graph-engineering
description: >
  Designs the topology of an AI system as an explicit, versioned artefact: task graphs (nodes are agents, functions, routers, verifiers, human gates; edges are the only permitted handoffs; state has declared merge rules) and knowledge graphs (typed entities and relations with provenance and time, so agents remember across sessions). ALWAYS use when designing, documenting, or auditing any routine, automation, agent workflow, or memory layer for VESTN, Vexiom, PCS, Velmure, Mensfortis, or a client; when a system double-fired, dropped a task, or nobody can say who owns a step; when choosing between a graph, plain RAG, or a linear pipeline; and on "graph engineering", "graph spec", "topology", "map the routine", "who owns this step", "does this need a graph", "knowledge graph", "agent memory", "provenance", "topology audit". Sits upstream of multi-agent-loopcraft, the-panel, ask-the-council, the-docket and system-cartographer and delegates to them. Pair with inference-economics and decision-log.
---

# Graph Engineering

Prompt engineering steered what the model says. Loop engineering steered how many times it tries. Graph engineering steers the shape of the system: which nodes exist, which handoffs are allowed, what state flows between them, and where a human sits. The artefact is the graph spec. Everything else in the library either produces a node, runs a node, or verifies a node.

The failure this prevents is not a bad answer. It is two parts of a system both thinking they own a step, or neither thinking they do, and nobody able to say afterwards what the system was supposed to do at that point. The prompts were fine. The topology was never written down.

Three rules govern everything below.

1. **The spec precedes the build.** No routine, automation, or agent workflow ships without a graph spec that could be diffed. If it exists only as prompts and cron entries, it has no topology, it has habits.
2. **Every edge answers who, what, and on what evidence.** An edge without a declared payload and a declared trigger is a guess.
3. **A graph must earn its cost.** Most tasks want a single agent with tools, or a linear pipeline. Recommending no graph is a success of this skill, not a failure.

---

## When this skill applies, and what it hands off

| Situation | This skill does | Then delegate to |
|---|---|---|
| New routine or automation | Write the task-graph spec first | multi-agent-loopcraft for loop mechanics, inference-economics for budgets |
| Existing routine misbehaving | Topology audit against the spec (or write the missing spec) | the-docket to triage findings |
| Agents need durable shared memory | Knowledge-graph spec: ontology, extraction, fusion, provenance, serving | obsidian-vault-conventions if the store is a vault |
| Mapping a codebase that already exists | Nothing. Point at system-cartographer | system-cartographer |
| Running a live multi-agent pass | Nothing. Those are executions of nodes | the-panel, ask-the-council, the-agency |
| Vexiom client engagement | Topology audit as a sibling product to the inference-economics cost audit | inference-economics AUDIT mode for the commercial shape |

If none of the rows fit, the task is probably not a graph problem. Say so.

---

## Step 0: Does this earn a graph?

Run this before drawing anything. Read `references/earn-its-cost.md` for the full checklist; the short form is below.

A graph earns its place when at least one of these is central to the workflow, not incidental:

- **Connected queries**: the answer needs two or more hops across relationships
- **Changing relations**: facts about who or what relates to whom change over time and the history matters
- **Provenance**: someone will ask "where did this come from" and needs a real answer
- **Shared world state**: more than one agent, session, or human must act on the same facts without re-deriving them
- **Ownership ambiguity**: the system has already double-fired, dropped a handoff, or has a step nobody can name an owner for

If none hold: single agent with tools, or a linear pipeline. Write that verdict in one line and stop. Do not build the graph because it is interesting.

If one or more hold: start with the **minimum viable graph**. Fewest nodes that make the ambiguity go away. Scale only when a measured signal improves: verified answer time, task success rate, or reviewer effort. Never on feel.

---

## Half one: task graphs

### The five components

Every task graph spec declares all five. Missing one is the finding.

1. **Nodes**: bounded units of execution. Types: `agent` (reasons inside its box), `function` (deterministic, no model), `router` (chooses the next edge), `join` (waits for several inputs, declares merge rule), `verifier` (independent check, never the producer), `gate` (human decision), `sink` (external side effect: send, publish, write).
2. **Edges**: the only permitted handoffs. Each carries a `payload` (what crosses), a `trigger` (what fires it), and an `owner` (which node is responsible for the payload being correct at that moment).
3. **State**: what persists between nodes, where it lives, and the **merge rule** for conflicting writes (last-write-wins, owner-wins, human-resolves, reject). Undeclared merge rules are how the same email goes out four times.
4. **Stop rules**: max iterations, max spend, timeout, and the exit condition in observable terms. A self-graded score alone is not an exit condition.
5. **Human gates**: where a person sits, what they see, and what they can do (approve, edit, reject, escalate). Every `sink` node that is irreversible has a gate or a declared reason it does not.

### The ownership test

For every step in the system ask: which single node is responsible for this being right at this moment? If the answer is "both" or "whichever runs first", the topology is wrong. Split the step or add a join with a merge rule.

### Determinism first

Not every node should be a model. Known business rules stay as `function` nodes. A model earns a node where semantic interpretation is required: classifying free text, drafting, judging quality. Putting a rule inside a prompt makes it unauditable and costs tokens on every run.

### Verifiers are never producers

A node that made a thing does not certify the thing. The verifier edge comes from a separate node with a separate context. This is the same separation ask-the-council enforces at the session level; here it is enforced in the topology.

### Deliverable: the graph spec

Write `graph-spec.json` using the schema in `references/graph-spec.md`. Start from `templates/graph-spec.example.json` (a worked VESTN intel-brief routine). Then run:

```
python scripts/validate_graph.py graph-spec.json
python scripts/render_graph.py graph-spec.json > graph.mmd
```

The validator fails on: orphan nodes, edges without payload or trigger, joins without merge rules, irreversible sinks without a gate, a missing exit condition (a missing spend cap or timeout only warns), and any node that is both producer and verifier of the same payload. Fix the spec, not the render.

---

## Half two: knowledge graphs

Read `references/knowledge-graph-pipeline.md` before doing any of this. The condensed rule set:

- **Ontology before extraction.** Declare entity types and relation types first, with a one-line definition each. Extraction without an ontology produces a bag of strings that looks like a graph.
- **Every edge carries source and time.** `source` (document, message, tool result, human) and `observed_at`. An edge without provenance is a rumour. This is what makes the graph better than a vector store for anything anyone will be held to.
- **Fusion is a decision, not a merge.** When two sources disagree, record both with provenance and a `status` (asserted, contested, superseded, retracted). Do not silently overwrite.
- **Serving is a separate stage.** How agents query the graph (typed lookups, multi-hop, time-windowed) is designed, not left to whatever the store's default search does.
- **Compare against plain RAG on real questions.** Take ten questions the system actually gets asked. If vector search answers them as well, the graph is not earning its cost for that workload.

House note: the VvV and MensFortis vaults are the natural stores. obsidian-vault-conventions governs the note format; this skill governs what the links and frontmatter must carry to count as a graph rather than a folder.

---

## The feedback graph

A single loop drifts. Graph engineering wires loops to watch each other. Read `references/feedback-graph.md` for the design; the four layers are:

- **Operational**: per-task success, latency, cost, tokens per outcome (inference-economics owns the telemetry)
- **Quality**: eval scores, error rates, verifier rejection rate
- **Governance**: who sets targets, who may move a threshold, when changes roll out
- **Audit**: periodic check that the metrics still track the real outcome (an eval suite can climb while live traffic gets worse)

Every routine declares which layers it has. Most of CJ's routines have operational only. That is fine to start, and it should be written down as a known gap rather than discovered later.

---

## Topology audit protocol

When an existing routine or client system arrives:

1. Ask for the spec. If there is none, that is finding one. Reconstruct it from prompts, schedules, and code into `graph-spec.json` as the audit's first deliverable.
2. Run the validator. Every failure is a finding with a severity.
3. Run the ownership test on every step by hand. The validator catches structural orphans; it cannot catch two agents whose prompts both say "you close out the conversation".
4. Check Step 0 in reverse: is any part of this a graph that does not earn its cost? Collapse it.
5. Check the feedback graph: which layers exist, which are missing.
6. Hand findings to the-docket. Do not fix inside the audit.

### Audit report structure

```
# Topology Audit: [System]
## Verdict (one paragraph: graph, pipeline, or single agent; and whether the current build matches that)
## Spec status (existed / reconstructed / partial)
## Findings (severity, node or edge, what is wrong, observable evidence)
## Ownership conflicts (step, contending nodes, proposed owner)
## Cost verdict (parts of the graph not earning their keep)
## Feedback layers (present / missing)
## Recommended minimum viable graph
```

---

## Pitfalls (warn about these unprompted)

- **Graph as decoration**: a Mermaid diagram drawn after the fact that nothing runs against. The spec is the truth; the diagram is a render.
- **Knowledge graph confused with task graph**: one is what the system remembers, the other is how it works. Different schemas, different failure modes. Do not let one term cover both in a brief.
- **Graph database mistaken for memory**: a store does not create reliable memory. Only the ontology, extraction and update rules do.
- **Merge rules by accident**: state written by two nodes with no declared rule. Look for this first in any double-send incident.
- **Self-certification**: a producer node whose output is checked only by itself or by nothing.
- **Gateless sinks**: an irreversible action with no human gate and no written reason for its absence.
- **Graph for its own sake**: the most common one. Return to Step 0.

---

## Library integration

- **multi-agent-loopcraft** owns loop mechanics, routing, and the Loop Design Doc. When a task graph contains a loop, loopcraft designs the loop and this skill records it as a subgraph with its stop rules exposed at the boundary.
- **the-panel, ask-the-council, the-docket, the-agency** are executions. In a spec they appear as node types (`panel` is a fan-out plus join, `council` is a verifier cluster, `docket` is a triage function, agency personas are agent node prompts).
- **system-cartographer** maps code that exists. This skill specifies systems before they exist and audits them against that spec. When both apply, cartographer's `system-map.json` is evidence for the audit, never a substitute for the spec.
- **inference-economics** owns cost telemetry and the Vexiom cost audit. The topology audit is its sibling product: cost audit answers "what does it spend", topology audit answers "what is it supposed to do and does it".
- **decision-log** records any change to a live graph's nodes, edges, or gates. Topology changes are material decisions.
- **punctuation-polish** and **humanizer** run on any audit report that leaves the building.

---

## Reference files

- `references/graph-spec.md`: the schema, node and edge types, merge rules, validator rules
- `references/earn-its-cost.md`: the full Step 0 checklist with worked verdicts
- `references/knowledge-graph-pipeline.md`: the nine-stage pipeline with provenance and fusion rules
- `references/feedback-graph.md`: the four loop layers and how they watch each other
- `templates/graph-spec.example.json`: worked example (VESTN daily intel brief routine)
- `scripts/validate_graph.py`: structural checks on a spec
- `scripts/render_graph.py`: spec to Mermaid
