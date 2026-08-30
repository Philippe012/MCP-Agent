TOOLS = [
    {
        "name": "list_files",
        "description": "List every file in the repository the agent is working in.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_file",
        "description": "Read the full text contents of one repository file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Repository-relative file path."}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_code",
        "description": "Case-sensitive search across all .py files in the repository; returns matching file paths.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite (or create) one repository text file with new content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repository-relative file path."},
                "content": {"type": "string", "description": "Full new file contents."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_tests",
        "description": "Run the repository's pytest suite and return returncode/stdout/stderr.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "git_diff",
        "description": "Return `git diff` for the repository (tracked-file changes only; new untracked files will not appear here).",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]
