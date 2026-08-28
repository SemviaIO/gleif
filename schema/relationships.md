# GLEIF Relationships

::[mappedBy](https://pkg.semvia.io/semvia/folio/mapping#mappedBy) RmlMappingMap

Projects the GLEIF Level 2 golden copy — `public.relationship_records`, 482,824 rows and
54 columns in the `gleif` database — onto RDF twice, from the same relation.

This document holds the first reading: one reified `gleif:Relationship` node per row,
carrying which entity stands in which relationship to which other, plus the relationship's
own status. The second reading — the same row as a typed child-to-parent edge on the
entity — lives in [`related-entities.ttl`](related-entities.ttl), which is the one mapping
in this package authored in Turtle rather than Markdown. That file opens with why.

Two TriplesMaps over one physical table is deliberate and supported — the federation
engine keys a registered table on the TriplesMap's local name, not on the relation, so
`Relationships` and `RelatedEntities` register as two tables over the same Postgres
relation.

> **Read this one when you want the relationship, not the edge.** A reified node is the
> only place `gleif:relationshipStatus` lives, and the only reading that survives GLEIF
> adding facts about a relationship rather than about its endpoints. If all you want is
> the ownership chain, walk the typed edges instead — they carry the relationship type in
> the predicate, so a closure over `gleif:directlyConsolidatedBy+` no longer drags
> fund-management and branch edges along with it.

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
