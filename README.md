# gleif

A Semvia semantic package over the GLEIF Legal Entity Identifier data — Level 1
(who is who) and Level 2 (who owns whom).

It ships no data. What it ships is a description: a small ontology, a Postgres
connection descriptor carrying no credential, and three RML TriplesMaps that
tell the Semvia federation engine how to read `lei_records` and
`relationship_records` as RDF. Install it and 3.39 million legal entities and
482,824 ownership relationships become queryable over SPARQL, answered by the
database at query time. Nothing is copied and nothing is materialized.

## Install

```json
{
  "requires": {
    "https://github.com/SemviaIO/gleif": "SemviaIO/gleif#v0.3.0"
  }
}
```

Any git ref works in place of the tag — a branch or a commit SHA, in the
`owner/repo#ref` form.

The connection descriptor names the database but carries **no password**. The
installer binds it out of band: `svdb:password` is a secret-marked field, and the
binding is keyed to the descriptor's own subject IRI,
`https://github.com/SemviaIO/gleif/schema/connection#semvia-test-data`, so the
credential is released only for the destination you consented to. No credential
appears anywhere in this repository, and none ever will.

## What it maps

| Source relation | TriplesMap | Yields |
| --- | --- | --- |
| `public.lei_records` | `LeiRecords` | one `gleif:LegalEntity` per LEI record |
| `public.relationship_records` | `Relationships` | one reified `gleif:Relationship` per row |
| `public.relationship_records` | `RelatedEntities` | one of six typed child-to-parent edges, chosen per row by the relationship type |

Entities are subject-keyed on their LEI, at `https://gleif.org/lei/{lei}`, so an
entity has the same IRI whichever relation it was read from.

```
schema/
  ontology.ttl             the classes and predicates
  connection.ttl           where the database is (no credential)
  legal-entities.md        the Level 1 mapping
  relationships.md         the Level 2 reified mapping
  relationship-types.ttl   the six relationship types as a SKOS scheme, and the lookup over it
  related-entities.ttl     the Level 2 typed-edge mapping
```

The mappings are authored as Markdown rather than Turtle. That is not a
convenience — a mapping is a document a human reads and argues with, and reading
it should not require reading RDF. `sem build` materializes them into the Turtle
the engine consumes.

`related-entities.ttl` is the exception, and the file says why in its header: its
predicate is chosen per row from a column, and the Markdown surface puts the
predicate in the `###` heading, where it can only be a constant. Rather than
author the wrong mapping in the nicer format, that one map drops to Turtle.

## The model

Two classes. `gleif:LegalEntity` is every row of the Level 1 golden copy, and
`gleif:Relationship` is a reified Level 2 relationship record.

There is no `Company` / `MutualFund` / `Branch` subclass ladder yet. The GLEIF
entity category rides as data on `gleif:entityCategory` instead: one relation
yields one class for every row it carries, so a ladder would have been a lattice
nothing ever populates. `rml:SQL2008Query` now makes a per-category filtered
source expressible, so the ladder is tracked in
[#4](https://github.com/SemviaIO/gleif/issues/4) rather than ruled out.

The relationship types, by contrast, *do* split — not into classes but into
predicates. A `rml:predicateMap` can carry `rml:reference` plus a
`svrl:resolveVia` lookup, which makes the predicate a function of the
discriminator column: one relation, one scan, six edges. Whether the engine
pushes the row condition into Postgres or evaluates it as a residual is not yet
measured against the live source. The vocabulary that decides which token
means which predicate is ordinary workspace data in `relationship-types.ttl`, so
a seventh GLEIF relationship type is a new `skos:Concept` and not a mapping
edit.

The ontology aligns five terms to GLEIF's own published vocabulary with
`owl:equivalentClass` / `owl:equivalentProperty`. Those are live lattice edges in
Semvia, walked in both directions, so the set is kept deliberately small and each
edge is defended in a comment next to it — along with the ones that were
considered and rejected.

## Caveats worth knowing before you query

**Name the edge you mean; `gleif:relatedEntity` is still the union.** Each row of
the Level 2 copy lands on the edge its relationship type names —
`gleif:directlyConsolidatedBy`, `gleif:ultimatelyConsolidatedBy`,
`gleif:fundManagedBy`, `gleif:subFundOf`, `gleif:feederTo`,
`gleif:internationalBranchOf` — so `gleif:directlyConsolidatedBy+` walks a
consolidation chain and nothing else. All six are declared
`rdfs:subPropertyOf gleif:relatedEntity`, so that edge still answers as their
union and a closure over it still enumerates every relationship regardless of
kind. It is the right question sometimes; it is just no longer the only one you
can ask. Reading `gleif:relatedEntity+` when you meant ownership will walk
fund-management and branch edges too, which is usually not what "who owns whom"
means.

**`gleif:ultimatelyConsolidatedBy` is already transitive.** GLEIF computes it, so
it is a shortcut to the root of the chain rather than another rung. Walk
`gleif:directlyConsolidatedBy+` to climb; read
`gleif:ultimatelyConsolidatedBy` once to arrive.

**Relationship validity periods are not mapped.** GLEIF stores them in
positional slots whose period type is not stable across rows, so mapping a slot
to a named predicate would assert a confidently wrong triple rather than an
absent one.

**Some column names are derived, not verified.** Six are confirmed against the
live relation; the rest follow the GLEIF golden-copy CSV header lowercased with
`.` replaced by `_`, and are marked as derived where they appear in the mapping
documents. A mapped column that turns out not to exist declines on its own — it
costs its predicate and leaves the rest of the map working.

**No `sh:minCount` on any mapped property.** These shapes describe a virtual
graph over a source we do not control, and that source has nulls — 8,986 records
carry no entity status. A shape is documentation here, not a gate the source
could satisfy.

## Licence and attribution

Everything Semvia authored here is CC0 1.0 Universal — see `LICENSE`.

The data is GLEIF's and is not redistributed by this package. See `NOTICE` for
the source, GLEIF's terms of use, and what this package does and does not claim.
