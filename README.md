# studio-framework

Local multi-expert studio framework: **Feature Pod** pipeline + **Review Board** gates + **Orchestrator-Only** lead, with verify-never-trust checks, gate-driven rework, receipts and resumable state.

[![conformance](https://img.shields.io/badge/Agent%20Plugins-1.1.0%20conformant-success)](https://agent-plugins.org) [![license](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

## Why
The valuable part of a multi-agent studio is not the chat UI - it is the *discipline*:
ordered stages, quantified gates, evidence over self-report, and an audit trail. This repo packages that discipline as ~300 lines of Python you can run locally.

## Mechanisms

- **Weighted gates**: dimension weights + veto line live in ONE source JSON; `runner/score.py` scores and can sweep variants. Proven property: changing weights can flip a verdict, so weights are a governance act (change via documented consensus + version lock).
- **Dispatch spec guard**: `runner/dispatch_guard.py` enforces seven evidence checks on every work order (identity/registration/deliverable, read-only claim, command trail, run evidence, seat independence, read-back), fail-closed.
- **Token ledger**: every dispatch should be recorded (G12 gate -> ledger -> token -> dispatch -> read-back); the runner appends ledger entries for each stage.

## Design
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Highlights:
- one seat registry (JSON) + one prompt file per seat (Markdown)
- deterministic post-checks per stage (the runner never trusts a self-report)
- unmet gate -> rework with the exact unmet items; unreachable -> ABANDONED with a reason
- receipts + lead log + resumable task state
- optional seat guard hook (any script that supports --validate-seat <name>)

## Quick start

~~~bash
STUDIO_ROOT=$PWD python3 runner/studio-run.py new-task --task "your topic"
STUDIO_ROOT=$PWD python3 runner/studio-run.py run --task-id <id> --channel openai --max-gate-rounds 2
python3 runner/studio-run.py dry-run   # no model calls: validates registry + seat guard
python3 tests/test_framework.py        # self-test
~~~

For the openai channel set:

~~~bash
STUDIO_API_BASE=https://api.example.com/v1
STUDIO_API_KEY=...
STUDIO_MODEL=your-model
~~~

## Compliance
The package follows the **Agent Plugins 1.1.0** layout (manifest + skills/<name>/SKILL.md) and ships a validator: scripts/validate-plugin.py.

## Scope / privacy
This repository contains **framework code only**: no seat prompts from any real studio, no platform internals, no credentials.

## License
MIT.
