<h1 align="center">pitlane-codex-plugin</h1>

<p align="center">
  <strong>Keep Codex code navigation compact by routing safe source reads through Pitlane.</strong>
</p>

<p align="center">
  A small Codex-compatible <code>PreToolUse</code> plugin for token-efficient source browsing, symbol search, and repo outlines.
</p>

<p align="center">
  <a href="https://github.com/Krablante/pitlane-codex-plugin/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/Krablante/pitlane-codex-plugin/ci.yml?branch=main&style=for-the-badge" alt="CI status">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License">
  </a>
  <img src="https://img.shields.io/badge/Python-3-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/Codex-Plugin%20Hooks-111111?style=for-the-badge" alt="Codex plugin hooks">
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
  become Pitlane search or outline calls when the project already has a Pitlane
  index;
- exact-output, regex-like search, machine-readable, build, test, Docker, SSH,
  data, and shell-control commands pass through unchanged.

There is no sidecar, container, SSH, wrapper, or gateway fallback path. If a
host-local `pitlane` executable is not available, the hook silently leaves the
original shell command alone.

Stack note: [Codez](https://github.com/Krablante/codez) is the recommended
public runtime layer for working plugin-hook compatibility and token-aware
context behavior. [RTK Codex Plugin](https://github.com/Krablante/rtk-codex-plugin)
can run before Pitlane to guard risky shell output. A Telegram gateway layer,
Teledex, is planned later and is not linked until it has a clean public release.

## Why People Use It

- avoid dumping large source files into the model context for routine browsing
- replace broad source reads with bounded `pitlane lines`
- turn simple symbol and listing exploration into indexed Pitlane navigation
- keep exact output intact for tests, builds, JSON, Docker, SSH, and automation
- install as a small plugin instead of changing shell habits by hand

## Mental Model

| Piece | Role |
| --- | --- |
| Codex-compatible runtime | executes `PreToolUse` hooks before shell calls |
| `pitlane-codex-hook` | decides whether a source-navigation command can be rewritten |
| host-local `pitlane` CLI | serves lines, search results, and outlines from a local project index |
| optional RTK plugin | runs earlier in the stack for shell token-safety and output guarding |

Architecture at a glance:

```text
Codex shell tool call
  -> PreToolUse hooks
     -> RTK can guard risky shell output
     -> Pitlane can rewrite narrow code-navigation commands
     -> exact-output/build/test/Docker/SSH/control command? pass through unchanged
```

## Highlights

- standalone hook: only depends on a host-local `pitlane` CLI
- index-aware symbol/listing rewrites
- bounded source-line reads for common code browsing commands
- conservative pass-through policy for commands where stdout semantics matter
- designed to fit the Codez + RTK + Pitlane + future Teledex stack

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
- symbol and outline rewrites require an existing Pitlane index.
- the plugin is intentionally shell-hook-only; gateway/session behavior belongs
  in higher-level tools.
