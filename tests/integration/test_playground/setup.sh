#!/bin/bash
# Setup script for mem integration tests
# Creates a sample project structure with various file types

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/sample_project"

echo "=== Setting up test playground ==="

# Clean up existing project
if [ -d "$PROJECT_DIR" ]; then
    echo "Removing existing project directory..."
    rm -rf "$PROJECT_DIR"
fi

# Create project structure
echo "Creating project directory structure..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/src/lib"
mkdir -p "$PROJECT_DIR/docs"
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/.hidden_dir"

# Create normal files
echo "Creating normal files..."
cat > "$PROJECT_DIR/README.md" << 'EOF'
# Sample Project

This is a test project for mem integration testing.

## Features
- File tracking
- Snapshot management
- Ignore patterns
EOF

echo "This is a normal text file." > "$PROJECT_DIR/normal.txt"
touch "$PROJECT_DIR/empty.txt"
echo "Another test file" > "$PROJECT_DIR/another.txt"
echo "Test file 2" > "$PROJECT_DIR/test2.txt"

cat > "$PROJECT_DIR/Makefile" << 'EOF'
.PHONY: all clean

all:
	@echo "Building project..."

clean:
	@echo "Cleaning..."
EOF

# Create source files
echo "Creating source files..."
cat > "$PROJECT_DIR/src/main.py" << 'EOF'
"""Main application entry point."""

def main():
    print("Hello from mem test!")

if __name__ == "__main__":
    main()
EOF

cat > "$PROJECT_DIR/src/utils.py" << 'EOF'
"""Utility functions."""

def helper_function():
    return "Helper result"
EOF

cat > "$PROJECT_DIR/src/lib/helper.py" << 'EOF'
"""Library helper functions."""

class Helper:
    def __init__(self):
        pass
EOF

# Create documentation
echo "Creating documentation files..."
cat > "$PROJECT_DIR/docs/guide.md" << 'EOF'
# User Guide

Welcome to the user guide.
EOF

cat > "$PROJECT_DIR/docs/api.md" << 'EOF'
# API Documentation

API reference documentation.
EOF

# Create data files
echo "Creating data files..."
cat > "$PROJECT_DIR/data/config.json" << 'EOF'
{
  "name": "test-project",
  "version": "1.0.0"
}
EOF

cat > "$PROJECT_DIR/data/settings.yaml" << 'EOF'
app:
  name: "Test App"
  debug: true
EOF

# Create hidden files (should be ignored by default)
echo "Creating hidden files..."
echo "This should be ignored" > "$PROJECT_DIR/.hidden_file.txt"
echo "Secret content" > "$PROJECT_DIR/.hidden_dir/secret.txt"
echo "Environment variables" > "$PROJECT_DIR/.env"

echo ""
echo "=== Setup complete ==="
echo "Project created at: $PROJECT_DIR"
echo ""
echo "Directory structure:"
cd "$PROJECT_DIR" && find . -type f | sort
echo ""
echo "Run './run_tests.sh' to execute tests"
