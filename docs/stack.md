# Stack Fit

`pitlane-codex-plugin` is useful as a standalone Codex-compatible plugin, but it
is also designed to sit in a larger local-agent stack.

## Part of the Codez stack

The Codez stack is modular. Each layer can be used on its own unless a higher
layer explicitly opts into it.

| Layer | Public surface | Responsibility | Dependency |
| --- | --- | --- | --- |
| [Codez](https://github.com/Krablante/codez) | Codex-compatible runtime | App Server v2, goal RPC, long-session hardening, prompt pruning, and plugin hooks | Does not require Teledex |
| [RTK Codex Plugin](https://github.com/Krablante/rtk-codex-plugin) | Optional Codex plugin | Shell/token safety through `rtk rewrite` and bounded output guarding | Requires a Codex-compatible plugin-hook runtime; does not require Teledex |
| [Pitlane Codex Plugin](https://github.com/Krablante/pitlane-codex-plugin) | Optional Codex plugin | Code-navigation/token-saving rewrites through a host-local `pitlane` CLI | Requires a Codex-compatible plugin-hook runtime and local `pitlane`; does not require Teledex |
| [Teledex](https://github.com/Krablante/teledex) | Telegram gateway/session layer | Topics, queues, live steer, `/goal` UX, and delivery/recovery around durable agent sessions | Requires Codez App Server v2 for normal public use; upstream `codex exec --json` is legacy compatibility only |

The plugin does not own sessions, chat delivery, host registries, or project
metadata. It only handles source-navigation command rewrite at the hook layer.

## Plain Version

Codez runs the agent. RTK makes risky shell output safer and smaller. Pitlane
makes routine code browsing smaller by replacing safe source reads with indexed
CLI calls. Teledex is the Telegram/session gateway that can drive a runtime,
but it is not part of the Codez runtime itself.

Pitlane does not require Codez, RTK, or Teledex. Codez and RTK are linked
because they have clean public repositories. Teledex is linked as the Codez-first
Telegram gateway layer; it can install or sync Pitlane for workers, but Pitlane
remains usable without any gateway.

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
