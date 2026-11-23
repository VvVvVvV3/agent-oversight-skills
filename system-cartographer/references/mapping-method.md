# The mapping method

How to actually walk a codebase and come out with nodes rather than a folder listing.
Read this once at cold start. On incremental updates you only need step 6.

---

## 0. Refuse to draw first

The failure mode is drawing a plausible diagram from filenames. Everything below is
ordered so that no node exists until something has been read.

Budget guide for a first pass on a repo of 20k to 100k lines: perimeter 15 percent,
tracing 45 percent, prose 25 percent, verification 15 percent. If prose is taking under
20 percent, `what_it_does` is probably being copied from function names.

---

## 1. Find the perimeter

Run these before opening any file. They locate where behaviour enters and leaves.

```bash
# entrypoints
rg -n --no-heading "app\.(get|post|put|patch|delete)|@(Get|Post|Put|Delete)Mapping|router\.(get|post)|@app\.route|func main|if __name__|cobra\.Command|argparse|click\.command"
# schedules and background work
rg -n --no-heading "cron|schedule|setInterval|celery|bullmq|sidekiq|@Scheduled|Worker\(|consume|subscribe"
# stores
rg -n --no-heading "createConnection|new Pool|SQLAlchemy|prisma|mongoose|redis|createClient|boto3|S3|from_url"
# outbound to other people's systems
rg -n --no-heading "fetch\(|axios|requests\.|http\.Client|HttpClient|stripe|twilio|sendgrid|openai|anthropic"
# configuration that changes behaviour
rg -n --no-heading "process\.env|os\.environ|getenv|viper\.|Settings\(|featureFlag|LaunchDarkly"
```

Every distinct hit cluster is a candidate node. Collapse near-duplicates: forty routes
on one resource are one `entrypoint` node, not forty.

### Language-specific entrypoints worth checking by hand

| Stack | Look at |
|---|---|
| Node / TS | `package.json` scripts, `src/index.*`, `server.*`, Dockerfile CMD |
| Python | `pyproject.toml` scripts, `manage.py`, `wsgi.py`, `asgi.py`, `__main__.py` |
| Go | `cmd/*/main.go`, `//go:generate` |
| Rust | `src/main.rs`, `[[bin]]` in `Cargo.toml` |
| Ruby | `config/routes.rb`, `Rakefile`, `sidekiq.yml` |
| Java / Kotlin | `@SpringBootApplication`, `application.yml` |
| Anything containerised | `Dockerfile`, `docker-compose.yml`, `Procfile`, k8s manifests |

Infrastructure files are usually outside `roots`, but read them anyway. They tell you
which processes actually run, which is not always what the code implies.

---

## 2. Decide the node grain

A node is a **unit of behaviour a person would name in conversation**, not a file and
not a function.

Tests for grain:

- If `what_it_does` needs the word "and" to join two unrelated verbs, split it.
- If two candidate nodes always change together and nobody would ever describe one
  without the other, merge them.
- If a node has one inbound and one outbound edge and adds no decision, it is probably
  a step inside its neighbour. Put it in `steps`, not on the diagram.
- Target 10 to 30 nodes for a service, 25 to 60 for a monolith. Past 60, split the map
  by bounded context and cross-reference, rather than producing something nobody reads.

Height is editorial. Give the tall boxes to the parts that carry the most logic or the
most risk, so the picture matches where the difficulty actually is.

---

## 3. Trace the edges from call sites

An edge is a claim that something moves from A to B. Prove it:

```bash
rg -n --no-heading "\bfunctionName\s*\(" --glob '!*test*'
rg -n --no-heading "publish\(|emit\(|send\(|enqueue\(|dispatch\("
rg -n --no-heading "INSERT INTO|UPDATE .* SET|\.save\(|\.create\(|\.update\("
```

Record the call site in `edges[].source`. An edge with no `source` is flagged by the
verifier as a claim nobody checked, which is exactly what it is.

Edge kinds:

- `data` moves a payload
- `control` transfers execution and waits
- `async` fires and does not wait, including anything through a queue
- `conditional` only fires under a stated condition, which goes in `condition`
- `error` is the failure path, and is worth drawing on any system where failure handling
  is a real behaviour rather than a throw

The most commonly missed edges are the ones the framework makes for you: ORM hooks,
middleware, signal handlers, event subscribers registered by decorator. Grep for the
registration mechanism, not just for explicit calls.

---

## 4. Read the bodies

For every node, open its primary source and read it. Not skim, read. You are looking
for the five things that go into `condition`:

1. **Unbounded anything.** Retries with no cap, queues with no dead letter, loops with
   no exit, caches with no eviction, pagination with no limit.
2. **Silent fallbacks.** A config value read with a default that is never set anywhere
   in the repo. Grep every env var name against the whole tree including CI config; the
   ones with no definition are live defects.
3. **Two writers.** Two code paths that both own the same field or row. Almost every
   state-corruption incident is here.
4. **Trust boundaries crossed without a check.** An identifier taken from a request and
   used to look something up without confirming the caller owns it.
5. **Work that scales with data.** Anything O(n) per request over a table that grows.
   Note the current n and where it stops being fine.

Set `state` honestly:

- `ok` built, wired, exercised
- `partial` happy path only, known gaps
- `stub` returns a constant or does nothing real
- `dead` present in the repo, nothing calls it
- `not_wired` finished but switched off

Grep for the `stub` and `dead` cases rather than trusting your reading:

```bash
rg -n --no-heading "TODO|FIXME|NotImplemented|raise NotImplemented|pass$|return null;|// stub"
rg -n --no-heading "^\s*#\s*(cron|schedule)|# *- *name:.*disabled|enabled:\s*false"
```

---

## 5. Write the prose last

Write `how_its_built` first, from the code, while it is fresh. Then write
`what_it_does` by asking: if I had to explain this to the person who pays for it, with
no jargon and no nouns from the codebase, what would I say?

Check each `what_it_does` against these:

- Would it still be true if the whole thing were rewritten in another language? If not,
  it is implementation detail in the wrong field.
- Does it name a thing the business cares about (an order, a customer, a document, a
  game) rather than a thing the code cares about (a handler, a service, a DTO)?
- Could a reader predict what breaks if this node fails?

---

## 6. Incremental update, the common case

```bash
python3 scripts/verify_map.py --json > /tmp/drift.json
```

`suspect_nodes` lists the nodes whose source changed. For each one:

```bash
git diff <map.commit>..HEAD -- <that node's source paths>
```

Read the diff, not the whole file. Ask four questions:

1. Did what it does change, or only how it is built? Update the field that changed.
2. Did the change add or remove a call across a node boundary? That is an edge.
3. Did the change fix or introduce a `condition`? Conditions are the field most often
   left stale, because fixing a bug rarely reminds anyone to delete its description.
4. Did the change alter a loop's exit condition? Check the flow.

Then set `commit` to the short SHA of the code commit and `generated` to today,
re-render, re-verify, and commit the map files as their own commit after the code.

---

## 7. Repos with no git history, or a map written before the first commit

Make the first commit, set `commit` to that commit's short SHA, then commit the map
again. If the repo
genuinely has no git, the drift check degrades to a warning and the map relies on the
update contract alone. Say so plainly to the user rather than letting them believe
enforcement is in place.
