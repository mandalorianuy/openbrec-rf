#!/usr/bin/env bash
set -euo pipefail
repo_name="${1:-openbrec-rf}"
command -v gh >/dev/null || { echo "gh no está instalado" >&2; exit 1; }
gh auth status
gh repo create "$repo_name" --public --source=. --remote=origin --push
