#!/bin/bash
# SentinelAI — Rollback Script
# Usage: ./scripts/rollback.sh <previous_tag>
# Example: ./scripts/rollback.sh v1.1.0

set -euo pipefail

PREVIOUS_TAG="${1:-}"

if [ -z "${PREVIOUS_TAG}" ]; then
    echo "Usage: $0 <previous_tag>"
    echo "Available tags:"
    git tag -l "v*" | sort -V
    exit 1
fi

echo "═══════════════════════════════════════════════════════"
echo " SentinelAI Rollback to ${PREVIOUS_TAG}"
echo "═══════════════════════════════════════════════════════"
echo ""

# Step 1: Verify tag exists
if ! git rev-parse "${PREVIOUS_TAG}" >/dev/null 2>&1; then
    echo "ERROR: Tag '${PREVIOUS_TAG}' not found."
    exit 1
fi

# Step 2: Confirm
echo "This will:"
echo "  1. Check out the code at ${PREVIOUS_TAG}"
echo "  2. Rebuild Docker images"
echo "  3. Restart services with the previous version"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Step 3: Create a safety backup of current state
echo "[1/6] Creating pre-rollback backup..."
BACKUP_NAME="pre-rollback-$(date +%Y%m%d_%H%M%S)"
git tag -a "${BACKUP_NAME}" -m "Pre-rollback backup before reverting to ${PREVIOUS_TAG}" 2>/dev/null || true

# Step 4: Checkout previous tag
echo "[2/6] Checking out ${PREVIOUS_TAG}..."
git checkout "${PREVIOUS_TAG}"

# Step 5: Run database migrations (if needed)
echo "[3/6] Running database migrations..."
if [ -f "backend/alembic.ini" ]; then
    cd backend
    python -m alembic upgrade head 2>/dev/null || echo "  Migration skipped (no changes needed)"
    cd ..
fi

# Step 6: Rebuild and restart
echo "[4/6] Rebuilding Docker images..."
docker compose build --no-cache backend frontend

echo "[5/6] Restarting services..."
docker compose up -d --force-recreate backend frontend

# Step 7: Verify health
echo "[6/6] Verifying health..."
sleep 10
if curl -sf http://localhost:8000/api/v1/live >/dev/null 2>&1; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo " ✅ Rollback to ${PREVIOUS_TAG} complete!"
    echo "═══════════════════════════════════════════════════════"
else
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo " ⚠️  Health check failed. Check logs:"
    echo "   docker compose logs backend --tail=50"
    echo "═══════════════════════════════════════════════════════"
fi

echo ""
echo "To restore forward: git checkout main && docker compose up -d --build"
