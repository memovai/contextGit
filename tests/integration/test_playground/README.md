# Mem Integration Test Playground

Comprehensive integration test suite for the `mem` command-line tool.

## Overview

This test suite validates core functionality of the mem tool, with special focus on `.memignore` behavior.

## Directory Structure

```
test_playground/
├── README.md           # This file
├── setup.sh            # Create test environment
├── cleanup.sh          # Clean up test artifacts
├── run_tests.sh        # Main integration test script
└── sample_project/     # Test project (created by setup.sh)
```

## Quick Start

### 1. Setup Test Environment

```bash
./setup.sh
```

This creates a sample project with various file types:
- Normal text files
- Source code files (Python)
- Documentation files (Markdown)
- Data files (JSON, YAML)
- Hidden files (should be ignored)

### 2. Run Tests

**Option A: Automated tests**
```bash
./run_tests.sh
```

**Option B: Manual testing**
```bash
cd sample_project
# Then follow manual testing steps below
```

### 3. Cleanup

```bash
./cleanup.sh
```

## Test Coverage

### Stage 1: Initialize & Verify .memignore
- Initialize mem repository
- Verify .memignore is created with default rules
- Verify hidden files (.*) are ignored from status

### Stage 2: Track Normal Files
- Track multiple files at once
- Verify tracked files appear as "Clean" in status

### Stage 3: Modify & Snapshot
- Modify tracked files
- Verify modifications are detected
- Create snapshot to save changes
- Verify files return to "Clean" state

### Stage 4: Dynamic .memignore Rules
- Create files that will be ignored
- Verify they appear in status initially
- Add new ignore rules to .memignore
- Verify ignored files disappear from status
- Snapshot .memignore changes

### Stage 5: File State Transitions (Clean/Modified/Untracked)
- **Test 5.1**: Verify Clean state - tracked files with no changes
- **Test 5.2**: Verify Untracked state - files not yet tracked
- **Test 5.3**: Verify Modified state - tracked files with changes
- **Test 5.4**: State transition: Untracked → Clean (via track)
- **Test 5.5**: State transition: Clean → Modified (via file edit)
- **Test 5.6**: State transition: Modified → Clean (via snapshot)
- **Test 5.7**: Verify all three states coexist correctly

### Stage 6: Track Remaining Files
- Track files in subdirectories (data/, docs/, src/)
- Verify nested directory support

### Stage 7: File Operations
- Rename tracked files
- Verify renamed files are tracked correctly
- Snapshot after rename

### Stage 8: History & Verification
- View complete history
- Show specific commit details
- Amend commit messages

## Manual Testing Steps

For better understanding of each command's behavior:

```bash
# Navigate to test project
cd sample_project

# 1. Initialize
mem init --loc .

# 2. View .memignore
cat .memignore

# 3. Check status (note: hidden files should NOT appear)
mem status --loc .

# 4. Track files
mem track --loc . README.md -p "test" -r "test"

# 5. Modify a file
echo "new content" >> README.md

# 6. Check modification status
mem status --loc .

# 7. Create snapshot
mem snap --loc . -p "snapshot" -r "test"

# 8. Add new ignore rule
echo "*.log" >> .memignore

# 9. Create file that should be ignored
echo "log" > app.log

# 10. Verify app.log does NOT appear in status
mem status --loc .

# 11. View history
mem history --loc .
```

## Validation Checklist

### .memignore Functionality
- [ ] `.memignore` is auto-created during `mem init`
- [ ] `.memignore` contains default rule `.*`
- [ ] `.memignore` itself is tracked (visible in history)
- [ ] Hidden files (`.hidden_file`, `.env`) do NOT appear in `mem status`
- [ ] Attempting to `mem track .hidden_file` is rejected or ignored
- [ ] After adding new rules (e.g., `*.log`), matching files disappear from status
- [ ] Already-tracked files continue to show status even if they match new rules

### File Operations
- [ ] Can track files with special characters
- [ ] Can track directories
- [ ] Modified files show as "Modified" in status
- [ ] Snapshot returns files to "Clean" state
- [ ] Rename operation works correctly
- [ ] History records all operations

### File States (Stage 5)
- [ ] **Clean state**: Tracked files with no changes display correctly
- [ ] **Untracked state**: Files not yet tracked display correctly
- [ ] **Modified state**: Tracked files with changes display correctly
- [ ] **State transition Untracked → Clean**: Track command works
- [ ] **State transition Clean → Modified**: File edits are detected
- [ ] **State transition Modified → Clean**: Snapshot restores clean state
- [ ] **Multiple states coexist**: Can have Clean/Modified/Untracked files simultaneously

## Test Results

**Date**: 2025-10-21

**Status**: All core functionality tests pass

**Key Findings**:
1. `.memignore` default rule (`.*`) works correctly
2. Hidden files completely absent from status (as expected)
3. Dynamic rule changes take effect immediately
4. All file operations work correctly
5. Nested directory support works (data/, src/, docs/)
6. File state transitions work correctly (Clean/Modified/Untracked)
7. File state reporting is consistent across operations

## Known Issues

None - all tests passing.

## Future Improvements

1. Add automated assertions to verify output content
2. Test more edge cases (symlinks, read-only files, etc.)
3. Performance testing (large files, many files)
4. Consider adding `jump` command tests
