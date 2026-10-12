# Architecture

~~~
task -> topic (scout) -> write (writer) -> gate (reviewer) -> [rework loop] -> PASS
            |                |                  |
       receipt+gates    receipt+gates      receipt+gates+verdict JSON
~~~

- State: runtime/tasks/<id>/state.json - resumable; COMPLETE stages are skipped unless --force.
- Receipts: runtime/receipts/<ts>-<id>-<stage>.json - who did what, which checks passed, how long.
- Lead log: runtime/lead-log.jsonl - orchestration actions only (the lead never writes content).
- Verdict parsing: runner/verdict.py handles both JSON and natural-language conclusions (EN/CN).
- Channels: claude (agent CLI) or openai (any OpenAI-compatible endpoint via STUDIO_API_BASE / STUDIO_API_KEY / STUDIO_MODEL).
- Seat guard: if scripts/process-guard.py exists, every dispatch is preceded by a --validate-seat call; otherwise the registry is the only check.

## Non-goals
No platform runtime, no UI, no credential storage. Bring your own models and your own prompts.
