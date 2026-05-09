#!/usr/bin/env python3
"""
Edit Watcher — Post-Tool-Use Hook for Edit/Write Visibility
============================================================
This hook intercepts every Edit and Write tool call, records the edited file path
and git diff to a session log, and prints to stdout so the user sees what was changed
in Claude Code's output panel.

Files touched are logged to: .claude/hooks/logs/edit-log.md
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def get_project_root():
    """Find the project root (.claude directory parent)."""
    script_dir = Path(__file__).parent.parent.parent  # .claude/hooks/scripts/ -> .claude/
    return script_dir.parent

def log_edit(file_path, tool_name, diff_output=None):
    """
    Write an edit record to the log file.

    Args:
        file_path: The file that was edited
        tool_name: "Edit" or "Write"
        diff_output: Optional git diff output
    """
    try:
        project_root = get_project_root()
        logs_dir = project_root / ".claude" / "hooks" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "edit-log.md"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Normalize file_path to be relative to project root
        try:
            rel_path = Path(file_path).relative_to(project_root)
        except ValueError:
            # If not under project root, just use as-is
            rel_path = Path(file_path)

        entry = f"\n[{timestamp}] **{tool_name}**: `{rel_path}`\n"

        if diff_output:
            entry += "```diff\n"
            # Truncate diff to 100 lines to keep log manageable
            diff_lines = diff_output.split('\n')[:100]
            entry += '\n'.join(diff_lines)
            if len(diff_output.split('\n')) > 100:
                entry += "\n... (truncated)\n"
            entry += "\n```\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)

    except Exception as e:
        print(f"Error logging edit: {e}", file=sys.stderr)

def get_git_diff(file_path, cwd=None):
    """
    Run git diff on a file and return the output.
    Falls back gracefully if git fails (e.g., file is untracked).
    """
    try:
        # Get relative path for git diff
        if cwd:
            abs_path = Path(cwd) / file_path
        else:
            abs_path = Path(file_path)

        result = subprocess.run(
            ["git", "diff", str(abs_path)],
            cwd=cwd or str(get_project_root()),
            capture_output=True,
            text=True,
            timeout=5
        )

        return result.stdout if result.returncode == 0 else None

    except Exception as e:
        return None

def main():
    """Main hook handler."""
    try:
        # Read hook data from stdin
        stdin_content = sys.stdin.read().strip()
        if not stdin_content:
            sys.exit(0)

        hook_data = json.loads(stdin_content)

        # Only process Edit and Write tools
        tool_name = hook_data.get("tool_name", "")
        if tool_name not in ("Edit", "Write"):
            sys.exit(0)

        # Extract file path
        tool_input = hook_data.get("tool_input", {})
        file_path = tool_input.get("file_path")

        if not file_path:
            sys.exit(0)

        # Get git diff
        cwd = hook_data.get("cwd") or str(get_project_root())
        diff_output = get_git_diff(file_path, cwd)

        # Log the edit
        log_edit(file_path, tool_name, diff_output)

        # Print to stdout (visible in Claude Code output panel)
        try:
            rel_path = Path(file_path).relative_to(get_project_root())
        except ValueError:
            rel_path = Path(file_path)

        print(f"[EDITED] {rel_path}")

        sys.exit(0)

    except json.JSONDecodeError:
        # Silently fail if JSON is malformed
        sys.exit(0)
    except Exception as e:
        # Fail gracefully without interrupting Claude's work
        print(f"Edit watcher error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
