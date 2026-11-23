---
name: system-cartographer
description: >
  Builds and then maintains a visual map of every back-end process in a codebase: what
  each part does in plain English, how it is really built, what is currently wrong with
  it, and how the parts connect. Produces system-map.json, an interactive isometric HTML
  explorer and a Mermaid render, plus a drift check so committed drift from the map is flagged.
  ALWAYS use for "map the backend", "how does this system work", "show me the flow",
  "architecture diagram", "system map", "document the processes", "I have lost track of
  what the code does", "onboard someone onto this repo", or when handing a vibe-coded
  repo to another person or agent. Also use unprompted at the END of any session that
  rewired a back-end process in a repo that already has a map. Pairs with the-agency for
  specialists per subsystem, multi-agent-loopcraft for loop-or-pipeline classification,
  ask-the-council for verification. Do NOT use for front-end component trees, UI
  wireframing, or one-off diagrams outside a repo.
---

# System Cartographer

The problem this solves: code written fast is code nobody has read. The middle ground
between reading every line and ignoring it entirely is a map that is always current,
always honest, and cheap enough to regenerate that it never rots.

Three rules govern everything below.

1. **The map is a build artefact, not a document.** It is generated, verified and
   committed alongside the code it describes.
2. **The JSON is the truth.** The HTML and the Mermaid are renders. Never hand-edit a
   render.
3. **A map that can drift will drift.** Every install ends with a drift check wired in.
   A map without enforcement is worse than no map, because people trust it.

---

## Artefacts

Everything lives under `docs/system-map/` unless the repo has a strong convention.

| File | What it is | Who reads it |
|---|---|---|
| `system-map.json` | Canonical machine-readable map. Source of truth. | Agents, the verifier, you |
| `system-map.html` | Self-contained isometric explorer. Hover, click, drill in, trace a flow. | Humans, collaborators, new joiners |
| `system-map.md` | Mermaid render plus node and condition tables. | Git diffs, pull requests, GitHub and Obsidian previews |

Schema: `references/schema.md`. Read it before writing a single node.

Scripts. At cold start, copy both into the target repo as `scripts/render_map.py` and
`scripts/verify_map.py`, because CI, the pre-commit hook and every future session need
them present in the repo rather than only inside this skill.

```bash
python3 scripts/render_map.py docs/system-map/system-map.json     # JSON to HTML + Mermaid
python3 scripts/verify_map.py docs/system-map/system-map.json --repo .
python3 scripts/verify_map.py --json --strict                     # --json: for agents; --strict: warnings fail too (hooks and CI do not use it)
```

The verifier is not decoration. It checks that every source path exists, every claimed
symbol is really in that file, every line range is inside the file, every edge endpoint
resolves, every code file under `roots` is claimed by some node, every loop flow has an
exit condition, and, crucially, which files have changed since the commit the map was
written against. It exits non-zero when committed code has drifted from the map.

Know its limit. The drift check compares the commit recorded in the map with HEAD, so it
sees committed changes only. It cannot see uncommitted edits, staged or not; the verifier
prints a warning that names them, but the warning does not fail the check. See "What the
drift check cannot see" in `references/enforcement.md`.

---

## Mode 1: cold start, mapping a repo that has no map

Do not start by drawing. Start by reading, in this order. Full procedure with the
grep patterns and the per-language entrypoint list is in `references/mapping-method.md`.

### 1. Establish the perimeter

Find the real edges of the system before the internals: entrypoints (HTTP routes, CLI
commands, cron and queue consumers, webhooks, scheduled jobs), persistent stores,
external services, and background workers. These become the first nodes. Everything
else is what happens between them.

Set `roots` to the directories the map claims to cover and `ignore` to what it
deliberately does not. Be honest here. A map that quietly excludes half the repo to hit
a coverage number is the exact failure this skill exists to prevent.

### 2. Partition, then deploy specialists

Split the perimeter into subsystems of a size one reader can hold, typically three to
seven. For each subsystem, deploy the matching specialist from **the-agency** and give
it that slice only, never the whole repo:

- data layer and stores: Backend Architect, Database Administrator
- request handling and services: Backend Architect, API Designer
- queues, workers, schedulers: Backend Architect, DevOps Automator
- authentication, secrets, permissions: Security specialists
- anything that touches money or user data: Legal Compliance Checker on the constraints

Each specialist returns nodes in schema shape for its slice, plus the edges it can prove
from code it has actually read. An edge it merely assumes goes in `unknowns`, not in
`edges`.

Follow the-agency's own discipline: grep the roster, extract only the chosen agent's
line range, cap at six agents, prefer one TEAM convening over serial deployments.

### 3. Classify the loops

Run every cyclic path through **multi-agent-loopcraft**'s core discriminator before you
record it as a flow. For each candidate loop, answer: is this a true loop (iteration
plus feedback driving toward an exit condition), or a pipeline wearing loop language?

- True loop: record it as a flow with `loop: true` and a concrete `exit`.
- Pipeline: record it with `loop: false`. Do not dress it up.
- A loop nobody can state an exit condition for is the highest-value finding in the
  whole exercise. Record it, flag it in `unknowns`, and tell the user in plain words.

The same skill's checklist letters map onto node fields: exit condition design becomes
`flows[].exit`, budget and blast radius becomes `condition` on the node that spends,
observability becomes an honest note about what you cannot see from the code.

### 4. Write the prose

The single hardest and most valuable part. `what_it_does` must be readable by someone
who has never opened the repo and does not know the framework. No class names, no file
paths, no library names, no "handles" or "manages". Say what actually happens to what.

