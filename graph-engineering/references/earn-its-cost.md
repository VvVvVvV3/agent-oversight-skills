# Does This Earn a Graph?

Run before drawing anything. The default answer is no. Recommending a single agent or a linear pipeline is the skill working, not the skill failing.

## The five conditions

Score each honestly. One clear "central" is enough to proceed; five "incidental" means no graph.

| Condition | Central looks like | Incidental looks like |
|---|---|---|
| Connected queries | "Which advisors are linked to counterparties on active deals?" needs two hops across typed relations | "What did the advisor say?" is one lookup |
| Changing relations | Roles, ownership, or stage change and the history must be queryable ("who owned this in March") | Facts are mostly static or only the latest value matters |
| Provenance | Someone will be held to the answer and must show where it came from (investor, lawyer, regulator, client) | Internal convenience, nobody will ask |
| Shared world state | Several agents or sessions must act on the same facts without re-deriving them, and drift between them costs real money or trust | One session, one agent, one context window |
| Ownership ambiguity | The system has already double-fired, dropped a handoff, or a step exists that nobody can name an owner for | The steps are obvious and linear |

## Three verdicts

**Single agent.** One model, good tools, a tight prompt, a retry loop. Wins on cost, latency, and debuggability. Choose this whenever the work fits one context window and one register.

**Pipeline.** Staged dispatch, no re-selection, no feedback. Cheaper than a loop and not wrong. Choose this when steps are fixed and ordered and no step needs to revisit an earlier one. A pipeline still gets a graph spec (it is a graph with no cycles), but a short one.

**Graph.** Declared nodes, permitted edges, merge rules, gates, stop rules. Choose this only when a condition above is central.

## Minimum viable graph

Once a graph is justified, the first version has the fewest nodes that make the central condition go away. Typical shape:

- One `source`
- One or two `agent` or `function` nodes
- One `verifier` if any output leaves the building
- One `gate` before any irreversible `sink`
- One `sink`

That is five or six nodes. Add nodes only when a measured signal justifies each one.

## The measured signals

Scale only when one of these improves in a before-and-after comparison on real traffic, not synthetic:

- **Verified answer time**: time from question to an answer someone checked and accepted
- **Task success rate**: fraction of runs that reach the exit condition without a human rescue
- **Reviewer effort**: minutes a human spends per run at the gate

If none improve after adding a node, remove it.

## Knowledge graph specific: the ten-question test

Before building a knowledge graph for agent memory, write down ten questions the system is actually asked. Answer them with plain vector search over the same source material. If vector search gets eight or more right with acceptable provenance, the knowledge graph is not earning its cost for that workload. Build it only for the questions vector search failed, and check those failures are connected-query or provenance failures rather than retrieval quality failures.

## Worked verdicts

**VESTN daily intel brief.** Sources polled, items filtered, deduped against yesterday, drafted, flagged for CJ, written to the vault. Ownership ambiguity was real (two routines could both flag the same item), provenance matters (a brief cites sources), and shared state exists (the dedupe memory). Verdict: graph, minimum viable, eight nodes. See `templates/graph-spec.example.json`.

**Mensfortis daily grid post.** Pick quote, pick archetype, draft caption, produce image brief, save. One register, one context window, no conflicting writers. Verdict: single agent with a checklist. No graph.

**Vexiom client onboarding memory.** Multiple sessions, multiple agents (proposal drafter, audit runner, invoice generator) all need the same client facts, and facts change (contact, scope, stage). Shared world state and changing relations are central. Verdict: knowledge graph, small ontology (Client, Contact, Engagement, Deliverable, Invoice), provenance on every edge.

**PCS job quoting.** Take a photo and description, produce a quote. Verdict: pipeline. Three fixed steps, no revisit, one gate before the quote is sent.
