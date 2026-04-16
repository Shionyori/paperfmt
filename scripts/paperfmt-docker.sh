#!/usr/bin/env sh
set -eu

IMAGE_NAME="paperfmt:local"

# Build image if missing.
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  docker build -t "$IMAGE_NAME" .
fi

# Pass all CLI args to paperfmt inside the container.
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  "$IMAGE_NAME" "$@"
