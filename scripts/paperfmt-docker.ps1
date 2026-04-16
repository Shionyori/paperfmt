$ErrorActionPreference = "Stop"

$imageName = "paperfmt:local"

# Build image if missing.
$exists = docker image inspect $imageName 2>$null
if (-not $exists) {
    docker build -t $imageName .
}

# Forward all arguments to paperfmt in the container.
docker run --rm `
  -v "${PWD}:/workspace" `
  -w /workspace `
  $imageName @args
