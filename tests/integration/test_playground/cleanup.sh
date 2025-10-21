#!/bin/bash
# Cleanup script for mem integration tests
# Removes all test artifacts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/sample_project"

echo "=== Cleaning up test playground ==="

# Remove sample project directory
if [ -d "$PROJECT_DIR" ]; then
    echo "Removing sample_project directory..."
    rm -rf "$PROJECT_DIR"
    echo "✓ Sample project removed"
else
    echo "No sample_project directory found"
fi

# Remove log files
echo "Removing log files..."
rm -f "$SCRIPT_DIR"/*.log "$SCRIPT_DIR"/*.txt
echo "✓ Log files removed"

echo ""
echo "✓ Cleanup complete"
echo ""
echo "To run tests again:"
echo "  1. ./setup.sh"
echo "  2. ./run_tests.sh"
