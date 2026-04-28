# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Detected stack
- Languages: Python 3.11+.
- Frameworks: prompt_toolkit (TUI), Rich (rendering), pytest (testing).
- Architecture: Local-first AI terminal (Python port of claw-code).

## Verification
- Run Python tests: `python3 -m pytest tests/ -q`
- Syntax check: `python3 -m py_compile src/*.py`
- `src/` and `tests/` are both present; update both surfaces together when behavior changes.

## Repository shape
- `src/` contains the Python source files for the Scream Code runtime, REPL, TUI, LLM client, and tool registry.
- `tests/` contains validation surfaces that should be reviewed alongside code changes.
- `rust/` contains an archived Rust workspace (not actively maintained).
- `scripts/` contains shell helpers.
- `skills/` contains REPL slash skill implementations.

## Working agreement
- Prefer small, reviewable changes and keep generated bootstrap files aligned with actual repo workflows.
- Keep shared defaults in `.claude.json`; reserve `.claude/settings.local.json` for machine-local overrides.
- Do not overwrite existing `CLAUDE.md` content automatically; update it intentionally when repo workflows change.
