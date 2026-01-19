# Production Setup Guide

This guide provides step-by-step instructions for setting up the B2B AI E-commerce Content Generator in a production environment.

## Table of Contents

1. [Pre-deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Security Setup](#security-setup)
4. [Environment Configuration](#environment-configuration)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Database and Storage](#database-and-storage)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup Configuration](#backup-configuration)
9. [Performance Optimization](#performance-optimization)
10. [Go-Live Checklist](#go-live-checklist)

## Pre-deployment Checklist

### Required Resources

- [ ] **OpenAI API Key**: Valid API key with sufficient credits
- [ ] **Domain Name**: Registered domain for production access
- [ ] **SSL Certificate**: Valid SSL certificate or Let's Encrypt setup
- [ ] **Server Resources**: Minimum 2GB RAM, 2 CPU cores, 20GB storage
- [ ] **Backup Storage**: External storage for backups (S3, GCS, etc.)

### Required Tools

- [ ] **Docker**: Version 20.10+ installed
- [ ] **Docker Compose**: Version 2.0+ installed
- [ ] **Git**: For code deployment
- [ ] **Nginx**: For reverse proxy (if not using Docker)
- [ ] **Monitoring Tools**: Prometheus, Grafana (optional)

## Infrastructure Requirements

### Minimum System Requirements

```
CPU: 2 cores (4 cores recommended)
RAM: 2GB (4GB recommended)
Storage: 20GB (50GB recommended)
Network: 100Mbps (1Gbps recommended)
OS: Ubuntu 20.04 LTS or CentOS 8+
```

### Recommended Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│  Reverse Proxy  │────│   Application   │
│    (Optional)   │    │     (Nginx)     │    │   (Streamlit)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Monitoring    │
                       │ (Prometheus +   │
                       │    Grafana)     │
                       └─────────────────┘
```

### Cloud Provider Recommendations

#### AWS

- **EC2**: t3.medium or larger
- **ECS**: Fargate with 2 vCPU, 4GB RAM
- **EKS**: For Kubernetes deployment
- **ALB**: Application Load Balancer
- **S3**: For file storage and backups
- **CloudWatch**: For monitoring

#### Google Cloud

- **Compute Engine**: e2-medium or larger
- **Cloud Run**: 2 vCPU, 4GB RAM
- **GKE**: For Kubernetes deployment
- **Cloud Load Balancing**: For traffic distribution
- **Cloud Storage**: For file storage and backups
- **Cloud Monitoring**: For observability

#### Azure

- **Virtual Machines**: Standard_B2s or larger
- **Container Instances**: 2 vCPU, 4GB RAM
- **AKS**: For Kubernetes deployment
- **Application Gateway**: For load balancing
- **Blob Storage**: For file storage and backups
- **Azure Monitor**: For monitoring

## Security Setup

### 1. Firewall Configuration

```bash
# Ubuntu/Debian with ufw
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL with firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. SSH Hardening

```bash
# Disable root login and password authentication
sudo nano /etc/ssh/sshd_config

# Add/modify these lines:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Port 2222  # Change default port

sudo systemctl restart sshd
```

### 3. User Management

```bash
# Create application user
sudo useradd -m -s /bin/bash appuser
sudo usermod -aG docker appuser

# Setup SSH key for appuser
sudo mkdir -p /home/appuser/.ssh
sudo cp ~/.ssh/authorized_keys /home/appuser/.ssh/
sudo chown -R appuser:appuser /home/appuser/.ssh
sudo chmod 700 /home/appuser/.ssh
sudo chmod 600 /home/appuser/.ssh/authorized_keys
```

### 4. Secrets Management

```bash
# Create secure directory for secrets
sudo mkdir -p /etc/b2b-ai-secrets
sudo chown root:appuser /etc/b2b-ai-secrets
sudo chmod 750 /etc/b2b-ai-secrets

# Store OpenAI API key securely
echo "OPENAI_API_KEY=your_actual_api_key_here" | sudo tee /etc/b2b-ai-secrets/openai.env
sudo chmod 640 /etc/b2b-ai-secrets/openai.env
```

## Environment Configuration

### 1. Production Environment File

Create `/home/appuser/b2b-ai-app/.env`:

```bash
# Application Configuration
APP_ENV=production
DEBUG=false

# Load OpenAI API key from secure location
OPENAI_API_KEY_FILE=/etc/b2b-ai-secrets/openai.env

# Server Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Security Configuration
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# Performance Configuration
MAX_FILE_SIZE_MB=100
CSV_CHUNK_SIZE=200
MAX_RETRIES=5
RETRY_DELAY_BASE=2.0
RATE_LIMIT_DELAY=120

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/b2b-ai/app.log

# Resource Limits
MEMORY_LIMIT=2G
CPU_LIMIT=1.0
```

### 2. System Service Configuration

Create systemd service file `/etc/systemd/system/b2b-ai.service`:

```ini
[Unit]
Description=B2B AI E-commerce Content Generator
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/b2b-ai-app
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable b2b-ai
sudo systemctl start b2b-ai
```

## SSL/TLS Configuration

### Option 1: Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 2: Custom Certificate

```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Copy your certificate files
sudo cp your-cert.pem /etc/nginx/ssl/cert.pem
sudo cp your-key.pem /etc/nginx/ssl/key.pem

# Set proper permissions
sudo chmod 644 /etc/nginx/ssl/cert.pem
sudo chmod 600 /etc/nginx/ssl/key.pem
sudo chown root:root /etc/nginx/ssl/*
```

### Nginx SSL Configuration

Update `/etc/nginx/sites-available/b2b-ai`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Database and Storage

### File Storage Configuration

```bash
# Create persistent storage directories
sudo mkdir -p /var/lib/b2b-ai/{logs,uploads,downloads,backups}
sudo chown -R appuser:appuser /var/lib/b2b-ai
sudo chmod 755 /var/lib/b2b-ai

# Mount external storage (optional)
# Add to /etc/fstab for persistent mounting
/dev/sdb1 /var/lib/b2b-ai ext4 defaults 0 2
```

### Log Management

```bash
# Configure logrotate
sudo tee /etc/logrotate.d/b2b-ai << EOF
/var/log/b2b-ai/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 appuser appuser
    postrotate
        docker-compose -f /home/appuser/b2b-ai-app/docker-compose.yml restart app
    endscript
}
EOF
```

## Monitoring Setup

### 1. System Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Setup system metrics collection
sudo tee /etc/cron.d/system-metrics << EOF
*/5 * * * * root /usr/bin/free -m >> /var/log/memory-usage.log
*/5 * * * * root /usr/bin/df -h >> /var/log/disk-usage.log
EOF
```

### 2. Application Monitoring

Deploy with monitoring profile:

```bash
cd /home/appuser/b2b-ai-app
./deployment/deploy.sh -e production -p monitoring deploy
```

### 3. Health Check Automation

```bash
# Setup automated health checks
sudo tee /etc/cron.d/b2b-ai-health << EOF
*/5 * * * * appuser /home/appuser/b2b-ai-app/deployment/scripts/health-check.sh --quick >> /var/log/b2b-ai-health.log 2>&1
0 */6 * * * appuser /home/appuser/b2b-ai-app/deployment/scripts/health-check.sh --report >> /var/log/b2b-ai-health-report.log 2>&1
EOF
```

### 4. Alerting Setup

```bash
# Install mail utilities for alerts
sudo apt install mailutils

# Create alert script
sudo tee /usr/local/bin/b2b-ai-alert << 'EOF'
#!/bin/bash
if ! /home/appuser/b2b-ai-app/deployment/scripts/health-check.sh --quick; then
    echo "B2B AI Application health check failed at $(date)" | mail -s "B2B AI Alert" admin@your-domain.com
fi
EOF

sudo chmod +x /usr/local/bin/b2b-ai-alert

# Add to cron
echo "*/10 * * * * root /usr/local/bin/b2b-ai-alert" | sudo tee -a /etc/crontab
```

## Backup Configuration

### 1. Automated Backups

```bash
# Create backup script
sudo tee /usr/local/bin/b2b-ai-backup << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/lib/b2b-ai/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup application data
cd /home/appuser/b2b-ai-app
./deployment/deploy.sh backup

# Backup to cloud storage (example with AWS S3)
if command -v aws &> /dev/null; then
    aws s3 sync /var/lib/b2b-ai/backups/ s3://your-backup-bucket/b2b-ai-backups/
fi

# Cleanup old local backups (keep 7 days)
find /var/lib/b2b-ai/backups/ -type d -mtime +7 -exec rm -rf {} +
EOF

sudo chmod +x /usr/local/bin/b2b-ai-backup

# Schedule daily backups
echo "0 2 * * * root /usr/local/bin/b2b-ai-backup" | sudo tee -a /etc/crontab
```

### 2. Database Backup (if using external database)

```bash
# Example for PostgreSQL
sudo tee /usr/local/bin/db-backup << 'EOF'
#!/bin/bash
BACKUP_FILE="/var/lib/b2b-ai/backups/db_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h localhost -U dbuser -d b2b_ai_db > "$BACKUP_FILE"
gzip "$BACKUP_FILE"
EOF
```

## Performance Optimization

### 1. System Optimization

```bash
# Optimize kernel parameters
sudo tee -a /etc/sysctl.conf << EOF
# Network optimization
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# File descriptor limits
fs.file-max = 65536
EOF

sudo sysctl -p
```

### 2. Docker Optimization

```bash
# Configure Docker daemon
sudo tee /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
EOF

sudo systemctl restart docker
```

### 3. Application Optimization

Update docker-compose.yml for production:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
        reservations:
          memory: 1G
          cpus: "0.5"
    environment:
      - STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
      - STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

## Go-Live Checklist

### Pre-Launch

- [ ] **Environment Configuration**: All environment variables set correctly
- [ ] **SSL Certificate**: Valid SSL certificate installed and configured
- [ ] **DNS Configuration**: Domain pointing to production server
- [ ] **Firewall Rules**: Only necessary ports open
- [ ] **Backup System**: Automated backups configured and tested
- [ ] **Monitoring**: Health checks and alerting configured
- [ ] **Performance Testing**: Load testing completed successfully
- [ ] **Security Scan**: Vulnerability assessment completed

### Launch Day

- [ ] **Final Deployment**: Deploy latest code to production
- [ ] **Health Check**: Verify all services are running
- [ ] **SSL Verification**: Confirm HTTPS is working correctly
- [ ] **Performance Check**: Verify response times are acceptable
- [ ] **Monitoring Verification**: Confirm all monitoring is active
- [ ] **Backup Test**: Verify backup system is working
- [ ] **User Acceptance**: Conduct final user acceptance testing

### Post-Launch

- [ ] **Monitor Logs**: Watch application logs for errors
- [ ] **Performance Monitoring**: Monitor response times and resource usage
- [ ] **User Feedback**: Collect and address user feedback
- [ ] **Security Monitoring**: Monitor for security incidents
- [ ] **Backup Verification**: Verify backups are being created successfully
- [ ] **Documentation Update**: Update documentation with any changes

## Troubleshooting Common Issues

### Application Won't Start

```bash
# Check Docker containers
docker-compose ps

# Check logs
docker-compose logs app

# Check system resources
free -h
df -h
```

### SSL Certificate Issues

```bash
# Test SSL certificate
openssl s_client -connect your-domain.com:443

# Check certificate expiration
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates
```

### Performance Issues

```bash
# Monitor resource usage
htop
iotop
nethogs

# Check application metrics
curl http://localhost:8501/_stcore/health
```

### Backup Issues

```bash
# Test backup restoration
./deployment/deploy.sh restore /path/to/backup

# Verify backup integrity
tar -tzf backup.tar.gz
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review logs and performance metrics
2. **Monthly**: Update system packages and security patches
3. **Quarterly**: Review and rotate API keys and certificates
4. **Annually**: Conduct security audit and disaster recovery testing

### Emergency Procedures

1. **Service Outage**: Follow incident response plan
2. **Security Breach**: Isolate system and assess damage
3. **Data Loss**: Restore from most recent backup
4. **Performance Degradation**: Scale resources or optimize configuration

For additional support, refer to the main [DEPLOYMENT.md](DEPLOYMENT.md) guide or contact the development team.
