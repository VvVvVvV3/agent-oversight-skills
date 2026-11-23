# system-map.json, the schema

The map is the artefact. The HTML and the Mermaid are renders of it. Never hand-edit a
render; edit the JSON and re-run the renderer.

Location: `docs/system-map/system-map.json` (override with `SYSTEM_MAP` env var).

---

## Top level

```jsonc
{
  "schema": "system-map/v1",          // required, exact string
  "repo": "rivers-of-empire",          // required, short repo name
  "title": "The Evolution Harness",    // required, what the system IS
  "subtitle": "how a strategy program gets written, tested and filed",
  "commit": "a1b2c3d",                 // required, short SHA of the last code commit the map describes
  "generated": "2026-08-15",           // ISO date, set to today on every update; not checked by the verifier
  "roots": ["src", "services"],        // required, dirs the map claims to cover
  "ignore": ["**/*_test.py", "migrations/**"],  // optional, globs excluded from coverage
  "summary": { ... },                  // see below
  "stats": [ ... ],
  "groups": [ ... ],
  "nodes": [ ... ],
  "edges": [ ... ],
  "flows": [ ... ],
  "unknowns": [ ... ]
}
```

The verifier fails without these top-level keys: `schema`, `repo`, `title`, `commit`,
`roots`, `nodes` and `edges`. The other keys here (`generated`, `summary`, `stats`,
`groups`, `flows`, `unknowns`) are used by the renderer and by convention. The verifier
does not check that they are present and does not fail without them.

## summary

Prose that survives a stranger reading it cold. Two required keys, both plain English,
no jargon that is not defined on the page.

```jsonc
"summary": {
  "what_this_is": "This repository is a turn-based 4X game plus a system that breeds strategy programs to play it. A language model writes a program, the program plays 60 games against the existing population, the results become a rating and a written description, and the description decides where it is filed.",
  "how_to_read": "Hover anything for a plain description. The How it's built tab gives the implementation, and Condition lists what is currently wrong with it.",
  "hard_part": "Nearly every hard problem here turned out to be a measurement problem rather than a strategy one."   // optional but strongly encouraged
}
```

## stats

Header counters. Facts pulled from the codebase or its data, never invented. Each one
must be traceable to something you actually counted or read.

```jsonc
"stats": [
  { "label": "MODEL ROLES", "value": "4" },
  { "label": "ENGINES", "value": "2, one not switched on" }
]
```

## groups

Sidebar sections. Order is the reading order you want a newcomer to follow.

```jsonc
"groups": [
  { "id": "loop",    "label": "THE EVOLUTION LOOP", "order": 1 },
  { "id": "support", "label": "SUPPORTING THE LOOP", "order": 2 },
  { "id": "game",    "label": "THE GAME",            "order": 3 },
  { "id": "out",     "label": "WHAT COMES OUT",      "order": 4 }
]
```

## nodes

One node per real unit of backend behaviour: a service, a job, a queue, a store, a model
call, an external dependency, an entrypoint. Not one node per file, and not one node per
function. If you cannot write `what_it_does` without saying "and", it is probably two nodes.

```jsonc
{
  "id": "P",                             // required, unique, short. Used on the diagram face.
  "label": "STRATEGY ARCHIVE",           // required, human name
  "group": "loop",                       // required, must match a groups[].id
  "kind": "store",                       // required, see kinds below
  "height": 2,                           // optional 1..4, visual mass. Use for the parts that carry the most logic.
  "what_it_does": "Holds every strategy program ever written, filed by what its description says it does.",
                                          // required. Plain English. A non-engineer must follow it.
  "how_its_built": "SQLite table plus a FAISS index over 768-dim description embeddings. Writes are append-only; nothing is ever deleted, only superseded.",
                                          // required. The implementation, honestly.
  "condition": "Index rebuild is O(n) on every write and takes 40s at 600 rows. Fine now, not fine at 10k.",
                                          // optional. What is currently WRONG with it. Empty string if genuinely nothing.
  "state": "ok",                         // required: ok | partial | stub | dead | not_wired
  "source": [                            // required, at least one entry, real paths
    { "path": "src/archive/store.py", "symbol": "StrategyArchive", "lines": "12-188" },
    { "path": "src/archive/index.py" }
  ],
  "steps": [                             // optional. What happens inside, in execution order.
    { "id": "P.1", "label": "embed description", "what": "768-dim vector from the write-up model" },
    { "id": "P.2", "label": "nearest-cluster file", "what": "cosine against existing cluster centroids, threshold 0.82" }
  ],
  "owner": "backend",                    // optional, team or person
  "risk": "high"                         // optional: low | medium | high. Drives the render's attention markers.
}
```

