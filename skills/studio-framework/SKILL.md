---
name: studio-framework
description: Local multi-expert studio framework - Feature Pod pipeline + Review Board gates + Orchestrator-Only lead, with verify-never-trust checks, gate-driven rework, receipts and resumable state. Use when running a role-based studio locally (writing / review / ops pipelines) without a platform runtime.
metadata:
  version: "0.1.0"
---

# Studio Framework

## When to use
Role-based pipelines that need ordered stages, quantified gates, and audit trails - running entirely locally.

## Topology (from agent-team-topologies)
- Feature Pod: multi-stage delivery pipeline (topic -> draft -> gate -> ...)
- Review Board: several gates / lenses, each with its own checklist file
- Orchestrator-Only: the lead coordinates and never writes the deliverable

## Discipline (from orchestration practice)
1. Plan: write PLAN.md with per-stage gates before dispatching.
2. Dispatch one leaf: one stage at a time, fresh context each dispatch.
3. Verify, never trust: the runner re-runs deterministic checks (length, CJK range, refusal/meta patterns, verdict presence) instead of trusting self-reports.
4. Integrate or ABANDON: unmet gates send the stage back with the exact unmet items; if unreachable, mark ABANDONED with a reason (never silently pass).
5. Release gate: publishing / outbound / payment actions always require explicit user approval.

## Layout

~~~
<root>/
  teams/<team>/runtime.json   seat registry (name + agentType + status)
  docs/<agentType>.md         one prompt per seat
  runner/studio-run.py        new-task | run | dry-run
  runtime/{tasks,receipts}/   state, receipts
  gates/                      final verdict JSON
  work/                       stage outputs
~~~

## Commands

~~~bash
STUDIO_ROOT=$PWD python3 runner/studio-run.py new-task --task "...anything..."
STUDIO_ROOT=$PWD python3 runner/studio-run.py run --task-id <id> --channel claude --max-gate-rounds 2
STUDIO_ROOT=$PWD python3 runner/studio-run.py dry-run     # registry + seat-gate check, no model calls
~~~
