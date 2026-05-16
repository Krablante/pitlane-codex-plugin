# Compatibility

The plugin is intended for Codex-compatible runtimes that support:

- plugin manifests via `.codex-plugin/plugin.json`;
- hook declarations via `hooks/hooks.json`;
- `PreToolUse` hooks for shell/Bash tool calls;
- `${PLUGIN_ROOT}` expansion in hook commands.

Known integration layers:

- [Codez](https://github.com/Krablante/codez) is the recommended public runtime
  layer when you want plugin hooks plus token-aware context behavior.
- [RTK Codex Plugin](https://github.com/Krablante/rtk-codex-plugin) can run
  earlier in the plugin order to guard risky shell output before Pitlane handles
  narrow code-navigation rewrites.
- Other Codez/Codex-compatible runtimes can execute the hook directly if they
  support plugin-loaded `PreToolUse` shell hooks.
- Telegram or remote-worker gateways can install or sync the plugin for worker
  machines, but no gateway is required for local usage. Teledex is the planned
  Telegram gateway layer; its planned public repo name is `Krablante/teledex`,
  and it is intentionally not linked until that repo exists.

Pitlane rewrites require a host-local `pitlane` binary in `PATH`. Symbol search
and recursive listing rewrites also require a ready Pitlane project index. The
hook can make a short auto-index attempt for safe local worktrees. Missed
source-navigation telemetry is compact and opt-in.

## Pass-Through Policy

The hook avoids rewriting commands where exact output is expected:

- tests and package-manager check commands
- build commands
- direct regex-like `rg`/`grep` searches
- Docker commands
- SSH and remote-control commands
- machine-readable modes such as JSON, porcelain, counts, and file lists
- data files and non-source reads
- interactive commands
- shell-control forms such as pipes, redirects, substitutions, and separators

When the hook cannot prove a command is safe to rewrite, it emits no hook output
and the runtime executes the original shell command unchanged. For actionable
source-navigation misses, including broad `find` and `git grep` shapes, it may
emit a small `additionalContext` hint with the same original command.

## Dependency Boundary

Pitlane Codex Plugin does not require Teledex. It only requires a
Codex-compatible runtime that supports plugin-loaded `PreToolUse` shell hooks
and a host-local `pitlane` CLI for rewrites.
