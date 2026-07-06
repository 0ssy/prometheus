# Plugin System

## Two separate extension points, not one

Prometheus has two distinct extension mechanisms that are easy to
conflate:

- **Plugins** (`plugins/`) — extend *capability*. A plugin is a unit
  of functionality the core doesn't have built in.
- **Agents** (`agents/`, `autonomous/`) — *perform tasks* using
  whatever capability is available, including what plugins provide.

`plugins/manager.py` and `agents/manager.py` are deliberately built
as the same shape (register/list/dispatch) — same pattern, different
concern. Don't merge them into one registry; the distinction between
"what can this system do" and "what is this system doing right now"
is worth keeping visible in the code, not just in prose.

## Contract

Every plugin implements `plugins/base.py`'s interface. Every agent
implements `agents/base.py`'s `PrometheusAgent.perform(task, context)`.
See `EchoPlugin` and `EchoAgent` as the reference implementations —
minimal on purpose, meant to be read as "this is the shape," not
copied as production logic.

## Why hardware isn't a plugin (yet)

The original doodle plan showed hardware platforms (Android, Linux,
ESP32, Vehicle, Drone) as plugins hanging off Prometheus Core. What
actually got built is different: hardware is `devices/`'s `Device`
contract (Phase Beta), a separate mechanism from the plugin system.

This wasn't an oversight — a `Device` needs a persistent connection,
lifecycle (connect/disconnect), and a registry with live state, which
doesn't fit the plugin system's simpler "register once, invoke by
name" shape. If a real need to expose device support *as* a plugin
shows up (e.g., a marketplace of third-party device drivers),
revisit this — don't force it into the plugin shape speculatively
now.

## Extending the whitelist pattern

Epsilon's `SUPPORTED_CHANGE_TYPES` (`autonomous/proposals.py`) is a
different kind of "plugin point" — not user-facing capability, but a
deliberately narrow, security-relevant whitelist. New change types
get added one at a time, each with its own simulator + tester pair.
Don't generalize this into "arbitrary code plugins" — the whitelist
*is* the safety property.
