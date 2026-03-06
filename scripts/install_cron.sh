#!/bin/bash

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)

COLLECTOR="*/5 * * * * $PROJECT_DIR/scripts/run_collector.sh"
UPDATER="3 * * * * $PROJECT_DIR/scripts/run_updater.sh"
SCHEDULER="5 * * * * $PROJECT_DIR/scripts/run_scheduler.sh"

(crontab -l 2>/dev/null | grep -v defrost_control; \
 echo "$COLLECTOR"; \
 echo "$UPDATER"; \
 echo "$SCHEDULER") | crontab -

echo "Installed cron jobs:"
crontab -l