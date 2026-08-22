# GLEIF Relationships

::[mappedBy](https://pkg.semvia.io/semvia/folio/mapping#mappedBy) RmlMappingMap

Projects the GLEIF Level 2 golden copy — `public.relationship_records`, 482,824 rows and
54 columns in the `gleif` database — onto RDF twice, from the same relation.

`Relationships` is the accurate reading: one reified `gleif:Relationship` node per row,
carrying which entity stands in which relationship to which other. `RelatedEntities` is
the flattened reading of the same row: a direct `gleif:relatedEntity` edge from child to
parent, which is the single-hop property path an ownership-closure query walks as
`gleif:relatedEntity+`.

Two TriplesMaps over one physical table is deliberate and supported — the federation
engine keys a registered table on the TriplesMap's local name, not on the relation, so
`Relationships` and `RelatedEntities` register as two tables over the same Postgres
relation.

> **The flattened edge unions all six relationship types.** `IS_ULTIMATELY_CONSOLIDATED_BY`,
> `IS_DIRECTLY_CONSOLIDATED_BY`, `IS_FUND-MANAGED_BY`, `IS_SUBFUND_OF`, `IS_FEEDER_TO` and
> `IS_INTERNATIONAL_BRANCH_OF` all become the same `gleif:relatedEntity` edge, because a
> relational logical source cannot filter rows. A closure over it therefore walks
> fund-management and branch edges alongside consolidation ones. A query that means
> consolidation specifically reads the reified `gleif:Relationship` node and narrows on
> `gleif:relationshipType`; that is what the first TriplesMap is for.

> **Column names.** The three `relationship_*` node and type columns are confirmed
> against the live relation; `relationship_relationshipstatus` is derived from the GLEIF
> CSV header by the same lowercase-and-underscore rule and marked below. A mapped column
> absent from the delivered schema declines on its own without breaking the TriplesMap.

> **No relationship period.** GLEIF carries validity dates as
> `Relationship.RelationshipPeriods.N.{StartDate,EndDate,PeriodType}`, where `N` is a
> positional slot whose period type is not stable across rows — slot 1 is the
> relationship period on some rows and the accounting or document-filing period on
> others. Mapping a positional slot to a named predicate would therefore assert a
> confidently wrong triple rather than an absent one, so the period is left unmapped
> until a filtered logical source can select on `PeriodType`.

## Relationships

One reified relationship node per row, subject-keyed on the RR-CDF natural key: the two
endpoint LEIs and the relationship type, which together identify a relationship record.

::[source](http://w3id.org/rml/source) [semvia-test-data](connection#semvia-test-data)
::[referenceFormulation](http://w3id.org/rml/referenceFormulation) [SQL2008Table](http://w3id.org/rml/SQL2008Table)
::[iterator](http://w3id.org/rml/iterator) "public.relationship_records"
::[template](http://w3id.org/rml/template) "https://gleif.org/relationship/{relationship_startnode_nodeid}-{relationship_endnode_nodeid}-{relationship_relationshiptype}"
::[class](http://w3id.org/rml/class) [Relationship](ontology#Relationship)

### startNode

The child entity — the one that is consolidated, managed, or branched from. A template,
so the object is an IRI joining the entity minted by the `LeiRecords` map. Confirmed
column.

::[template](http://w3id.org/rml/template) "https://gleif.org/lei/{relationship_startnode_nodeid}"

### endNode

The parent entity. Confirmed column.

::[template](http://w3id.org/rml/template) "https://gleif.org/lei/{relationship_endnode_nodeid}"

### relationshipType

The GLEIF relationship type token. Confirmed column, and the predicate a query narrows on
when it means one specific kind of relationship.

::[reference](http://w3id.org/rml/reference) "relationship_relationshiptype"

### relationshipStatus

ACTIVE or INACTIVE — whether the relationship itself still holds, as distinct from
whether either endpoint entity does. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "relationship_relationshipstatus"

## RelatedEntities

The same rows read as a direct child-to-parent edge. The subject is the child entity
itself — the same IRI the LeiRecords map mints — so the edge lands on the legal entity
rather than on a relationship node, and a closure query needs no reification hop.

::[source](http://w3id.org/rml/source) [semvia-test-data](connection#semvia-test-data)
::[referenceFormulation](http://w3id.org/rml/referenceFormulation) [SQL2008Table](http://w3id.org/rml/SQL2008Table)
::[iterator](http://w3id.org/rml/iterator) "public.relationship_records"
::[template](http://w3id.org/rml/template) "https://gleif.org/lei/{relationship_startnode_nodeid}"
::[class](http://w3id.org/rml/class) [LegalEntity](ontology#LegalEntity)

Typing the subject as a legal entity here is not a second, weaker definition of the
class — it is the same entity, asserted from a second relation, and it is true of every
row: an endpoint of a GLEIF relationship record is by construction an entity in the
register.

### relatedEntity

The parent entity. All six relationship types collapse onto this one edge; see the
caveat above.

::[template](http://w3id.org/rml/template) "https://gleif.org/lei/{relationship_endnode_nodeid}"
