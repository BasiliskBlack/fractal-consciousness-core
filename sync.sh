#!/bin/bash
# ShotNET Repository Sync Script
# This script ensures the repository is up to date before any operations

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Run the sync script
python3 "$REPO_DIR/scripts/sync_repo.py" "$REPO_DIR"

# Continue with the original command if provided
if [ $# -gt 0 ]; then
    echo "\n🚀 Executing: $@"
    echo "-"$(printf '=%.0s' {1..48})
    exec "$@"
fi
