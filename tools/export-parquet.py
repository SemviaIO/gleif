#!/usr/bin/env python3
"""Export the mapped GLEIF columns from Postgres to Parquet laid out for pruning.

Writes the full golden copy into this package's `data/`, which `sem package`
bundles into the archive:

    data/lei_records.parquet
    data/relationship_records.parquet

With `--groups-out`, it also writes the corporate-group cut that SemviaIO/gleif-groups
bundles — every relationship row, plus every legal entity that is a start or end
node of one:

    <groups-out>/lei_records.parquet
    <groups-out>/relationship_records.parquet

Only the thirteen columns the package's mappings reference are exported. The
layout is chosen for a reader that fetches byte ranges: rows sorted on
the join key so row-group min/max statistics prune, a page index so a point
lookup reads one page rather than one row group, a bloom filter on each key a
query binds, and the sort order recorded in the footer.

The credential never reaches this script's arguments or source. `psql` reads
`PGPASSWORD` from the environment the caller hands it, so supply it as a
per-invocation prefix:

    PGPASSWORD="$(op read 'op://development/<item>/password')" \\
        python3 tools/export-parquet.py --groups-out ../gleif-groups/data

Requires `psql` on PATH and `pyarrow` >= 19 (per-column bloom filter options).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pcsv
import pyarrow.parquet as pq

# The semvia-test-data Neon project the 0.3.0 descriptor pointed at. None of
# these is secret; the password is the only credential and it arrives through
# the environment.
DEFAULT_HOST = "ep-small-block-aymhbzd3.c-5.us-east-2.aws.neon.tech"
DEFAULT_PORT = "5432"
DEFAULT_DATABASE = "gleif"
DEFAULT_USER = "reader"

PACKAGE_DATA = Path(__file__).resolve().parent.parent / "data"

LEI_COLUMNS = [
    "lei",
    "entity_legalname",
    "entity_entitycategory",
    "entity_entitystatus",
    "entity_legaljurisdiction",
    "entity_legalform_entitylegalformcode",
    "entity_legaladdress_country",
    "entity_legaladdress_city",
    "registration_registrationstatus",
]
LEI_SORT = ["lei"]
LEI_BLOOM = ["lei"]

RELATIONSHIP_COLUMNS = [
    "relationship_startnode_nodeid",
    "relationship_endnode_nodeid",
    "relationship_relationshiptype",
    "relationship_relationshipstatus",
]
RELATIONSHIP_SORT = ["relationship_startnode_nodeid", "relationship_endnode_nodeid"]
RELATIONSHIP_BLOOM = ["relationship_startnode_nodeid", "relationship_endnode_nodeid"]

ROW_GROUP_SIZE = 300_000
BLOOM_FPP = 0.01


def fetch(conninfo: str, relation: str, columns: list[str]) -> pa.Table:
    """Stream one relation out of Postgres as CSV and parse it into Arrow."""
    select = f"SELECT {', '.join(columns)} FROM {relation}"
    command = ["psql", conninfo, "-X", "-v", "ON_ERROR_STOP=1", "-c", f"\\copy ({select}) TO STDOUT WITH (FORMAT csv, HEADER true)"]
    with subprocess.Popen(command, stdout=subprocess.PIPE) as proc:
        assert proc.stdout is not None
        table = pcsv.read_csv(
            proc.stdout,
            convert_options=pcsv.ConvertOptions(
                column_types={name: pa.string() for name in columns},
                # psql writes NULL as an unquoted empty field and an empty
                # string as `""`, so only the unquoted form is a null.
                strings_can_be_null=True,
                quoted_strings_can_be_null=False,
            ),
        )
    if proc.returncode != 0:
        sys.exit(f"psql exited {proc.returncode} reading {relation}")
    return table


def write(table: pa.Table, path: Path, sort: list[str], bloom: list[str]) -> None:
    table = table.sort_by([(name, "ascending") for name in sort])
    # Each bloom filter is per column chunk, so it sizes to one row group's
    # distinct values, not the whole file's.
    ndv = max(1, min(table.num_rows, ROW_GROUP_SIZE))
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        row_group_size=ROW_GROUP_SIZE,
        compression="zstd",
        write_statistics=True,
        write_page_index=True,
        sorting_columns=pq.SortingColumn.from_ordering(table.schema, [(name, "ascending") for name in sort]),
        bloom_filter_options={name: {"ndv": ndv, "fpp": BLOOM_FPP} for name in bloom},
    )


def check(path: Path, sort: list[str], bloom: list[str]) -> bool:
    """Print the row count, size and footer layout of one file; return whether the layout holds."""
    meta = pq.ParquetFile(path).metadata
    names = [meta.schema.column(i).name for i in range(meta.num_columns)]
    ok = True
    sorted_on: list[str] = []
    page_index = True
    bloom_present = {name: True for name in bloom}
    for g in range(meta.num_row_groups):
        group = meta.row_group(g)
        ordering = [names[c.column_index] for c in (group.sorting_columns or ())]
        if g == 0:
            sorted_on = ordering
        elif ordering != sorted_on:
            ok = False
        for c in range(group.num_columns):
            column = group.column(c)
            page_index = page_index and column.has_column_index and column.has_offset_index
            if column.path_in_schema in bloom_present and column.bloom_filter_offset is None:
                bloom_present[column.path_in_schema] = False
    ok = ok and sorted_on == sort and page_index and all(bloom_present.values())
    print(f"{path}")
    print(f"  rows            {meta.num_rows:,}")
    print(f"  bytes           {path.stat().st_size:,}")
    print(f"  row groups      {meta.num_row_groups}")
    print(f"  sorting_columns {', '.join(sorted_on) or '(none)'}")
    print(f"  page index      {'present' if page_index else 'MISSING'}")
    for name, present in bloom_present.items():
        print(f"  bloom {name:<30} {'present' if present else 'MISSING'}")
    print(f"  layout          {'ok' if ok else 'FAILED'}")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=PACKAGE_DATA)
    parser.add_argument("--groups-out", type=Path)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--user", default=DEFAULT_USER)
    args = parser.parse_args()

    if not os.environ.get("PGPASSWORD"):
        sys.exit("PGPASSWORD is not set; pass it as a per-invocation prefix (see --help)")

    conninfo = f"host={args.host} port={args.port} dbname={args.database} user={args.user} sslmode=verify-full sslrootcert=system"

    lei = fetch(conninfo, "public.lei_records", LEI_COLUMNS)
    relationships = fetch(conninfo, "public.relationship_records", RELATIONSHIP_COLUMNS)

    outputs = [
        (lei, args.out / "lei_records.parquet", LEI_SORT, LEI_BLOOM),
        (relationships, args.out / "relationship_records.parquet", RELATIONSHIP_SORT, RELATIONSHIP_BLOOM),
    ]
    if args.groups_out is not None:
        endpoints = pc.unique(
            pa.chunked_array(
                relationships["relationship_startnode_nodeid"].chunks + relationships["relationship_endnode_nodeid"].chunks
            )
        )
        group_lei = lei.filter(pc.is_in(lei["lei"], value_set=endpoints))
        outputs += [
            (group_lei, args.groups_out / "lei_records.parquet", LEI_SORT, LEI_BLOOM),
            (relationships, args.groups_out / "relationship_records.parquet", RELATIONSHIP_SORT, RELATIONSHIP_BLOOM),
        ]
    for table, path, sort, bloom in outputs:
        write(table, path, sort, bloom)

    results = [check(path, sort, bloom) for _, path, sort, bloom in outputs]
    if not all(results):
        sys.exit("footer check failed")


if __name__ == "__main__":
    main()
