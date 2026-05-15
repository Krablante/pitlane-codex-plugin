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
  Telegram gateway layer and is intentionally not linked until it has a public
  release.

Pitlane rewrites require a host-local `pitlane` binary in `PATH`. Symbol search
and recursive listing rewrites also require a ready Pitlane project index.

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
and the runtime executes the original shell command unchanged.
