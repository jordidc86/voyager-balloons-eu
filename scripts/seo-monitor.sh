#!/bin/sh
set -eu

PYTHON="${SEO_MONITOR_PYTHON:-python3}"
if [ -x ".venv-seo-monitor/bin/python" ]; then
  PYTHON=".venv-seo-monitor/bin/python"
fi

if [ "${1:-}" = "test" ]; then
  shift
  exec "$PYTHON" -m unittest discover -s tests -p 'test_*.py' "$@"
fi

exec "$PYTHON" -m seo_monitor "$@"
