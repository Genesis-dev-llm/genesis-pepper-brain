#!/bin/bash
# Script to run GENESIS Pepper Middleware Brain

echo "Starting GENESIS Pepper Middleware Brain..."

# Find the Python interpreter in the current environment or default to 'python'
PYTHON_EXEC="python"
if [ -d "venv" ]; then
    PYTHON_EXEC="venv/bin/python"
fi
# Execute the main application
exec $PYTHON_EXEC main.py