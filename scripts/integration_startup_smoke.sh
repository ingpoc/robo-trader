#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-robo-trader:integration-smoke}"
NETWORK_NAME="${NETWORK_NAME:-robo-trader-integration-net}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-robo-trader-int-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-robo-trader-int-redis}"
APP_CONTAINER="${APP_CONTAINER:-robo-trader-int-app}"
APP_PORT="${APP_PORT:-8000}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-60}"

require_command() {
    local command_name="$1"
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name"
        exit 1
    fi
}

cleanup() {
    docker rm -f "$APP_CONTAINER" "$REDIS_CONTAINER" "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
    docker network rm "$NETWORK_NAME" >/dev/null 2>&1 || true
}

trap cleanup EXIT

cd "$PROJECT_ROOT"

require_command docker
require_command curl

docker rm -f "$APP_CONTAINER" "$REDIS_CONTAINER" "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
docker network rm "$NETWORK_NAME" >/dev/null 2>&1 || true

docker build -t "$IMAGE_TAG" .
docker network create "$NETWORK_NAME" >/dev/null

docker run -d \
    --name "$POSTGRES_CONTAINER" \
    --network "$NETWORK_NAME" \
    -e POSTGRES_DB=robo_trader_integration \
    -e POSTGRES_USER=test_user \
    -e POSTGRES_PASSWORD=test_password \
    postgres:15-alpine >/dev/null

docker run -d \
    --name "$REDIS_CONTAINER" \
    --network "$NETWORK_NAME" \
    redis:7-alpine >/dev/null

docker run -d \
    --name "$APP_CONTAINER" \
    --network "$NETWORK_NAME" \
    -p "${APP_PORT}:8000" \
    -e DATABASE_URL=postgresql://test_user:test_password@"$POSTGRES_CONTAINER":5432/robo_trader_integration \
    -e REDIS_URL=redis://"$REDIS_CONTAINER":6379/0 \
    -e ENVIRONMENT=testing \
    "$IMAGE_TAG" >/dev/null

deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
until curl -fsS "http://127.0.0.1:${APP_PORT}/api/health" >/dev/null; do
    if [ "$SECONDS" -ge "$deadline" ]; then
        echo "Application failed to become ready within ${HEALTH_TIMEOUT_SECONDS}s"
        docker logs "$APP_CONTAINER" || true
        exit 1
    fi
    sleep 2
done

echo "Integration startup smoke passed."
