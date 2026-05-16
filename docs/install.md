# Install

This plugin expects a Codex-compatible runtime that supports plugin manifests
and `PreToolUse` hooks.

Clone the plugin into the plugin cache used by your runtime. One common cache
layout is:

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
git clone https://github.com/Krablante/pitlane-codex-plugin \
  "$codex_home/plugins/cache/github/pitlane-codex-plugin/local"
```

Enable plugin support in your Codex config:

```toml
[features]
plugins = true
plugin_hooks = true

[plugins."pitlane-codex-plugin@github"]
enabled = true
```

If your runtime assigns a different marketplace or local plugin key, enable the
key that matches its cache layout.

The hook only rewrites when a host-local `pitlane` executable is available:

```bash
pitlane --version
```

For symbol search and repo outline rewrites, index the target project first:

```bash
pitlane index /path/to/project
```

The hook does not start, contact, or fall back to any gateway, container,
remote host, or sidecar process. No Teledex install is required for local
plugin usage.
