# Deployment Guide

Complete guide for deploying Poolula Platform to production and staging environments.

## Overview

Poolula Platform deployment supports multiple environments:

- **Local Development** - SQLite database, hot reload

- **Staging** - Test environment with production-like setup

- **Production** - Live system for LLC operations

### Deployment Checklist

**Before deploying:**

- [ ] All tests passing (`uv run pytest`)

- [ ] Database migrations created and tested

- [ ] Environment variables configured

- [ ] Backup created (`python scripts/backup.py`)

- [ ] Dependencies updated (`uv sync`)

- [ ] API documentation reviewed

- [ ] Security review complete (secrets, permissions)

## Local Development

### Starting the API Server

```bash
# Start with hot reload
uv run uvicorn apps.api.main:app --reload --port 8082

# Access at:
# http://localhost:8082
```

### Development Configuration

**Environment variables (.env):**

```env
# Database
DATABASE_URL=sqlite:///./poolula.db

# API
API_HOST=0.0.0.0
API_PORT=8082
API_RELOAD=true

# AI (Phase 2+)
ANTHROPIC_API_KEY=sk-ant-...

# Logging
DEBUG=false
LOG_LEVEL=INFO
```

### Running All Services Locally

```bash
# Terminal 1: API server
uv run uvicorn apps.api.main:app --reload --port 8082

# Terminal 2: Watch tests (optional)
uv run pytest-watch

# Terminal 3: Frontend (Phase 4+)
cd frontend && npm run dev
```

## Staging Deployment

### Purpose

**Staging mirrors production for testing:**

- Production database engine (PostgreSQL)

- Production-like data volume

- Same deployment process

- Integration testing

- QA validation

### Setup Staging Environment

**1. Create staging database:**

```bash
# PostgreSQL (recommended for staging)
createdb poolula_staging

# Set connection string
export DATABASE_URL=postgresql://user:pass@localhost/poolula_staging
```

**2. Apply migrations:**

```bash
.venv/bin/alembic upgrade head
```

**3. Seed staging data:**

```bash
# Use seed scripts
uv run python scripts/seed_database.py --initial
uv run python scripts/seed_obligations.py --year 2025
```

**4. Start staging server:**

```bash
# Port 8083 for staging
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8083
```

### Staging Workflow

```
1. Deploy to staging → 2. Run tests → 3. QA review → 4. Deploy to production
```

**Testing on staging:**

```bash
# Run full test suite
uv run pytest

# Run API integration tests
curl http://staging.poolula.com:8083/health

# Test chatbot queries
curl -X POST http://staging.poolula.com:8083/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our property address?"}'
```

## Production Deployment

### Production Architecture

**Components:**

- **API Server** - FastAPI on port 8082 (or 80/443 with reverse proxy)

- **Database** - SQLite (current) or PostgreSQL (recommended for scale)

- **Vector Store** - ChromaDB for document embeddings

- **Web Server** - Nginx reverse proxy (optional)

- **SSL/TLS** - Let's Encrypt certificates (if public)

### Deployment Options

**Option 1: Simple VPS (Recommended for Phase 1-3)**

Deploy to a single VPS (DigitalOcean, Linode, etc.):

- 1-2 GB RAM

- 20-40 GB SSD

- Ubuntu 22.04 LTS

**Option 2: Docker (Phase 4+)**

Containerized deployment with Docker Compose.

**Option 3: Cloud Platform (Future)**

AWS, Google Cloud, or Azure for scale.

## VPS Deployment (Step-by-Step)

### 1. Provision Server

```bash
# SSH into server
ssh user@poolula-server.com

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.13 python3-pip git sqlite3 nginx
```

### 2. Setup Application

```bash
# Clone repository
git clone https://github.com/yourusername/poolula-platform.git
cd poolula-platform

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install production dependencies (Phase 2+)
uv sync --group rag
```

### 3. Configure Environment

```bash
# Create production .env
cat > .env << EOF
DATABASE_URL=sqlite:///./poolula.db
API_HOST=0.0.0.0
API_PORT=8082
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
DEBUG=false
LOG_LEVEL=WARNING
EOF

# Secure permissions
chmod 600 .env
```

