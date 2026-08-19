#!/bin/sh
set -eu
pg_isready -U pm_kernel -d pm_kernel >/dev/null
test "$(psql -v ON_ERROR_STOP=1 -At -U pm_kernel -d pm_kernel \
  -c 'SELECT 1 FROM context.schema_migrations WHERE version=1')" = 1
