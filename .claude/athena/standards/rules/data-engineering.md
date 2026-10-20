---
globs: ["**/pipelines/**", "**/etl/**", "**/data/**", "**/scripts/**/*.py", "**/tasks/**"]
---
# Data engineering constraints

## Infrastructure
EC2 t3.large: 2 vCPU, 8GB RAM. PostgreSQL RDS is the compute engine. Python orchestrates only.

## Before any data code
Run: `SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;`

## Scale decision tree
- Under 1K rows: anything works
- 1K–100K: pandas vectorized only (no apply, no iterrows)
- 100K–1M: SQL with aggregation, window functions, CTEs
- Over 1M: SQL with indexes. EXPLAIN ANALYZE before shipping

## Banned (commit hook blocks these)
- `df.iterrows()` — vectorize or SQL
- `df.apply(lambda)` on >1K rows
- `pd.read_sql("SELECT * FROM large_table")` without WHERE
- Loading tables into Python for GROUP BY/JOIN — use SQL
- `pd.read_csv()` on >100MB without chunking

## Required
- `COPY` or `to_sql(method='multi', chunksize=5000)` for bulk inserts
- WHERE clauses on date ranges for historical queries
- Row count before and after every transform
- Server-side cursors for large results, never fetchall()
