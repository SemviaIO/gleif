-- Physical structure for the relations this package's mappings project.
--
-- This file is a TRANSCRIPT, not a proposal. Every index below already exists
-- on the `gleif` database in the semvia-test-data Neon instance, verified
-- against `pg_indexes` on 2026-08-22. It is committed here because a semantic
-- package that describes a relation's MEANING and says nothing about its
-- PHYSICAL LAYOUT ships half a description: the federation engine's pushdown
-- planner assumes a relational source prunes on an indexed key
-- (`PushdownProfile`, crates/vkg-federation/src/federation/capability.rs), and
-- it has no way to learn which columns those are. Recording them makes the
-- assumption auditable and makes the drift visible when it happens.
--
-- Every statement is IF NOT EXISTS, so applying this to the live database is a
-- no-op today. It is not a migration; it is the answer to "what does this
-- package need to be true of its source for the demo queries to hold their
-- latency budget."
--
-- See SemviaIO/SemviaIO#5152 for the open design question this file stands in
-- for: physical structure belongs in the modelling→ingest pipeline as declared
-- metadata, not as hand-applied DDL that a package transcribes after the fact.

-- ---------------------------------------------------------------------------
-- public.lei_records — 3,390,198 rows, 338 columns (GLEIF Level 1 golden copy)
-- ---------------------------------------------------------------------------

-- The subject key. `LeiRecords` mints its subject IRI from `{lei}`, and every
-- relationship endpoint below joins back to this column to resolve an entity's
-- attributes. UNIQUE because the LEI is the ISO 17442 identifier and the golden
-- copy carries one row per LEI — the uniqueness is a fact about the source, and
-- declaring it lets the planner treat the join as key-preserving rather than
-- assuming fan-out.
CREATE UNIQUE INDEX IF NOT EXISTS idx_lei
  ON public.lei_records USING btree (lei);

-- Name lookup, two indexes for two different questions.
--
-- The btree with `text_pattern_ops` answers anchored prefix search — "every
-- entity whose name starts with ACME" — which is the shape a type-ahead in the
-- demo produces. `lower(...)` because the search is case-insensitive and an
-- index on the raw column cannot serve a lowered predicate.
CREATE INDEX IF NOT EXISTS idx_lei_name
  ON public.lei_records USING btree (lower(entity_legalname) text_pattern_ops);

-- The GIN trigram index answers UNANCHORED and fuzzy match — "anything like
-- ACME Holdings" — which the btree cannot serve at any selectivity. This is the
-- one that makes the demo's entity-resolution beat feel instant over 3.4M rows;
-- without it that query is a sequential scan of a 338-column relation.
-- Requires the pg_trgm extension.
CREATE INDEX IF NOT EXISTS idx_lei_name_trgm
  ON public.lei_records USING gin (lower(entity_legalname) gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- public.relationship_records — GLEIF Level 2 ("who owns whom")
-- ---------------------------------------------------------------------------
--
-- These three are the ones that matter most, and the reason is structural
-- rather than a matter of degree. An ownership-chain walk is ITERATED: each hop
-- looks up the next endpoint by the previous hop's node id. Unindexed, every
-- hop is a sequential scan and the cost multiplies by chain depth — so the
-- query the flagship demo is built around is precisely the query that degrades
-- worst. Indexed, each hop is a btree probe and depth costs what it should.

-- Downward walk: given an entity, who does it report as its parent/manager?
-- `Relationships` and `RelatedEntities` both key their subject template on this
-- column, so it is the entry point for every Level 2 read.
CREATE INDEX IF NOT EXISTS idx_rr_start
  ON public.relationship_records USING btree (relationship_startnode_nodeid);

-- Upward walk: given an entity, who reports IT as their parent? This is the
-- direction the "show me everything this ultimate parent controls" query runs,
-- and it has no other access path — the start-node index cannot serve it.
CREATE INDEX IF NOT EXISTS idx_rr_end
  ON public.relationship_records USING btree (relationship_endnode_nodeid);

-- The discriminator. `gleif:relatedEntity` deliberately unions all six GLEIF
-- relationship types (IS_DIRECTLY_CONSOLIDATED_BY, IS_ULTIMATELY_CONSOLIDATED_BY,
-- IS_FUND-MANAGED_BY, IS_SUBFUND_OF, IS_FEEDER_TO, IS_INTERNATIONAL_BRANCH_OF)
-- because an RML logical source over a relational connection cannot filter rows
-- — see schema/relationships.md. So the DISTINCTION between an ownership edge
-- and a fund-management edge is drawn by the reading query, not by the mapping,
-- which makes this column a filter on the hot path rather than a rarely-touched
-- attribute.
CREATE INDEX IF NOT EXISTS idx_rr_type
  ON public.relationship_records USING btree (relationship_relationshiptype);
