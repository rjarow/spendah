#!/bin/bash
set -e

cd "$(dirname "$0")/.."

if [ -d "backend/.venv" ]; then
    source backend/.venv/bin/activate
else
    echo "No .venv found, using system Python"
fi

cd backend
exec pytest "$@"
