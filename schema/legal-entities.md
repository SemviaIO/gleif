# GLEIF Legal Entities

::[mappedBy](https://pkg.semvia.io/semvia/folio/mapping#mappedBy) RmlMappingMap

Projects the GLEIF Level 1 golden copy — `public.lei_records`, 3,390,198 rows and 338
columns in the `gleif` database — onto `gleif:LegalEntity`. One TriplesMap over the whole
relation, so one relation yields one class for every row it carries and the GLEIF entity
category rides as data on `gleif:entityCategory` rather than splitting the class. Now that
a logical source can carry SQL, a per-category split is expressible — see
[#4](https://github.com/SemviaIO/gleif/issues/4).

Nothing here copies data. The mapping is a description the federation engine registers as
a virtual table; every read is answered by Postgres at query time.

> **Column names.** Six of the columns below are confirmed against the live relation.
> The rest are derived from the GLEIF golden-copy CSV header by the rule the confirmed
> six all obey — lowercase the header, replace `.` with `_` — and are marked
> `derived, unverified` where they appear. The blast radius is bounded and per-column: a
> mapped column that is not in the delivered schema declines on its own and leaves the
> rest of the TriplesMap intact, so an unverified name costs at most its own predicate.
> Verifying them against the live schema is step 4 of the plan and is not done here.

The iterator below is `public.lei_records`, schema-qualified. `gleif` is the DATABASE
name, not a schema — `gleif.lei_records` resolves to no relation, and a relation
reference that resolves to nothing registers with an empty Arrow schema, which the
federation engine refuses.

## LeiRecords

One legal entity per LEI record, subject-keyed on the LEI itself. Every row, every entity
category — the category is carried as data rather than as a class.

::[source](http://w3id.org/rml/source) [semvia-test-data](connection#semvia-test-data)
::[referenceFormulation](http://w3id.org/rml/referenceFormulation) [SQL2008Table](http://w3id.org/rml/SQL2008Table)
::[iterator](http://w3id.org/rml/iterator) "public.lei_records"
::[template](http://w3id.org/rml/template) "https://gleif.org/lei/{lei}"
::[class](http://w3id.org/rml/class) [LegalEntity](ontology#LegalEntity)

### lei

The ISO 17442 identifier, also the key the subject IRI is minted from. Confirmed column.

::[reference](http://w3id.org/rml/reference) "lei"

### legalName

The registered legal name in the local alphabet. Confirmed column.

::[reference](http://w3id.org/rml/reference) "entity_legalname"

### entityCategory

GENERAL, FUND, SOLE_PROPRIETOR, RESIDENT_GOVERNMENT_ENTITY, BRANCH, or
INTERNATIONAL_ORGANIZATION — the discriminator that would have been a subclass ladder if
the source could be filtered. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "entity_entitycategory"

### entityStatus

ACTIVE or INACTIVE. Confirmed column, and confirmed nullable — 8,986 rows carry no value,
which is why no shape in the ontology puts an `sh:minCount` on it.

::[reference](http://w3id.org/rml/reference) "entity_entitystatus"

### legalJurisdiction

The ISO 3166 jurisdiction of formation, e.g. `US-DE`, as the literal token the column
holds rather than a jurisdiction IRI. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "entity_legaljurisdiction"

### legalForm

The four-character ELF code. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "entity_legalform_entitylegalformcode"

### legalAddressCountry

ISO 3166 country of the registered legal address. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "entity_legaladdress_country"

### legalAddressCity

City of the registered legal address. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "entity_legaladdress_city"

### registrationStatus

The LEI registration's own lifecycle status — ISSUED, LAPSED, RETIRED and friends —
which is about the registration rather than the entity, and so is distinct from
`gleif:entityStatus`. Derived, unverified.

::[reference](http://w3id.org/rml/reference) "registration_registrationstatus"