### 4. Initialize Database

```bash
# Run migrations
.venv/bin/alembic upgrade head

# Seed initial data
uv run python scripts/seed_database.py --initial
uv run python scripts/seed_obligations.py
```

### 5. Setup Systemd Service

Create service file for automatic restart:

```bash
# Create service file
sudo nano /etc/systemd/system/poolula-api.service
```

**Service configuration:**

```ini
[Unit]
Description=Poolula Platform API
After=network.target

[Service]
Type=simple
User=poolula
Group=poolula
WorkingDirectory=/home/poolula/poolula-platform
Environment="PATH=/home/poolula/poolula-platform/.venv/bin"
ExecStart=/home/poolula/poolula-platform/.venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8082
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable poolula-api

# Start service
sudo systemctl start poolula-api

# Check status
sudo systemctl status poolula-api
```

### 6. Configure Nginx Reverse Proxy

**Nginx configuration:**

```nginx
# /etc/nginx/sites-available/poolula

server {
    listen 80;
    server_name poolula.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site:**

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/poolula /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 7. Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d poolula.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

**Nginx will be automatically updated for HTTPS:**

```nginx
server {
    listen 443 ssl;
    server_name poolula.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/poolula.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/poolula.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8082;
        ...
    }
}
```

### 8. Setup Monitoring

**Basic health check:**

```bash
# Create health check script
cat > ~/check_health.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/health)
if [ "$RESPONSE" != "200" ]; then
    echo "API health check failed: $RESPONSE"
    sudo systemctl restart poolula-api
fi
EOF

chmod +x ~/check_health.sh
```

**Add to crontab:**

```bash
# Run every 5 minutes
crontab -e

# Add line:
*/5 * * * * /home/poolula/check_health.sh >> /var/log/poolula-health.log 2>&1
```

## Docker Deployment (Phase 4+)

### Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8082"]
```

### Docker Compose

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8082:8082"
    environment:
      - DATABASE_URL=postgresql://poolula:password@db:5432/poolula
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
    restart: always

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=poolula
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=poolula
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api
    restart: always

volumes:
  postgres_data:
```

**Deploy with Docker Compose:**

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Database Migration in Production

### Pre-Deployment

```bash
# 1. Create backup
python scripts/backup.py

# 2. Test migration locally
.venv/bin/alembic upgrade head

# 3. Test rollback locally
.venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head
```

### During Deployment

```bash
# 1. Stop API (brief downtime)
sudo systemctl stop poolula-api

# 2. Backup production database
python scripts/backup.py

# 3. Apply migrations
.venv/bin/alembic upgrade head

# 4. Start API
sudo systemctl start poolula-api

# 5. Verify health
curl http://localhost:8082/health
```

### Zero-Downtime Migration

For critical production systems:

1. **Add new columns (nullable)**

2. **Deploy code that writes to old + new columns**

3. **Backfill data**

4. **Deploy code that only uses new columns**

5. **Drop old columns**

See [Migrations Guide](migrations.md#zero-downtime-migrations) for details.

## Rollback Strategy

### API Rollback

```bash
# Revert to previous git commit
git checkout <previous-commit>

# Restart service
sudo systemctl restart poolula-api
```

### Database Rollback

```bash
# Rollback one migration
.venv/bin/alembic downgrade -1

# Restore from backup (if needed)
python scripts/backup.py --restore latest
```

### Full Rollback Procedure

```bash
# 1. Stop API
sudo systemctl stop poolula-api

# 2. Restore database from backup
python scripts/backup.py --restore <backup-name>

# 3. Checkout previous code version
git checkout <previous-tag>

# 4. Restart API
sudo systemctl start poolula-api

# 5. Verify
curl http://localhost:8082/health
```

## Monitoring and Logging

### Application Logs

**Systemd journal:**

```bash
# View logs
sudo journalctl -u poolula-api -f

# Last 100 lines
sudo journalctl -u poolula-api -n 100

