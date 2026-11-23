# Graph Spec Schema

The spec is JSON so it can be diffed, validated, and rendered. The Mermaid render is derived; never hand-edit it.

## Top level

```json
{
  "name": "string, kebab-case, matches the routine or system name",
  "version": "integer, bump on any node, edge, gate, or stop-rule change",
  "owner": "human accountable for this graph",
  "purpose": "one sentence, what the system is for",
  "step0_verdict": "graph | pipeline | single-agent",
  "step0_reason": "which earn-its-cost condition holds, or none",
  "nodes": [],
  "edges": [],
  "state": {},
  "stop_rules": {},
  "feedback_layers": {},
  "changelog": []
}
```

## Nodes

```json
{
  "id": "kebab-case, unique",
  "type": "agent | function | router | join | verifier | gate | sink | source",
  "does": "plain English, one sentence, what this node is responsible for",
  "model": "only for agent, router (if LLM), verifier: model tier per inference-economics",
  "inputs": ["state keys this node reads"],
  "outputs": ["state keys this node writes"],
  "merge_rule": "join only: last-write-wins | owner-wins | human-resolves | reject",
  "irreversible": "sink only: true | false",
  "gate_reason_absent": "sink only, if irreversible and no gate feeds it: why",
  "gate_actions": "gate only: subset of approve, edit, reject, escalate",
  "subgraph": "optional path to a nested spec (a loop designed by multi-agent-loopcraft)"
}
```

Type meanings:

- **source**: where work enters (schedule, webhook, human message, inbox poll). No inputs.
- **agent**: a model reasoning inside a bounded remit. It may loop internally; the loop's stop rules surface at the node.
- **function**: deterministic. No model. Business rules, formatting, dedupe, file writes that are reversible.
- **router**: chooses among outgoing edges. Declare whether rule-based or model-based.
- **join**: waits for multiple incoming edges. Must declare `merge_rule`.
- **verifier**: independent check. Its `inputs` may not include its own outputs, and it may not share an `id` prefix with the producer it checks.
- **gate**: a human. Declare `gate_actions`.
- **sink**: an external side effect. Sending, publishing, writing to a system of record, spending money.

## Edges

```json
{
  "from": "node id",
  "to": "node id",
  "payload": "what crosses, named state keys or a description",
  "trigger": "what fires it: on-complete | on-approve | on-reject | on-condition:<expr> | on-schedule:<cron> | on-event:<name>",
  "owner": "node id responsible for the payload being correct at this moment; defaults to from"
}
```

## State

```json
{
  "store": "where state lives: in-memory | file:<path> | vault:<path> | db:<name>",
  "keys": {
    "key-name": {
      "written_by": ["node ids"],
      "merge_rule": "required if written_by has more than one entry",
      "summarised": "true if raw content is replaced by a rolling summary; loops should be true"
    }
  }
}
```

## Stop rules

```json
{
  "max_iterations": "integer or null for non-looping graphs",
  "max_spend": "string with unit, e.g. '150k tokens' or 'GBP 2.00'",
  "timeout": "duration",
  "exit_condition": "observable, multi-signal where possible, e.g. 'validator passes AND verifier accepts AND gate approves'",
  "on_breach": "escalate-to:<gate id> | halt | degrade-to:<node id>"
}
```

## Feedback layers

```json
{
  "operational": { "present": true, "signals": ["tokens per brief", "run latency"] },
  "quality": { "present": false, "gap": "no verifier rejection rate tracked" },
  "governance": { "present": true, "who_moves_thresholds": "CJ" },
  "audit": { "present": false, "gap": "no periodic check that brief relevance tracks real use" }
}
```

## Changelog

```json
[{ "version": 2, "date": "YYYY-MM-DD", "change": "added verifier before send", "decision_log_ref": "optional id" }]
```

## Validator rules (what `validate_graph.py` enforces)

Exit 0 when there are no errors, 1 when there is at least one, 2 for wrong usage. A file that cannot be read, is not JSON, is not an object, or has a malformed shape is an error (E21: one `ERROR` line, exit 1, never a traceback; this describes `validate_graph.py`).

| Id | Rule that fails | Why |
|---|---|---|
| E1 | A node has no `id` | Nothing can point at it |
| E2 | Two nodes share an `id` | Edges become ambiguous |
| E3 | A node's `type` is missing or not one of the eight | The type decides which other rules apply |
| E4 | A node has no `does` | A step with no stated job has no owner |
| E5 | A `join` has no valid `merge_rule` | Undeclared merges cause double actions |
| E6 | A `gate` has no `gate_actions` | A gate that cannot act is decoration |
| E7 | A `verifier` lists one of its own outputs among its inputs | Self-certification |
| E8 | A `verifier` is the only producer of one of its inputs; always reported together with E7, because such a verifier necessarily lists its own output as an input | Self-certification |
| E9 | An edge runs from a verifier to itself | Self-certification |
| E10 | An edge names a node that does not exist | Renders lie otherwise |
| E11 | An edge has no `payload` | An edge without one is a guess |
| E12 | An edge `trigger` is missing or invalid. Valid only if exactly `on-complete`, `on-approve` or `on-reject`, or it starts with `on-condition:`, `on-schedule:` or `on-event:` and has at least one non-space character after the colon | An edge without one is a guess |
| E13 | An edge has an `owner` that is not a node id | Ownership must point at something real |
| E14 | A node other than a `source` has no incoming edge, or a node other than a `sink` or `gate` has no outgoing edge | Orphans are steps nobody owns |
| E15 | An `irreversible` sink has no gate anywhere upstream and no `gate_reason_absent` | Unreviewed irreversible actions |
| E16 | A state key has more than one writer and no valid `merge_rule` | Same reason as E5, at the state level |
| E17 | A state key names a writer that is not a node | Ownership must point at something real |
| E18 | `stop_rules.exit_condition` is missing | A loop with no stated exit never ends cleanly |
| E19 | `step0_verdict` is missing or not one of `graph`, `pipeline`, `single-agent` | Forces the earn-its-cost question |
| E20 | There is no `gate` node and no top-level `gate_reason_absent` | Every system has an oversight layer, even if it is one person |
| E21 | For `validate_graph.py`: the file cannot be read, is not JSON, is not an object, or `nodes` or `edges` hold something that is not an object; any other malformed shape is reported the same way | The script cannot check what it cannot parse |

Warnings (non-fatal, exit code unchanged): W1 a `router` with fewer than two outgoing edges; W2 a `gate` with no outgoing edge; W3 an `exit_condition` containing the word score and no " and " (a crude text check for a single self-graded score); W4 `stop_rules.max_spend` or `stop_rules.timeout` missing; W5 more than eight agent nodes (revisit Step 0); W6 no `feedback_layers` block.

Not checked by the script (review by hand):

1. An `agent` whose `does` reads like a fixed rule and should be a `function`.
2. A verifier sharing an `id` prefix with the producer it checks.
3. E15 looks for a gate on some path to the sink, not on every path. A spec where one route crosses a gate and another goes round it passes.
4. Presence of `name`, `version`, `owner`, `purpose` and `changelog`, and whether node `inputs` and `outputs` line up with edge payloads.

`render_graph.py` expects a spec that passes validation; given one it cannot draw it prints one `ERROR` line and exits 1.
