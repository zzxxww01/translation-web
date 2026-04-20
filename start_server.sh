#!/bin/bash
# Translation Agent Server Startup Script

set -e

# Load environment variables
set -a
source .env
set +a

# Validate critical environment variables
REQUIRED_VARS=("VECTORENGINE_API_KEY" "VECTORENGINE_BASE_URL")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    MISSING_VARS+=("$var")
  fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
  echo "ERROR: Missing required environment variables:"
  printf '  - %s\n' "${MISSING_VARS[@]}"
  exit 1
fi

echo "Environment variables loaded successfully"
echo "Starting server on port 54321..."

# Start server
.venv/Scripts/python.exe -m uvicorn src.api.app:app \
  --host 0.0.0.0 \
  --port 54321 \
  --log-level info
