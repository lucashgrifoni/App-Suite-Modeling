#!/usr/bin/env bash
set -euo pipefail

version=1.1309.0
sha256=4802579c2818938a2f4849d270df1139f310104286a8a5c6305328a3c2eb9e1c
directory="$(mktemp -d "${RUNNER_TEMP:?}/snyk-cli.XXXXXX")"
binary="$directory/snyk"

curl --fail --silent --show-error --location --proto '=https' --retry 3 \
  --output "$binary" "https://github.com/snyk/cli/releases/download/v${version}/snyk-linux"
printf '%s  %s\n' "$sha256" "$binary" | sha256sum --check --strict
chmod 0755 "$binary"
printf '%s\n' "$directory" >> "${GITHUB_PATH:?}"
