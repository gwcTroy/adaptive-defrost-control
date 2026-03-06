#!/bin/bash

PROJECT_DIR="/opt/defrost-control"
PYTHON="$PROJECT_DIR/venv/bin/python"

cd $PROJECT_DIR

$PYTHON src/defrost_control/defrost_scheduler.py \
    >> logs/scheduler.log 2>&1