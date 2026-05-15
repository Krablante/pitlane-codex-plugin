# Stack Fit

`pitlane-codex-plugin` is useful as a standalone Codex-compatible plugin, but it
is also designed to sit in a larger local-agent stack.

## Layers

| Layer | Responsibility |
| --- | --- |
| [Codez](https://github.com/Krablante/codez) or another compatible runtime | runs the model loop, shell tool, config, and plugin hooks |
| [RTK Codex Plugin](https://github.com/Krablante/rtk-codex-plugin) | keeps shell exploration compact and guards risky long-line output |
| Pitlane Codex Plugin | routes safe code-navigation commands to host-local Pitlane CLI |
| Telegram gateway / Teledex | coming next; may install or sync plugins on worker machines |

The plugin does not own sessions, chat delivery, host registries, or project
metadata. It only handles source-navigation command rewrite at the hook layer.

## Recommended Order

When RTK and Pitlane are both enabled, load RTK before Pitlane. RTK handles
general shell-output safety; Pitlane then wins only for the narrow
code-navigation commands it accepts.

```toml
[features]
plugins = true
plugin_hooks = true

[plugins."rtk-codex-plugin@github"]
enabled = true

[plugins."pitlane-codex-plugin@github"]
enabled = true
```

## Public Stack

The current public stack shape is:

- [Codez](https://github.com/Krablante/codez): core Codex-compatible runtime
  with token-aware context behavior, App Server v2, and plugin hook
  compatibility
- [RTK Codex Plugin](https://github.com/Krablante/rtk-codex-plugin): optional
  shell token-safety and bounded output
- Pitlane Codex Plugin: optional indexed code-navigation rewrite
- Teledex: Telegram-facing gateway, coming later

Pitlane does not require Codez, RTK, or Teledex. Codez and RTK are linked now
because they have clean public releases; Teledex is intentionally not linked
until its public repo is ready.
