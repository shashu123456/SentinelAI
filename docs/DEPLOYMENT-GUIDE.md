# SentinelAI — Deployment Guide

Complete guide for deploying SentinelAI to any environment.

---

## Quick Start (One-Click Docker)

```bash
git clone https://github.com/your-org/sentinelai.git
cd sentinelai
./scripts/deploy.sh
```

Open http://localhost — done.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Compose (Recommended)](#docker-compose)
3. [Cloud Deployment](#cloud-deployment)
4. [Terraform](#terraform)
5. [Configuration](#configuration)
6. [Monitoring & Observability](#monitoring)
7. [Backups & Recovery](#backups)
8. [Scaling](#scaling)
9. [Security Checklist](#security)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Docker Deployment
- Docker Engine 24+ 
- Docker Compose v2+
- 2GB RAM minimum (4GB recommended)
- 10GB disk space

### Cloud Deployment
- AWS / Azure / GCP account
- Terraform 1.5+ (for IaC)
- Domain name (for production)
- SSL certificate (Let's Encrypt or managed)

---

## Docker Compose

### Core Services

```bash
# Start core stack
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f backend
```

### Full Stack (with Monitoring)

```bash
# Enable all profiles
docker compose --profile full up -d

# This starts: Backend, Frontend, Postgres, Redis, 
# Prometheus, Grafana, Loki, Alertmanager
```

### AI-Enhanced Stack

```bash
# With Ollama AI
docker compose --profile ai up -d

# Pull the AI model
docker compose exec ollama ollama pull mistral
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 80 | Web UI |
| Backend API | 8000 | REST API |
| API Docs | 8000/docs | OpenAPI/Swagger |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| Prometheus | 9090 | Metrics |
| Grafana | 3001 | Dashboards |
| Loki | 3100 | Logs |
| Alertmanager | 9093 | Alerts |

---

## Cloud Deployment

### AWS (ECS Fargate)

```bash
cd deploy/terraform/aws
terraform init
terraform plan -var="db_password=CHANGE_ME" -var="secret_key=CHANGE_ME"
terraform apply
```

### Render (One-Click)

1. Fork the repository
2. Go to [render.com](https://render.com)
3. Click "New" → "Blueprint"
4. Connect your GitHub repo
5. Render auto-detects `render.yaml`
6. Click "Apply"

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set environment variables
railway variables set SECRET_KEY=$(openssl rand -base64 48)
railway variables set POSTGRES_PASSWORD=$(openssl rand -base64 24)
railway variables set SENTINEL_ENV=production

# Deploy
railway up
```

### Vercel (Frontend Only)

```bash
cd frontend
npm install -g vercel
vercel --prod
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# CRITICAL: Change these before production
SECRET_KEY=<64-char-random-string>
POSTGRES_PASSWORD=<strong-password>

# Domain
CORS_ORIGINS=["https://yourdomain.com"]
REFRESH_TOKEN_COOKIE_SECURE=true

# AI (optional)
OLLAMA_MODEL=mistral
```

### Secrets Management

**Never commit `.env` to version control.**

For production:
- AWS: Use Secrets Manager or SSM Parameter Store
- Azure: Use Key Vault
- GCP: Use Secret Manager
- Docker: Use Docker secrets or external vault

---

## Monitoring

### Prometheus Metrics

Available at `http://localhost:9090`:
- HTTP request rate and latency
- Authentication events
- Scanner throughput
- Database connections
- Memory and CPU usage

### Grafana Dashboards

Available at `http://localhost:3001`:
- Pre-configured Prometheus datasource
- Import dashboards from `deploy/grafana/dashboards/`

### Alertmanager

Alerts are configured for:
- Service downtime (>1 minute)
- High error rate (>5%)
- High latency (p95 > 2s)
- Brute force attacks
- Database connection pool exhaustion
- Scan queue backlog

### Loki (Logs)

Centralized logging at `http://localhost:3100`:
- Structured JSON logs from all services
- 7-day retention
- Full-text search via Grafana

---

## Backups

### Automated Backups

```bash
# Run backup manually
docker compose --profile backup exec backup /backup.sh

# Schedule via cron (daily at 3 AM)
0 3 * * * docker compose --profile backup exec backup /backup.sh
```

### Backup Location

Backups are stored in `/backups/` inside the container.
For production, mount to S3/GCS/Azure Blob.

### Restore from Backup

```bash
# List backups
docker compose exec backup ls -la /backups/

# Restore
gunzip < /backups/sentinelai_YYYYMMDD_HHMMSS.sql.gz | \
    docker compose exec -T postgres psql -U sentinelai -d sentinelai
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale backend to 3 instances
docker compose up -d --scale backend=3

# Load balancing is handled by nginx
```

### Database Scaling

- **Read replicas**: Add `--read-replica` to RDS
- **Connection pooling**: Increase `pool_size` in database.py
- **Caching**: Redis handles 128MB with LRU eviction

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "1.0"
    reservations:
      memory: 256M
      cpus: "0.5"
```

---

## Security Checklist

### Before Deployment

- [ ] `SECRET_KEY` is a random 64+ character string
- [ ] `POSTGRES_PASSWORD` is strong and unique
- [ ] `.env` is NOT committed to git
- [ ] `CORS_ORIGINS` only includes your domain
- [ ] `REFRESH_TOKEN_COOKIE_SECURE=true`
- [ ] `ENABLE_SECURITY_HEADERS=true`
- [ ] HTTPS is configured (TLS termination)
- [ ] Database is not exposed to public internet
- [ ] Redis is not exposed to public internet
- [ ] Default Grafana password is changed

### Production Hardening

- [ ] Enable rate limiting at load balancer
- [ ] Configure WAF (CloudFlare, AWS WAF)
- [ ] Enable audit logging
- [ ] Set up intrusion detection
- [ ] Configure log shipping to SIEM
- [ ] Enable database encryption at rest
- [ ] Enable Redis encryption in transit
- [ ] Set up VPC/network isolation
- [ ] Configure security groups/firewall rules
- [ ] Enable container image scanning

---

## Troubleshooting

### Common Issues

**Backend won't start**
```bash
docker compose logs backend --tail=50
# Common: Database connection refused → check postgres is healthy
# Common: Missing SECRET_KEY → ensure .env is configured
```

**Database connection errors**
```bash
docker compose exec postgres pg_isready -U sentinelai
docker compose restart postgres
```

**Frontend shows blank page**
```bash
docker compose logs frontend --tail=20
# Check CORS_ORIGINS includes your domain
```

**High memory usage**
```bash
docker stats
# Restart if needed: docker compose restart backend
```

### Health Check Endpoints

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `/api/v1/live` | Liveness probe | 200 OK |
| `/api/v1/ready` | Readiness probe | 200 OK |
| `/api/v1/health` | Full health check | 200 + component status |
| `/api/health` | Simple health | `{"status": "healthy"}` |

### Useful Commands

```bash
# Service status
docker compose ps

# Follow logs
docker compose logs -f

# Restart a service
docker compose restart backend

# Rebuild after code changes
docker compose up -d --build

# Enter a container
docker compose exec backend bash

# Run database migrations
docker compose exec backend python -m alembic upgrade head

# Create a backup
docker compose --profile backup exec backup /backup.sh

# Rollback to previous version
./scripts/rollback.sh v1.1.0
```

---

## Disaster Recovery

### Recovery Time Objective (RTO): 15 minutes
### Recovery Point Objective (RPO): 1 hour (with automated backups)

### Recovery Steps

1. **Service failure**: `docker compose restart <service>`
2. **Database failure**: Restore from latest backup
3. **Full outage**: `./scripts/deploy.sh` (rebuilds everything)
4. **Bad deployment**: `./scripts/rollback.sh <previous-tag>`
5. **Data corruption**: Restore from point-in-time backup

---

## Version Management

```bash
# Check current version
docker compose exec backend python -c "from app.config import get_settings; print(get_settings().VERSION)"

# Upgrade
git pull origin main
docker compose up -d --build

# Rollback
./scripts/rollback.sh v1.1.0
```
