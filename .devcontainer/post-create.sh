#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${PWD}"
VENV="${WORKSPACE}/.venv"
HA_CONFIG="${WORKSPACE}/.devcontainer/ha_config"

echo "==> Creating Python virtualenv"
python -m venv "${VENV}"
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo "==> Installing Python dependencies"
pip install --upgrade pip wheel
pip install -r requirements_test.txt
# aiodns 3.2 is incompatible with pycares 5.x (Channel.getaddrinfo signature
# change). Pin pycares until aiodns publishes a matching release.
pip install 'pycares<5'

echo "==> Installing Claude Code (native installer)"
if ! command -v claude >/dev/null 2>&1; then
  curl -fsSL https://claude.ai/install.sh | bash
fi
# Ensure ~/.local/bin is on PATH for future shells
if ! grep -q 'HOME/.local/bin' "${HOME}/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${HOME}/.bashrc"
fi
export PATH="${HOME}/.local/bin:${PATH}"

echo "==> Preparing Home Assistant config directory"
mkdir -p "${HA_CONFIG}"
if [ ! -f "${HA_CONFIG}/configuration.yaml" ]; then
  cat > "${HA_CONFIG}/configuration.yaml" <<'YAML'
default_config:

logger:
  default: info
  logs:
    custom_components.gofanco_prophecy: debug
YAML
fi

# Symlink the custom component into the HA config so edits are picked up live
mkdir -p "${HA_CONFIG}/custom_components"
ln -sfn "${WORKSPACE}/custom_components/gofanco_prophecy" \
  "${HA_CONFIG}/custom_components/gofanco_prophecy"

# Blueprints are copied rather than symlinked — HA's blueprint loader
# sometimes misses symlinked author directories on container overlay fs.
mkdir -p "${HA_CONFIG}/blueprints/automation"
rm -rf "${HA_CONFIG}/blueprints/automation/gofanco_prophecy"
cp -r "${WORKSPACE}/blueprints/automation/gofanco_prophecy" \
  "${HA_CONFIG}/blueprints/automation/gofanco_prophecy"

# Install Lovelace custom cards directly (no HACS available in the
# devcontainer). Pinned versions keep the dashboard YAMLs in dashboards/
# compatible with what the user sees in HA.
MUSHROOM_VERSION="5.1.1"
BUTTON_CARD_VERSION="7.0.1"
mkdir -p "${HA_CONFIG}/www" "${HA_CONFIG}/.storage"

download_card() {
  local name="$1" url="$2" dest="${HA_CONFIG}/www/$1"
  if [ ! -f "${dest}" ]; then
    echo "==> Downloading ${name}"
    curl -fsSL "${url}" -o "${dest}"
  fi
}
download_card "mushroom.js" \
  "https://github.com/piitaya/lovelace-mushroom/releases/download/v${MUSHROOM_VERSION}/mushroom.js"
download_card "button-card.js" \
  "https://github.com/custom-cards/button-card/releases/download/v${BUTTON_CARD_VERSION}/button-card.js"

# Write (or rewrite) the Lovelace resources storage file to register both cards.
python - <<PYEOF
import json, uuid
from pathlib import Path
path = Path("${HA_CONFIG}/.storage/lovelace_resources")
resources = [
    ("/local/mushroom.js?v=${MUSHROOM_VERSION}",),
    ("/local/button-card.js?v=${BUTTON_CARD_VERSION}",),
]
path.write_text(json.dumps({
    "version": 1,
    "minor_version": 1,
    "key": "lovelace_resources",
    "data": {"items": [
        {"id": uuid.uuid4().hex, "type": "module", "url": url}
        for (url,) in resources
    ]},
}, indent=2) + "\n")
PYEOF

echo "==> Done."
echo "Start Home Assistant with:  source .venv/bin/activate && hass -c .devcontainer/ha_config"
echo "Launch Claude Code with:    claude"
