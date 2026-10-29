#!/usr/bin/env bash
set -o errexit
uv sync --frozen
uv run python manage.py collectstatic --noinput
uv run python manage.py check --deploy --fail-level WARNING
