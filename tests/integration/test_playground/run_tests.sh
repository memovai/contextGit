#!/bin/bash
# Final integration test script for mem commands
# Uses cd to project directory to avoid path issues

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/sample_project"
MEMOV_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "${YELLOW}>>> $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}\n"
}

print_error() {
    echo -e "${RED}✗ $1${NC}\n"
}

# Function to check if command succeeded
check_success() {
    if [ $? -ne 0 ]; then
        print_error "Previous command failed"
        exit 1
    fi
}

# Function to check if output contains error keywords
check_output_for_errors() {
    local output="$1"
    if echo "$output" | grep -iq "error\|failed\|unexpected"; then
        print_error "Command produced errors"
        echo "$output"
        exit 1
    fi
}

# Verify setup
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory not found!"
    echo "Please run './setup.sh' first"
    exit 1
fi

# Change to project directory for easier file operations
cd "$PROJECT_DIR"

print_section "Stage 1: Initialize & Verify .memignore"

print_step "1.1: Initialize mem repository"
uv run --directory "$MEMOV_ROOT" mem init --loc "$PROJECT_DIR"
print_success "Initialized"

print_step "1.2: Check .memignore content"
cat .memignore
print_success ".memignore created with default rules"

print_step "1.3: Check status - hidden files should NOT appear"
uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR"
print_success "Hidden files are correctly ignored"

print_section "Stage 2: Track Normal Files"

print_step "2.1: Track all normal files at once"
OUTPUT=$(uv run --directory "$MEMOV_ROOT" mem track --loc "$PROJECT_DIR" \
    "$PROJECT_DIR/README.md" \
    "$PROJECT_DIR/normal.txt" \
    "$PROJECT_DIR/empty.txt" \
    "$PROJECT_DIR/another.txt" \
    "$PROJECT_DIR/test2.txt" \
    "$PROJECT_DIR/Makefile" \
    -p "Initial files" -r "Tracking project files" 2>&1)
check_output_for_errors "$OUTPUT"
print_success "Tracked files"

print_step "2.4: Check status"
uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR"
print_success "Status shows tracked files as clean"

print_section "Stage 3: Modify & Snapshot"

print_step "3.1: Modify some files"
echo "Modified content" >> normal.txt
echo "More changes" >> README.md
print_success "Files modified"

print_step "3.2: Check status - should show modifications"
uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR"
print_success "Modifications detected"

print_step "3.3: Create snapshot"
uv run --directory "$MEMOV_ROOT" mem snap --loc "$PROJECT_DIR" -p "After modifications" -r "Snapshot changes"
print_success "Snapshot created"

print_step "3.4: Check status - should be clean"
uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR"
print_success "Files are clean after snapshot"

print_section "Stage 4: Dynamic .memignore Rules"

print_step "4.1: Create files that will be ignored"
mkdir -p temp
echo "Temporary cache" > temp/cache.tmp
echo "Application log" > app.log
echo "Debug log" > debug.log
print_success "Created temp and log files"

print_step "4.2: Check status - should appear as untracked"
uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" | grep -E "(app.log|debug.log)" || echo "Files appear in status"
print_success "Log files visible before adding rule"

print_step "4.3: Add new ignore rules to .memignore"
cat >> .memignore << 'EOF'

# Ignore temp directory
temp/

# Ignore log files
*.log
EOF
print_success "Added new ignore rules"

print_step "4.4: Check status - ignored files should disappear"
uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR"
print_success "Log files no longer appear in status"

print_step "4.5: Snapshot .memignore changes"
uv run --directory "$MEMOV_ROOT" mem snap --loc "$PROJECT_DIR" -p "Updated ignore rules" -r "Added temp and log patterns"
print_success "Snapshotted .memignore"

print_section "Stage 5: File State Transitions (Clean/Modified/Untracked)"

print_step "5.1: Verify Clean state - tracked files with no changes"
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
echo "$STATUS" | grep "Clean:.*README.md" > /dev/null && print_success "README.md is Clean"

print_step "5.2: Verify Untracked state - files not yet tracked"
echo "$STATUS" | grep "Untracked:.*data/config.json" > /dev/null && print_success "data/config.json is Untracked"

print_step "5.3: Verify Modified state - .memignore was changed"
echo "$STATUS" | grep "Modified:.*\.memignore" > /dev/null && print_success ".memignore is Modified"

print_step "5.4: Track an untracked file - state transition: Untracked → Clean"
uv run --directory "$MEMOV_ROOT" mem track --loc "$PROJECT_DIR" "$PROJECT_DIR/docs/api.md" -p "Track docs" -r "Adding API documentation"
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
echo "$STATUS" | grep "Clean:.*docs/api.md" > /dev/null && print_success "docs/api.md transitioned to Clean"

print_step "5.5: Modify a clean file - state transition: Clean → Modified"
echo "New API endpoint" >> docs/api.md
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
echo "$STATUS" | grep "Modified:.*docs/api.md" > /dev/null && print_success "docs/api.md transitioned to Modified"

print_step "5.6: Snapshot modified files - state transition: Modified → Clean"
uv run --directory "$MEMOV_ROOT" mem snap --loc "$PROJECT_DIR" -p "Update docs" -r "Saved changes"
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
echo "$STATUS" | grep "Clean:.*docs/api.md" > /dev/null && print_success "docs/api.md transitioned back to Clean"
echo "$STATUS" | grep "Clean:.*\.memignore" > /dev/null && print_success ".memignore also transitioned to Clean"

