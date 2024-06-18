#!/usr/bin/env sh

set -x

# Runs the export now and then every 6 hours
while true; do
  .venv/bin/python -m librechat_stats
  sleep 21600
done
