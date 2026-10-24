---
name: catchme-light
description: >-
  Query the user's always-on screen recording via the catchme CLI.
  Use when the user mentions catchme, activity recording, screen capture,
  digital footprint, or asks about what they were doing/seeing earlier.
---

# CatchMe — Screen Memory CLI

Query the user's always-on screen recording via the `catchme` CLI.

> **Prerequisite**: `catchme awake` must already be running in the background.

## Find & Activate the Environment

The conda env name may not be `catchme`. Discover it first:

```bash
find "$(conda info --base)/envs" -path "*/bin/catchme" 2>/dev/null | head -1
```

This prints something like `/opt/miniconda3/envs/ENVNAME/bin/catchme`. Extract the env name from the path and activate it:

```bash
conda activate ENVNAME
```

**Verify awake is running:**

```bash
catchme ram
```

If no `awake` process appears, inform the user that `catchme awake` needs to be started first.

## Commands

### `catchme ask -- "<question>"`

Query activity history in natural language. The retrieval pipeline navigates the activity tree, inspects screenshots, and returns a natural language answer.

```bash
catchme ask -- "What was I working on this morning?"
catchme ask -- "When did I last open Figma?"
catchme ask -- "Summarize my afternoon session"
```

### `catchme cost`

Show LLM token usage (last 10 min / today / all time).

### `catchme disk`

Show storage breakdown (database, screenshots, trees) and total event count.

### `catchme ram`

Show RAM usage of all running catchme processes.

### `catchme web [-p PORT]`

Launch web dashboard (default: `http://127.0.0.1:8765`).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `find` returns nothing | catchme is not installed in any conda env |
| `command not found: catchme` | Wrong env activated — re-run the `find` command above |
| `ask` returns no results | `catchme awake` not running — check `catchme ram` |
| LLM errors | Check the path printed by `catchme init` (by default `~/.catchme/config.json`, or `%USERPROFILE%\.catchme\config.json` on Windows) |

## Notes

- `catchme awake` must be running for `ask` to have recent data
- Data is stored locally by default; when a cloud LLM is configured, activity context and selected screenshots may be sent to that endpoint.
