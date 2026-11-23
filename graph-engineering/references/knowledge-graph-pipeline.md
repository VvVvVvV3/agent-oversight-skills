# Knowledge Graph Pipeline for Agent Memory

A knowledge graph is what agents remember: typed entities, typed relations, each edge stamped with where it came from and when. This is the nine-stage pipeline, condensed for practical use. The stages are the standard academic sequence (the Southeast University knowledge graph course is the reference lineage); the rules attached to each are house rules.

Read the whole file before designing memory for any multi-session or multi-agent system. Run the ten-question test in `earn-its-cost.md` first.

## The nine stages

### 1. Ontology design
Declare entity types and relation types before touching data. One line each. Keep it small; ten entity types is a lot for a venture-scale graph.

```
Entities:  Person, Organisation, Deal, Document, Decision, Asset
Relations: advises(Person, Organisation), party_to(Organisation, Deal),
           evidenced_by(Deal, Document), decided(Person, Decision),
           supersedes(Decision, Decision)
```

Rule: every relation names its domain and range. A relation that can connect anything to anything is not a relation, it is a tag.

### 2. Source selection
Name the sources that feed the graph and rank their trust. Human statement in chat, executed contract, tool result, web page, and model inference are not equal. Record the ranking; fusion (stage 6) depends on it.

### 3. Entity extraction
Pull entities from sources. Model-based extraction is fine, but every extracted entity carries `source` and `observed_at`. Extraction without an ontology is the most common failure: it yields a bag of strings that renders as a graph and answers nothing.

### 4. Relation extraction
Pull typed relations between extracted entities. Reject any relation not in the ontology; log the rejection, because repeated rejections are how the ontology learns it is missing a type.

### 5. Entity resolution
Decide when two mentions are the same thing. "Sam", "Sam Taylor", "Head of Operations" may all be one Person. Record the resolution decision and its confidence. Wrong merges are worse than duplicates because they are silent.

### 6. Fusion
When two sources disagree, do not overwrite. Record both edges with provenance and set `status`:

- `asserted`: single source, not contradicted
- `contested`: multiple sources disagree, unresolved
- `superseded`: a later, higher-trust source replaced this; keep the old edge with `valid_until`
- `retracted`: the source itself withdrew it

Fusion is a decision with a rule (trust ranking, recency, human), not a merge. Contested edges surface to a human gate on a cadence.

### 7. Quality and consistency
Check: every edge has source and time; no relation violates domain or range; no entity is orphaned with zero edges after resolution; contested count is tracked as a metric.

### 8. Storage and serving
Choose the store by query shape, not fashion. For CJ's scale, an Obsidian vault with disciplined frontmatter and links is a legitimate graph store, and obsidian-vault-conventions governs the format. Serving is designed separately: typed lookup ("all Deals party_to Organisation X"), multi-hop ("Persons advising Organisations party_to active Deals"), time-windowed ("what did we believe about X on date Y").

### 9. Maintenance and update
Declare the update cadence, who may write, and what triggers re-extraction. A graph nobody updates is a snapshot with a database in front of it.

## The edge record

Every edge, wherever it is stored, carries:

```json
{
  "from": "entity id",
  "relation": "ontology relation name",
  "to": "entity id",
  "source": "document path, message id, tool result id, or 'human:CJ'",
  "observed_at": "ISO timestamp",
  "valid_from": "optional",
  "valid_until": "optional, set when superseded",
  "status": "asserted | contested | superseded | retracted",
  "confidence": "0 to 1, from extraction or resolution"
}
```

In a vault, this maps to frontmatter on the note plus a typed link. See obsidian-vault-conventions for the exact keys; do not invent parallel ones.

## What a knowledge graph is not

- Not a task graph. That is how the system works; this is what it knows.
- Not created by a graph database. The store holds what the ontology, extraction, and update rules put there, and nothing more.
- Not a replacement for vector search. It beats vector search on connected queries, provenance, and time. It loses on fuzzy recall over unstructured prose. Most systems want both, with the graph as the system of record and vector search as the finder.
