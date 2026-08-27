#!/bin/bash
# SentinelAI — One-Click Deployment Script
# Usage: curl -sSL https://raw.githubusercontent.com/.../scripts/deploy.sh | bash
# Or: ./scripts/deploy.sh

set -euo pipefail

echo "═══════════════════════════════════════════════════════"
echo "  SentinelAI — Enterprise Security Platform"
echo "  Deployment Script v1.2.0"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── Step 1: Check prerequisites ─────────────────────────────
echo "[1/8] Checking prerequisites..."

check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "  ❌ $1 is not installed. Please install it first."
        exit 1
    fi
    echo "  ✅ $1 found: $(command -v "$1")"
}

check_command docker
check_command docker compose

# ── Step 2: Generate secrets ────────────────────────────────
echo ""
echo "[2/8] Generating secrets..."

if [ ! -f .env ]; then
    cp .env.example .env

    # Generate SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || openssl rand -base64 48 | tr -d '\n')
    POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 24 | tr -d '\n')
    GRAFANA_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || openssl rand -base64 12 | tr -d '\n')

    # Update .env with generated secrets
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env
        sed -i '' "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" .env
        sed -i '' "s|GRAFANA_PASSWORD=.*|GRAFANA_PASSWORD=${GRAFANA_PASSWORD}|" .env
    else
        sed -i "s|SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env
        sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" .env
        sed -i "s|GRAFANA_PASSWORD=.*|GRAFANA_PASSWORD=${GRAFANA_PASSWORD}|" .env
    fi

    echo "  ✅ .env created with generated secrets"
    echo "  ⚠️  IMPORTANT: Review and customize .env before production use"
else
    echo "  ✅ .env already exists, skipping"
fi

# ── Step 3: Pull latest images ──────────────────────────────
echo ""
echo "[3/8] Pulling latest images..."
docker compose pull 2>/dev/null || true

# ── Step 4: Build custom images ─────────────────────────────
echo ""
echo "[4/8] Building application images..."
docker compose build --parallel

# ── Step 5: Start database services first ───────────────────
echo ""
echo "[5/8] Starting database services..."
docker compose up -d postgres redis
echo "  Waiting for database to be ready..."
sleep 10

# ── Step 6: Run migrations ──────────────────────────────────
echo ""
echo "[6/8] Running database migrations..."
docker compose run --rm backend python -m alembic upgrade head 2>/dev/null || \
    echo "  ⚠️  Migrations may need manual attention"

# ── Step 7: Start all services ──────────────────────────────
echo ""
echo "[7/8] Starting all services..."
docker compose up -d

# ── Step 8: Health check ────────────────────────────────────
echo ""
echo "[8/8] Running health checks..."
echo "  Waiting for services to start..."
sleep 15

HEALTHY=true
check_endpoint() {
    local url=$1
    local name=$2
    if curl -sf "$url" >/dev/null 2>&1; then
        echo "  ✅ $name is healthy"
    else
        echo "  ❌ $name is not responding"
        HEALTHY=false
    fi
}

check_endpoint "http://localhost:8000/api/v1/live" "Backend"
check_endpoint "http://localhost:8000/api/v1/ready" "Readiness"
check_endpoint "http://localhost:80/" "Frontend"

echo ""
echo "═══════════════════════════════════════════════════════"

if [ "$HEALTHY" = true ]; then
    echo "  ✅ SentinelAI deployed successfully!"
else
    echo "  ⚠️  Some services are still starting up."
    echo "  Run: docker compose logs --tail=20"
fi

echo ""
echo "  🌐 Frontend:    http://localhost"
echo "  🔧 Backend API: http://localhost:8000"
echo "  📊 API Docs:    http://localhost:8000/docs"
echo "  📈 Prometheus:  http://localhost:9090 (with --profile observability)"
echo "  📉 Grafana:     http://localhost:3001 (with --profile observability)"
echo ""
echo "  Commands:"
echo "    docker compose logs -f           # View logs"
echo "    docker compose ps                # Service status"
echo "    docker compose --profile full up # Enable all services"
echo "    ./scripts/backup.sh              # Create backup"
echo "    ./scripts/rollback.sh v1.1.0     # Rollback"
echo "═══════════════════════════════════════════════════════"
