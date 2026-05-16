<h1 align="center">pitlane-codex-plugin</h1>

<p align="center">
  <strong>Keep Codex code navigation compact by routing safe source reads through Pitlane.</strong>
</p>

<p align="center">
  A small Codex-compatible <code>PreToolUse</code> plugin for token-efficient source browsing, symbol search, and repo outlines.
</p>

<p align="center">
  <a href="./docs/install.md">Install</a>
  ·
  <a href="./docs/compatibility.md">Compatibility</a>
  ·
  <a href="./docs/stack.md">Stack Fit</a>
</p>

`pitlane-codex-plugin` adds a code-navigation `PreToolUse` hook for
Codex-compatible runtimes. It rewrites only narrow, safe shell reads into
host-local `pitlane` CLI calls:

- source `cat`, `head`, and simple `sed -n A,Bp` reads become `pitlane lines`;
- simple symbol-looking `rg`, recursive `grep`, `ls -R`, and `tree` commands
  become Pitlane search or outline calls when the project has a Pitlane index,
  with a cheap auto-index attempt for safe local worktrees;
- missed source-navigation opportunities, including broad `find` and
  `git grep` shapes, can emit a small hint while leaving the original command
  unchanged; compact telemetry for these misses is opt-in;
- exact-output, regex-like search, machine-readable, build, test, Docker, SSH,
  data, and shell-control commands pass through unchanged.

There is no sidecar, container, SSH, wrapper, or gateway fallback path. If a
host-local `pitlane` executable is not available, the hook silently leaves the
original shell command alone.

## Part of the Codez stack

The Codez stack is modular. Each layer can be used on its own unless a higher
layer explicitly opts into it.

| Layer | Public surface | Responsibility | Dependency |
| --- | --- | --- | --- |
| [Codez](https://github.com/Krablante/codez) | Codex-compatible runtime | App Server v2, goal RPC, long-session hardening, prompt pruning, and plugin hooks | Does not require Teledex |
| [RTK Codex Plugin](https://github.com/Krablante/rtk-codex-plugin) | Optional Codex plugin | Shell/token safety through `rtk rewrite` and bounded output guarding | Requires a Codex-compatible plugin-hook runtime; does not require Teledex |
| [Pitlane Codex Plugin](https://github.com/Krablante/pitlane-codex-plugin) | Optional Codex plugin | Code-navigation/token-saving rewrites through a host-local `pitlane` CLI | Requires a Codex-compatible plugin-hook runtime and local `pitlane`; does not require Teledex |
| Teledex (planned public repo: `Krablante/teledex`) | Telegram gateway/session layer | Topics, queues, live steer, `/goal` UX, and multi-host delivery/recovery | Basic mode can drive upstream Codex; full mode requires a Codez-compatible runtime with App Server v2 and plugin-hook support |

When RTK and Pitlane are both enabled, load RTK before Pitlane. RTK handles
general shell-output safety; Pitlane then wins only for the narrow
code-navigation commands it accepts.

## Why People Use It

- avoid dumping large source files into the model context for routine browsing
- replace broad source reads with bounded `pitlane lines`
- turn simple symbol and listing exploration into indexed Pitlane navigation
- keep exact output intact for tests, builds, JSON, Docker, SSH, and automation
- install as a small plugin instead of changing shell habits by hand

## Quick Start

Clone the plugin into the plugin cache used by your Codex-compatible runtime.
One common GitHub cache layout looks like this:

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
git clone https://github.com/Krablante/pitlane-codex-plugin \
  "$codex_home/plugins/cache/github/pitlane-codex-plugin/local"
```

Enable plugin hooks and the plugin key that matches your install location:

```toml
[features]
plugins = true
plugin_hooks = true

[plugins."pitlane-codex-plugin@github"]
enabled = true
```

Put `pitlane` in `PATH`, index a project, and run the focused test suite:

```bash
pitlane --version
pitlane index /path/to/project
make test
```

Read next:

- [Install](./docs/install.md)
- [Compatibility](./docs/compatibility.md)
- [Stack Fit](./docs/stack.md)

## Notes

- `pitlane` is required for rewrites; without it, the hook passes through.
- symbol and outline rewrites require a ready Pitlane index; safe local
  worktrees can be auto-indexed with a short timeout.
- the plugin is intentionally shell-hook-only; gateway/session behavior belongs
  in higher-level tools.
