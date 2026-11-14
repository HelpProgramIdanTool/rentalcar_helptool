#!/usr/bin/env bash
set -o errexit
uv sync --frozen
uv run python scripts/compile_operator_messages.py
uv run python manage.py collectstatic --noinput
uv run python manage.py check --deploy --fail-level WARNING
