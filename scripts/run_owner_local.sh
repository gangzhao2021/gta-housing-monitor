#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .streamlit/owner_auth.env ]; then
  echo 'Run scripts/setup_owner_password.py first.' >&2
  exit 1
fi
set -a
. ./.streamlit/owner_auth.env
set +a
export HOUSING_REQUIRE_OWNER_AUTH=1
exec .venv/bin/streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