# Since yesterday
sudo journalctl -u poolula-api --since yesterday
```

**Application log file:**

```bash
# Configure in .env
LOG_FILE=/var/log/poolula/app.log

# Tail logs
tail -f /var/log/poolula/app.log
```

### Error Tracking

**Log rotation:**

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/poolula
```

**Configuration:**

```
/var/log/poolula/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 poolula poolula
    sharedscripts
    postrotate
        systemctl reload poolula-api > /dev/null 2>&1 || true
    endscript
}
```

### Performance Monitoring

**Basic metrics:**

```bash
# API response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8082/health

# Where curl-format.txt contains:
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_starttransfer:  %{time_starttransfer}\n
time_total:  %{time_total}\n
```

**Database size:**

```bash
# SQLite
du -h poolula.db

# PostgreSQL
psql -c "SELECT pg_size_pretty(pg_database_size('poolula'));"
```

## Security Considerations

### Environment Variables

**Never commit secrets:**

```bash
# Add to .gitignore
.env
*.key
*.pem
```

**Use secret management:**

```bash
# Production: Use systemd environment files
sudo nano /etc/poolula/secrets.env

# Reference in service file:
EnvironmentFile=/etc/poolula/secrets.env
```

### Database Security

**SQLite:**

```bash
# Set restrictive permissions
chmod 600 poolula.db
chown poolula:poolula poolula.db
```

**PostgreSQL:**

- Use strong passwords

- Restrict network access (bind to localhost or VPC)

- Enable SSL connections

- Regular backups

### API Security

**Rate limiting (Phase 4+):**

```python
from fastapi import FastAPI
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

**CORS configuration:**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 8082/tcp     # Block direct API access
sudo ufw enable
```

## Backup and Recovery

### Automated Backups

**Cron job for daily backups:**

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /home/poolula/poolula-platform && python scripts/backup.py >> /var/log/poolula/backup.log 2>&1
```

**Backup script features:**

- Automatic timestamping

- Compression

- Retention policy (keep last 30 days)

- Off-site copy (rsync to backup server)

### Disaster Recovery

**Recovery procedure:**

```bash
# 1. Provision new server

# 2. Install application

# 3. Restore database from backup
python scripts/backup.py --restore latest

# 4. Apply any pending migrations
.venv/bin/alembic upgrade head

# 5. Start services
sudo systemctl start poolula-api
```

**Test recovery quarterly:**

```bash
# Schedule disaster recovery drills
# Q1, Q2, Q3, Q4: Restore to staging and verify
```

## CI/CD Pipeline (Phase 4+)

### GitHub Actions Example

**.github/workflows/deploy.yml:**

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/poolula/poolula-platform
            git pull origin main
            .venv/bin/alembic upgrade head
            sudo systemctl restart poolula-api
```

## Troubleshooting

### Service Won't Start

**Check logs:**

```bash
sudo journalctl -u poolula-api -n 50
```

**Common issues:**

- Port already in use: `sudo lsof -i :8082`

- Database connection failed: Check DATABASE_URL

- Missing dependencies: `uv sync`

- Permission denied: Check file ownership

### Database Migration Fails

**Check migration status:**

```bash
.venv/bin/alembic current
.venv/bin/alembic history
```

**Resolve conflicts:**

```bash
# Stamp current version
.venv/bin/alembic stamp head

# Or restore from backup and retry
```

### Out of Disk Space

**Check disk usage:**

```bash
df -h
du -sh /home/poolula/*
```

**Clean up:**

```bash
# Remove old backups
find backups/ -mtime +30 -delete

# Clean up logs
sudo journalctl --vacuum-time=7d

# Clean pip cache
pip cache purge
```

## Related Documentation

- [Migrations Guide](migrations.md) - Database migrations
- [Testing Guide](testing.md) - Pre-deployment testing
- Backup tool: `scripts/backup.py`
- [Architecture Overview](../architecture/system-design.md) - System architecture

## External Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)

- [Nginx Configuration](https://nginx.org/en/docs/)

- [Let's Encrypt](https://letsencrypt.org/getting-started/)