### kinds

| kind | means | rendered as |
|---|---|---|
| `entrypoint` | where a request or run begins: HTTP route, CLI, cron, webhook | flat slab, dashed inbound |
| `process` | code that transforms things | standard box |
| `store` | database, table, index, bucket, cache, file archive | stacked plates |
| `queue` | message bus, task queue, channel | thin wide box |
| `job` | scheduled or background worker | box with a clock mark |
| `model` | an LLM or ML model call | small raised box |
| `external` | third-party API or service you do not control | outline only, no fill |
| `config` | flags, env, settings that change behaviour materially | small flat tile |

### state

Honesty field. This is what stops the map from being marketing.

- `ok`: built, wired, exercised
- `partial`: works for the happy path only, known gaps
- `stub`: signature exists, body does nothing real
- `dead`: still in the repo, nothing calls it
- `not_wired`: finished but not switched on (the Rust rewrite in the reference image)

## edges

```jsonc
{
  "from": "P",                  // required, node id
  "to": "S",                    // required, node id
  "label": "parent candidates", // required, what actually moves along this edge (the verifier only warns when it is missing)
  "kind": "data",               // required: data | control | async | conditional | error
  "condition": "only when the era counter advances",  // optional, when this edge fires
  "source": [{ "path": "src/loop/select.py", "lines": "44-51" }]  // optional but preferred: where the call actually is
}
```

An edge without a `source` is a claim you have not checked. The verifier counts them.

## flows

Named traversals. These drive the "trace one step" and "resume the flow" controls, and
they are how a reader learns the system in order rather than by wandering.

```jsonc
{
  "id": "evolution",
  "label": "Evolution loop",
  "path": ["P", "S", "D", "R", "H", "C", "E", "P"],   // node ids in execution order
  "loop": true,                                        // does it return to the start
  "trigger": "era advance, or manual run",
  "exit": "era N has 8 rated doctrines filed"          // required when loop is true
}
```

A flow with `loop: true` and no `exit` is the single most common defect this schema
catches. It means nobody knows when the thing is supposed to stop.

## unknowns

Written record of what you could not determine. Never silently omit a subsystem you
failed to understand; put it here.

```jsonc
"unknowns": [
  "Retry policy on the model-call driver: retries exist in code but the backoff constant is read from an env var that is not set anywhere in the repo.",
  "Whether the Rust engine and the Python engine produce identical game outcomes. No differential test exists."
]
```

---

## Hard rules

1. Every `source[].path` must exist in the repo. The verifier fails on dead anchors.
2. Every `edges[].from` and `.to` must be a real node id.
3. Every file under `roots` that is not matched by `ignore` should be reachable from some
   node's `source`. The verifier reports coverage and lists uncharted files.
4. `what_it_does` never contains a class name, a file path, or a library name. That is
   what `how_its_built` is for. If a reader needs the vocabulary of the codebase to
   understand `what_it_does`, rewrite it.
5. `condition` is not a wishlist. It is present tense, observed, and specific enough to
   act on. "Could be optimised" is not a condition. "Rebuilds the whole index on every
   write, 40s at 600 rows" is.
6. No em dashes or en dashes anywhere in the JSON strings. House mechanics apply to the
   map exactly as they apply to prose.
