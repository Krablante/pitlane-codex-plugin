---
name: pitlane-codex-hook
description: "Use when inspecting Pitlane Codex hook behavior: source-read rewrites, symbol-search/listing rewrites, bypass modes, and coexistence with the RTK hook."
---

# Pitlane Codex Hook

This plugin adds a Codex `PreToolUse` Bash hook that keeps common code
navigation reads token-efficient by rewriting safe cases to Pitlane CLI calls.

## Behavior

- Source `cat`, `head`, and simple `sed -n A,Bp` reads become
  `pitlane lines`.
- Simple symbol-looking `rg`, recursive `grep`, and recursive listings become
  Pitlane search/outline only when the project already has a Pitlane index.
- Exact-output, machine-readable, build, test, data, Docker, SSH, and shell
  control commands pass through.
- The hook is intentionally separate from the RTK hook. When both are enabled,
  configure RTK first and Pitlane after it, so Pitlane rewrites win only for
  the narrow code-navigation cases it accepts.

## Bypass

Set one of these env vars to disable the hook for a command/session:

- `PITLANE_CODEX_HOOK_DISABLE=1`
- `PITLANE_CODEX_BYPASS=1`
- `PITLANE_DISABLE=1`
- `PITLANE_DISABLED=1`

Pitlane bypass only disables this hook. When exact raw shell output matters with
both hooks enabled, also use the relevant RTK bypass such as
`RTK_CODEX_BYPASS=1`.
