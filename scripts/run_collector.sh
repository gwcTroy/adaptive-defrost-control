#!/bin/bash

PROJECT_DIR="/opt/defrost-control"
PYTHON="$PROJECT_DIR/venv/bin/python"

cd $PROJECT_DIR

$PYTHON src/defrost_control/defrost_event_collector.py \
    >> logs/collector.log 2>&1