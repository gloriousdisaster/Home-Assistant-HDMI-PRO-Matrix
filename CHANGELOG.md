# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] — 2026-04-24

A ground-up rewrite of the 1.0 integration, covering a full async client,
coordinator-driven state, preset scenes, a per-output `media_player`
platform, automation blueprints, dashboard recipes, and a large round
of typing + CI polish.

### Added
- **`media_player` platform** — one entity per HDMI output with a native
  source picker, power control, and volume-mute (routes the output to input 0).
  Renders as a stock HA Tile or Mushroom card per output without extra config.
- **Preset scenes** — 8 device-native preset slots exposed:
  - `select.hdmi_matrix_recall_preset` — recall slots 1–8.
  - `text.hdmi_matrix_preset_N_name` × 8 — rename slots; writes persist to
    the device.
  - Service `gofanco_prophecy.save_preset(index)` — save current routing.
- **Four automation blueprints** under `blueprints/automation/gofanco_prophecy/`:
  recall preset, auto-route on media-player state change, save preset on
  event, mute-all on event. Each has a one-click "Open in HA" import badge
  in the README.
- **Three dashboard recipes** under `dashboards/`:
  - `stock.yaml` — no HACS frontend dependencies.
  - `mushroom.yaml` — requires Mushroom cards.
  - `matrix_grid.yaml` — AV-switcher-style grid (rows = outputs, columns =
    inputs, currently-routed cell highlighted), requires `button-card`.
- **Text platform** for input / output / preset labels; writes persist to
  the device (≤7 characters).
- **Reconfigure flow** — change the matrix's host from the UI without
  deleting and re-adding the integration.
- **`diagnostics.py`**, `icons.json`, exception translations in `strings.json`,
  `services.yaml` with selectors for `save_preset`.
- **Config-flow validation** — distinguishes `cannot_connect` vs.
  `invalid_response`; port range 1–65535 enforced; factory-default host
  `192.168.1.92` pre-filled.

### Changed
- **Async client** via raw `asyncio.open_connection` — the device speaks a
  non-standard HTTP/0.9-adjacent dialect that `aiohttp` can't parse, so the
  client uses a typed `ProphecyState` dataclass and hand-rolls request /
  response framing that tolerates a status-lineless body.
- **Wire format aligned with the device's own web UI** — commands go in
  both the querystring (`/inform.cgi?<cmd>`) and POST body, matching the
  firmware-tested path exactly.
- **`DataUpdateCoordinator`** with `ConfigEntry.runtime_data` replaces the
  legacy `hass.data[DOMAIN]` dict pattern. 15-second polling with a 0.5-second
  debouncer on mutations so rapid UI flips collapse to a single refresh.
- **Clean entity IDs** — `DeviceInfo.name` is a plain "HDMI Matrix", so
  entity IDs are `switch.hdmi_matrix_power`, `select.hdmi_matrix_output_1`,
  `text.hdmi_matrix_input_1_label`, etc. — no IP octet noise.
- **State response validation** — replies missing known keys (`out1`,
  `powstatus`) raise `ProphecyResponseError` instead of silently treating
  the state as all-mute.
- **All entities** extend a shared `ProphecyEntity(CoordinatorEntity)` base
  with `has_entity_name=True` and per-entity `translation_key`.
- **Dashboard top bar** (matrix_grid recipe) — Power / Mute all / Preset
  render as three matching vertical Mushroom cards so they share the same
  shape. The preset dropdown lives under its label, no truncation.

### Removed
- **Component-local `requirements.txt`** (was incorrectly pinning HA).
- **Original empty `services.yaml`** (replaced with the real one).
- **`run_callback_threadsafe`-based sync wrappers** that pre-dated async HA.

### Deferred (not implemented)
- **Standby / lock binary sensors** — the device's state JSON never exposes
  a `standby` or `locked` key over the HTTP endpoint, so a read-only sensor
  would always be stale.
- **EDID selects** — the device offers write commands (`ediddefault`,
  `ediddisplay`) but no read-back, so a write-only select is worse UX than
  no entity.

### Developer / quality
- **mypy strict** enabled across the integration; CI has a `lint.yml`
  workflow running ruff + mypy + pre-commit.
- **Tests grew from 23 → 47+**, covering the new platforms, preset flow,
  and edge cases (name truncation at 7 chars, unmute-with-no-inputs,
  multi-matrix service targeting, concurrent-command serialization,
  HTTP/1.0 status-line handling).
- **CI workflows** — `hacs/action@22.5.0` pinned, `hassfest@master` (the
  only stable pointer maintained by the HA team), `codecov-action@v5`.
- **Pre-commit** — ruff, ruff-format, codespell, check-json, check-yaml
  with `--unsafe` for HA's `!input` tags, end-of-file-fixer, trailing
  whitespace.
- **Devcontainer** — Mushroom + button-card auto-installed via
  `post-create.sh`, blueprints copied into the HA config so they appear
  in the Blueprint picker without a manual import step.

---

## [1.0.0] — 2025

Initial release. Reverse-engineered HTTP control of the Gofanco Prophecy
PRO-Matrix44-SC from the device's embedded web UI. Per-output select entities
for routing, a switch for power, and a button for mute-all.

---

[2.0.0]: https://github.com/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix/releases/tag/v2.0.0
[1.0.0]: https://github.com/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix/releases/tag/v1.0.0