Weak: "Manages the order lifecycle via the OrderService state machine."
Strong: "Takes an order the customer has just confirmed, holds their money without
taking it, and waits for the warehouse to say whether it can really ship."

`how_its_built` is where the class names, the library, the retry counts and the
timeouts go. `condition` is where the truth goes: what is currently wrong, in present
tense, specific enough to act on. Empty string only when there is genuinely nothing.

### 5. Verify before you ship

Run `verify_map.py`. Fix every error. Then run the map through **ask-the-council**, with
the reviewers pointed at the map rather than at prose:

- **Fact Checker**: does every node's `how_its_built` match the file it points at? Open
  three at random and read them. Any claim not visible in the source is a hallucination.
- **Devil's Advocate**: which `state: ok` is actually `partial`? Which `condition: ""`
  is wishful? Which edge is assumed rather than traced to a call site?
- **Completeness Auditor**: what does the coverage report say is uncharted, and is each
  omission deliberate? Is any entrypoint, cron, or external call missing entirely?
- **Source Critic**: is `what_it_does` grounded in behaviour, or is it a restatement of
  the function name?
- **Synthesiser**: PASS, FIX, or SURFACE.

Deliver with the council's condensed audit trail. Unresolved items go into `unknowns` in
the map itself, not just into the chat, so the next reader inherits them.

### 6. Install the enforcement

Write the drift check in before you call the job done. `references/enforcement.md` and
`assets/` carry ready-made versions of:

- a Claude Code `Stop` hook that runs the verifier and refuses a clean finish when
  committed code has drifted from the map. It does not block on uncommitted edits.
- a `pre-commit` hook for humans. It lets through the commit that first makes the map
  stale, and blocks the next commit that touches mapped code.
- a GitHub Actions job for pull requests. This is the check that holds.

Then tell the user, in one line, which one you installed and how to turn it off.

---

## Mode 2: the update contract, the part that actually matters

Once a repo has `docs/system-map/system-map.json`, this clause is live for every future
session in that repo, including sessions that never mention the map:

> Any change that adds, removes, renames, rewires or materially alters a back-end
> process is not complete until the map reflects it. The map update belongs in the same
> change as the code: the code commit, then a map commit straight after it.

Procedure at the end of such a change:

1. Commit the code change.
2. `python3 scripts/verify_map.py --json` and read `suspect_nodes`.
3. For each suspect node, re-read the changed source and update `what_it_does`,
   `how_its_built`, `condition`, `state`, and the line ranges.
4. Add nodes for anything new. Delete nodes for anything removed, and delete their
   edges. A node whose code is gone must not linger as `dead`; `dead` means the code is
   still there and nothing calls it.
5. Set `commit` to the short SHA of the code commit from step 1 and `generated` to today.
6. Re-run `render_map.py`.
7. Re-run `verify_map.py`. It must exit 0.
8. Commit the three map files: `git add docs/system-map && git commit docs/system-map`.

It is two commits because a map cannot name the commit that contains itself, and drift
is measured against committed code, so the code is committed first and the map follows
as its own commit.

Say what changed in the map in one line. Do not narrate the whole procedure.

**Incremental, never wholesale.** Do not regenerate the map from scratch on an ordinary
change. The accumulated `condition` and `unknowns` entries are the most expensive thing
in the file and a full regeneration throws them away. Touch the suspect nodes and leave
the rest alone.

---

## What good looks like

A map passes the bar when all of these hold:

- A competent engineer who has never seen the repo can read the HTML for ten minutes and
  then correctly say what happens when a request arrives.
- Every `condition` field is something you could open a ticket from.
- Every loop has an exit condition, or is explicitly recorded as not having one.
- `verify_map.py` exits 0 with coverage above 85 percent, and every uncharted file is
  uncharted on purpose. The script prints coverage in its report and does not enforce a
  threshold, so read the figure yourself.
- `unknowns` is not empty. An empty `unknowns` on a real codebase means the mapper did
  not look hard enough, and should be treated as a defect rather than a triumph.

---

## Failure modes to warn about unprompted

- **The flattering map.** Every node `ok`, every condition blank. Useless, and worse
  than useless because it is trusted. If a first pass produces this, the pass was not a
  reading pass.
- **The file listing.** One node per file, edges that are just imports. This describes
  the folder structure, not the system. Nodes are units of behaviour.
- **The map that stopped.** Committed once, never verified again. This is what the drift
  check exists for, and why installing it is part of the job rather than a suggestion.
- **Coverage theatre.** Hitting a coverage number by widening `ignore`. The verifier
  cannot catch this; you have to not do it.
- **Renders edited by hand.** Someone fixes a typo in the HTML, the next render wipes it,
  and trust in the pipeline goes with it. Fix the JSON.
- **Diagram instead of understanding.** A beautiful picture assembled from function
  names without reading a single function body. The council's Fact Checker pass exists
  to catch exactly this; run it honestly.

---

## House integration

- **Mechanics.** No em dashes or en dashes anywhere, including inside the JSON strings.
  The verifier flags them. Run punctuation-polish on any prose that ships alongside.
- **Specialists.** Rosters come from the-agency, never invented.
- **Loops.** Classification and exit-condition discipline come from multi-agent-loopcraft.
- **Verification.** ask-the-council clears the map before delivery. The standard pipeline
  is agency, then council.
- **Method.** For a large cold start, hard-task-method governs decomposition and
  self-verification; this skill supplies the artefact shape inside that frame.
- **Decisions.** If mapping surfaces a material architecture decision, log it via
  decision-log rather than burying it in `unknowns`.
- **Terseness.** One line of framing, then the artefact. Do not narrate the procedure.