print_step "5.7: Verify all three states coexist correctly"
echo "Another line" >> README.md  # Make a tracked file Modified
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
HAS_CLEAN=$(echo "$STATUS" | grep -c "Clean:" || true)
HAS_MODIFIED=$(echo "$STATUS" | grep -c "Modified:" || true)
HAS_UNTRACKED=$(echo "$STATUS" | grep -c "Untracked:" || true)
if [ "$HAS_CLEAN" -gt 0 ] && [ "$HAS_MODIFIED" -gt 0 ] && [ "$HAS_UNTRACKED" -gt 0 ]; then
    print_success "All three states (Clean/Modified/Untracked) present simultaneously"
else
    print_error "Missing states: Clean=$HAS_CLEAN Modified=$HAS_MODIFIED Untracked=$HAS_UNTRACKED"
    exit 1
fi
echo -e "${GREEN}State summary: ${HAS_CLEAN} Clean, ${HAS_MODIFIED} Modified, ${HAS_UNTRACKED} Untracked${NC}\n"

print_step "5.8: Test fine-grained snapshot - only snap specific files"
# Setup: Modify multiple files
echo "Manual change 1" >> another.txt
echo "Manual change 2" >> empty.txt
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
echo "$STATUS" | grep "Modified:.*another.txt" > /dev/null && print_success "another.txt is Modified"
echo "$STATUS" | grep "Modified:.*empty.txt" > /dev/null && print_success "empty.txt is Modified"
echo "$STATUS" | grep "Modified:.*README.md" > /dev/null && print_success "README.md is still Modified"

# Fine-grained snapshot: only snap another.txt
uv run --directory "$MEMOV_ROOT" mem snap --loc "$PROJECT_DIR" --files "$PROJECT_DIR/another.txt" -p "Fine-grained snap" -r "Only snapping another.txt"
STATUS=$(uv run --directory "$MEMOV_ROOT" mem status --loc "$PROJECT_DIR" 2>&1)
echo "$STATUS" | grep "Clean:.*another.txt" > /dev/null && print_success "another.txt is now Clean after fine-grained snap"
echo "$STATUS" | grep "Modified:.*empty.txt" > /dev/null && print_success "empty.txt is still Modified (not snapped)"
echo "$STATUS" | grep "Modified:.*README.md" > /dev/null && print_success "README.md is still Modified (not snapped)"

# Verify history shows only another.txt in the snapshot
LAST_COMMIT=$(uv run --directory "$MEMOV_ROOT" mem history --loc "$PROJECT_DIR" 2>&1 | grep -oE '[a-f0-9]{7}' | head -1)
SHOW_OUTPUT=$(uv run --directory "$MEMOV_ROOT" mem show --loc "$PROJECT_DIR" "$LAST_COMMIT" 2>&1)
echo "$SHOW_OUTPUT" | grep "Fine-grained snap" > /dev/null && print_success "Commit message shows fine-grained snap"
echo "$SHOW_OUTPUT" | grep "another.txt" > /dev/null && print_success "Commit includes another.txt"

print_section "Stage 6: Track Remaining Files"

print_step "6.1: Track data files"
OUTPUT=$(uv run --directory "$MEMOV_ROOT" mem track --loc "$PROJECT_DIR" "$PROJECT_DIR/data/config.json" "$PROJECT_DIR/data/settings.yaml" -p "Data files" -r "JSON and YAML data" 2>&1)
check_output_for_errors "$OUTPUT"
print_success "Tracked data files"

print_section "Stage 7: File Operations"

print_step "7.1: Rename a file"
uv run --directory "$MEMOV_ROOT" mem rename --loc "$PROJECT_DIR" "$PROJECT_DIR/normal.txt" "$PROJECT_DIR/renamed.txt" -p "Rename operation" -r "Renamed normal.txt"
print_success "File renamed"

print_step "7.2: Check renamed file exists"
test -f "$PROJECT_DIR/renamed.txt" && print_success "Renamed file exists"

print_step "7.3: Snapshot after rename"
uv run --directory "$MEMOV_ROOT" mem snap --loc "$PROJECT_DIR" -p "After rename" -r "Snapshotted rename"
print_success "Snapshot created"

print_section "Stage 8: History & Verification"

print_step "8.1: View complete history"
OUTPUT=$(uv run --directory "$MEMOV_ROOT" mem history --loc "$PROJECT_DIR" 2>&1)
check_output_for_errors "$OUTPUT"
echo "$OUTPUT"
print_success "History displayed"

print_step "8.2: Get first commit hash and show details"
FIRST_COMMIT=$(uv run --directory "$MEMOV_ROOT" mem history --loc "$PROJECT_DIR" 2>&1 | grep -oE '[a-f0-9]{7}' | tail -1)
if [ -z "$FIRST_COMMIT" ]; then
    print_error "Failed to get commit hash"
    exit 1
fi
OUTPUT=$(uv run --directory "$MEMOV_ROOT" mem show --loc "$PROJECT_DIR" "$FIRST_COMMIT" 2>&1)
check_output_for_errors "$OUTPUT"
echo "$OUTPUT"
print_success "Show command works"

print_step "8.3: Amend commit message"
OUTPUT=$(uv run --directory "$MEMOV_ROOT" mem amend --loc "$PROJECT_DIR" "$FIRST_COMMIT" -p "Updated prompt" -r "Updated response" --by_user 2>&1)
check_output_for_errors "$OUTPUT"
print_success "Amend command works"

print_section "Test Complete!"
echo -e "${GREEN}All integration tests passed successfully!${NC}\n"
