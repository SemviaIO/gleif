# gleif

A Semvia semantic package over the GLEIF Legal Entity Identifier data — Level 1
(who is who) and Level 2 (who owns whom).

The package ships no data. What it ships is a description: a small ontology, a
connection descriptor for a public bucket, and three RML TriplesMaps that tell
the Semvia federation engine how to read two Parquet objects as RDF. Install it
and 3.39 million legal entities and 482,824 ownership relationships become
queryable over SPARQL, answered from the bucket at query time with HTTP range
requests. No credential, no file to place, and no Semvia server in the path.

## Install

Paste `https://pkg.semvia.io/semvia/gleif/@0.4.0` into Folio's dependency
drawer, or from a workspace:

```sh
sem add https://pkg.semvia.io/semvia/gleif/@0.4.0
```

Either records the requirement in `sem.json`:

```json
{
  "requires": [
    {
      "@type": "https://pkg.semvia.io/semvia/core/semantic-package#PackageRequirement",
      "package": "https://pkg.semvia.io/semvia/gleif/",
      "versionMinimum": "0.4.0"
    }
  ]
}
```

It requires [`party`](https://github.com/SemviaIO/party) 0.2.0, the hub its
alignment points into, so the installer fetches that too.

The connection descriptor, `https://pkg.semvia.io/semvia/gleif/connection#pkg-semvia-io`,
is an `svdb:BlobConnection` with no `svdb:accessKeyId`. That absence declares an
anonymous public bucket, read over HTTP at `svdb:endpoint`: there is no secret
to bind, so installing it raises no keychain prompt and asks for no consent.

## What it maps

| Source object | TriplesMap | Yields |
| --- | --- | --- |
| `@data/lei_records.parquet` | `LeiRecords` | one `gleif:LegalEntity` per LEI record |
| `@data/relationship_records.parquet` | `Relationships` | one reified `gleif:Relationship` per row |
| `@data/relationship_records.parquet` | `RelatedEntities` | one of six typed child-to-parent edges, chosen per row by the relationship type |

Each key is joined to the connection's `svdb:prefix`, `semvia/gleif/`, so the
objects are `https://pkg.semvia.io/semvia/gleif/@data/lei_records.parquet` and
`https://pkg.semvia.io/semvia/gleif/@data/relationship_records.parquet`.

Entities are subject-keyed on their LEI, at `https://gleif.org/lei/{lei}`, so an
entity has the same IRI whichever file it was read from.

```
schema/
  ontology.ttl             the classes and predicates
  connection.ttl           the public bucket (no credential)
  legal-entities.ttl       the Level 1 mapping
  relationships.ttl        the Level 2 reified mapping
  relationship-types.ttl   the six relationship types as a SKOS scheme, and the lookup over it
  related-entities.ttl     the Level 2 typed-edge mapping
  party-alignment.ttl      lattice edges into the party hub
tools/
  export-parquet.py        writes the two Parquet objects from the Postgres golden copy
```

The mappings are Turtle. Each logical source names its object with `svdb:key`,
which the Markdown mapping surface does not route. `related-entities.ttl` would
be Turtle regardless, and its header says why: its predicate is chosen per row
from a column, which the Markdown heading grammar cannot express.

## Physical layout

The Parquet layout is this package's physical structure, the way an index file
would be for a database source. It is laid out for a reader that fetches byte
ranges: rows sorted on the key a query binds, so row-group statistics prune; a
page index, so a point lookup reads one page rather than one row group; bloom
filters on the keys; and the sort order recorded in the footer. Each map
declares the same order with `svcat:declaredSortOrder`, so a query that asks for
it plans no sort.

| Object | Rows | Bytes | Row groups | Sorted by | Bloom filters |
| --- | ---: | ---: | ---: | --- | --- |
| `lei_records.parquet` | 3,390,198 | 101,222,073 | 12 | `lei` | `lei` |
| `relationship_records.parquet` | 482,824 | 5,869,457 | 2 | `relationship_startnode_nodeid`, `relationship_endnode_nodeid` | both node columns |

Row groups hold 300,000 rows. Both files carry a page index and are
zstd-compressed. Only the thirteen columns the mappings reference are exported.

`tools/export-parquet.py` regenerates both from the Postgres golden copy and
prints the counts, sizes, and footer check above. It takes the reader password
from `PGPASSWORD`, supplied as a per-invocation prefix; no credential appears in
the script or in this repository.

## The model

Two classes. `gleif:LegalEntity` is every row of the Level 1 golden copy, and
`gleif:Relationship` is a reified Level 2 relationship record.

There is no `Company` / `MutualFund` / `Branch` subclass ladder yet. The GLEIF
entity category rides as data on `gleif:entityCategory` instead: one source
yields one class for every row it carries, so a ladder would have been a lattice
nothing ever populates. A per-category filtered source would make the ladder
expressible, so it is tracked in
[#4](https://github.com/SemviaIO/gleif/issues/4) rather than ruled out.

The relationship types, by contrast, *do* split — not into classes but into
predicates. A `rml:predicateMap` can carry `rml:reference` plus a
`svrl:resolveVia` lookup, which makes the predicate a function of the
discriminator column: one file, one scan, six edges. Whether the engine
pushes the row condition into the Parquet scan or evaluates it as a residual is
not yet measured against the bucket. The vocabulary that decides which token
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

**No `sh:minCount` on any mapped property.** These shapes describe a virtual
graph over a source we do not control, and that source has nulls — 8,986 records
carry no entity status. A shape is documentation here, not a gate the source
could satisfy.

## Licence and attribution

Everything Semvia authored here is CC0 1.0 Universal — see `LICENSE`.

The data is GLEIF's. The package archive carries none of it; the two Parquet
objects its mappings read are a copy of GLEIF's golden copy that Semvia
publishes beside the archive in the `semvia-pkg` bucket. See `NOTICE` for the
source, GLEIF's terms of use, and what this package does and does not claim.
