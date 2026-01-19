# B2B AI E-commerce Content Generator - Deployment Guide

This comprehensive guide covers deployment options for the B2B AI E-commerce Content Generator across different environments and platforms.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Configuration](#environment-configuration)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Platform Deployment](#cloud-platform-deployment)
6. [Monitoring and Observability](#monitoring-and-observability)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance and Updates](#maintenance-and-updates)

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- At least 2GB RAM and 1 CPU core available

### 1-Minute Deployment

```bash
# Clone the repository
git clone <repository-url>
cd b2b-ai-ecommerce-content-generator

# Copy environment configuration
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or use your preferred editor

# Deploy with Docker Compose
./deployment/deploy.sh deploy

# Access the application
open http://localhost:8501
```

## Environment Configuration

### Environment Files

The application supports multiple environment configurations:

| Environment | File                     | Description                              |
| ----------- | ------------------------ | ---------------------------------------- |
| Development | `.env` or `.env.example` | Local development with debug enabled     |
| Staging     | `.env.staging`           | Pre-production testing environment       |
| Production  | `.env.production`        | Production deployment with optimizations |

### Required Configuration

All environments require these essential settings:

```bash
# OpenAI API Configuration (REQUIRED)
OPENAI_API_KEY=your_openai_api_key_here

# Application Environment
APP_ENV=production  # development|staging|production
DEBUG=false         # true for development
```

### Optional Configuration

```bash
# File Processing
MAX_FILE_SIZE_MB=100
CSV_CHUNK_SIZE=200

# API Settings
MAX_RETRIES=5
RETRY_DELAY_BASE=2.0
RATE_LIMIT_DELAY=120

# Security
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# Performance
MEMORY_LIMIT=1G
CPU_LIMIT=0.5
```

## Docker Deployment

### Basic Deployment

Deploy the application with minimal configuration:

```bash
# Using the deployment script
./deployment/deploy.sh -e production deploy

# Or manually with Docker Compose
docker-compose up -d app
```

### Full Stack Deployment

Deploy with reverse proxy and additional services:

```bash
# Deploy with production profile (includes Nginx)
./deployment/deploy.sh -e production -p production deploy

# Deploy with monitoring (includes Prometheus and Grafana)
./deployment/deploy.sh -e production -p monitoring deploy
```

### Docker Compose Profiles

| Profile      | Services                   | Use Case                        |
| ------------ | -------------------------- | ------------------------------- |
| `basic`      | App only                   | Development, simple deployments |
| `production` | App + Nginx + Redis        | Production with load balancing  |
| `monitoring` | All + Prometheus + Grafana | Full observability stack        |

### Custom Docker Build

```bash
# Build custom image
docker build -t b2b-ai-content-generator:custom .

# Run with custom image
docker run -d \
  --name b2b-ai-app \
  -p 8501:8501 \
  -e OPENAI_API_KEY=your_key_here \
  -e APP_ENV=production \
  b2b-ai-content-generator:custom
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Ingress controller (nginx recommended)
- Cert-manager (for SSL certificates)

### Quick Kubernetes Deployment

```bash
# Apply all Kubernetes manifests
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods -n b2b-ai-content-generator

# Get service URL
kubectl get ingress -n b2b-ai-content-generator
```

### Step-by-Step Kubernetes Deployment

1. **Create namespace:**

   ```bash
   kubectl apply -f deployment/kubernetes/namespace.yaml
   ```

2. **Configure secrets:**

   ```bash
   # Create secret with your OpenAI API key
   kubectl create secret generic b2b-ai-app-secrets \
     --from-literal=OPENAI_API_KEY=your_openai_api_key_here \
     -n b2b-ai-content-generator
   ```

3. **Apply configuration:**

   ```bash
   kubectl apply -f deployment/kubernetes/configmap.yaml
   kubectl apply -f deployment/kubernetes/pvc.yaml
   ```

4. **Deploy application:**

   ```bash
   kubectl apply -f deployment/kubernetes/deployment.yaml
   kubectl apply -f deployment/kubernetes/service.yaml
   ```

5. **Configure ingress:**
   ```bash
   # Edit ingress.yaml to set your domain
   nano deployment/kubernetes/ingress.yaml
   kubectl apply -f deployment/kubernetes/ingress.yaml
   ```

### Scaling

```bash
# Scale to 3 replicas
kubectl scale deployment b2b-ai-app --replicas=3 -n b2b-ai-content-generator

# Auto-scaling (requires metrics-server)
kubectl autoscale deployment b2b-ai-app \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n b2b-ai-content-generator
```

## Cloud Platform Deployment

### AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker build -t b2b-ai-content-generator .
docker tag b2b-ai-content-generator:latest <account>.dkr.ecr.us-west-2.amazonaws.com/b2b-ai-content-generator:latest
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/b2b-ai-content-generator:latest

# Deploy with ECS CLI or CloudFormation
# See deployment/aws/ directory for templates
```

### Google Cloud Run

```bash
# Build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/b2b-ai-content-generator
gcloud run deploy b2b-ai-content-generator \
  --image gcr.io/PROJECT_ID/b2b-ai-content-generator \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your_key_here,APP_ENV=production
```

### Azure Container Instances

```bash
# Create resource group
az group create --name b2b-ai-rg --location eastus

# Deploy container
az container create \
  --resource-group b2b-ai-rg \
  --name b2b-ai-app \
  --image b2b-ai-content-generator:latest \
  --dns-name-label b2b-ai-unique \
  --ports 8501 \
  --environment-variables OPENAI_API_KEY=your_key_here APP_ENV=production
```

### Heroku

```bash
# Login and create app
heroku login
heroku create your-app-name

# Set environment variables
heroku config:set OPENAI_API_KEY=your_key_here
heroku config:set APP_ENV=production

# Deploy
git push heroku main
```

## Monitoring and Observability

### Built-in Monitoring

The application includes comprehensive logging and monitoring:

- **Application logs**: Structured JSON logging
- **Performance metrics**: Request timing and resource usage
- **Health checks**: Endpoint for load balancer health checks
- **Error tracking**: Detailed error logging with context

### Prometheus Metrics

When deployed with the monitoring profile:

```bash
# Access Prometheus
open http://localhost:9090

# Key metrics to monitor:
# - streamlit_requests_total
# - streamlit_request_duration_seconds
# - streamlit_active_sessions
# - python_memory_usage_bytes
```

### Grafana Dashboards

```bash
# Access Grafana
open http://localhost:3000
# Default credentials: admin/admin (change on first login)

# Pre-configured dashboards:
# - Application Overview
# - Performance Metrics
# - Error Tracking
# - Resource Usage
```

### Log Aggregation

For production deployments, consider:

- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Fluentd**: Log collection and forwarding
- **Cloud logging**: AWS CloudWatch, Google Cloud Logging, Azure Monitor

## Security Considerations

### Container Security

- **Non-root user**: Application runs as non-root user (UID 1000)
- **Read-only filesystem**: Where possible, use read-only containers
- **Security scanning**: Regularly scan images for vulnerabilities
- **Minimal base image**: Uses slim Python image to reduce attack surface

### Network Security

- **TLS encryption**: Always use HTTPS in production
- **Rate limiting**: Nginx configuration includes rate limiting
- **CORS protection**: Configurable CORS settings
- **XSRF protection**: Enabled by default in production

### Secrets Management

- **Environment variables**: Never commit secrets to version control
- **Kubernetes secrets**: Use native Kubernetes secret management
- **Cloud secret managers**: AWS Secrets Manager, Google Secret Manager, Azure Key Vault
- **Vault integration**: HashiCorp Vault for advanced secret management

### API Security

- **API key rotation**: Regularly rotate OpenAI API keys
- **Request validation**: Input sanitization and validation
- **Rate limiting**: Protect against API abuse
- **Audit logging**: Log all API requests for security monitoring

## Troubleshooting

### Common Issues

#### Application Won't Start

```bash
# Check logs
docker-compose logs app
# or
kubectl logs -f deployment/b2b-ai-app -n b2b-ai-content-generator

# Common causes:
# 1. Missing OPENAI_API_KEY
# 2. Invalid environment configuration
# 3. Port conflicts
# 4. Insufficient resources
```

#### Health Check Failures

```bash
# Test health endpoint directly
curl http://localhost:8501/_stcore/health

# Check resource usage
docker stats
# or
kubectl top pods -n b2b-ai-content-generator
```

#### Performance Issues

```bash
# Monitor resource usage
docker stats b2b-ai-content-generator
# or
kubectl top pods -n b2b-ai-content-generator

# Check application logs for errors
tail -f logs/app.log

# Adjust resource limits in docker-compose.yml or deployment.yaml
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set DEBUG=true in environment
export DEBUG=true

# Or in .env file
echo "DEBUG=true" >> .env

# Restart application
./deployment/deploy.sh restart
```

### Log Analysis

```bash
# View application logs
./deployment/deploy.sh logs

# Filter for errors
docker-compose logs app | grep ERROR

# Monitor in real-time
docker-compose logs -f app
```

## Maintenance and Updates

### Regular Maintenance Tasks

1. **Update dependencies**: Monthly security updates
2. **Rotate secrets**: Quarterly API key rotation
3. **Monitor resources**: Weekly resource usage review
4. **Backup data**: Daily backup of persistent volumes
5. **Security scans**: Weekly vulnerability scans

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
./deployment/deploy.sh -f deploy

# Or with zero-downtime (Kubernetes)
kubectl set image deployment/b2b-ai-app app=b2b-ai-content-generator:new-version -n b2b-ai-content-generator
```

### Backup and Restore

```bash
# Create backup
./deployment/deploy.sh backup

# Restore from backup
./deployment/deploy.sh restore /path/to/backup

# Kubernetes backup (using Velero or similar)
velero backup create b2b-ai-backup --include-namespaces b2b-ai-content-generator
```

### Rollback Procedures

```bash
# Docker Compose rollback
docker-compose down
git checkout previous-version
./deployment/deploy.sh deploy

# Kubernetes rollback
kubectl rollout undo deployment/b2b-ai-app -n b2b-ai-content-generator
kubectl rollout status deployment/b2b-ai-app -n b2b-ai-content-generator
```

## Performance Optimization

### Resource Tuning

Adjust resource limits based on your workload:

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G # Increase for large files
      cpus: "1.0" # Increase for concurrent users
    reservations:
      memory: 1G
      cpus: "0.5"
```

### Scaling Strategies

1. **Vertical scaling**: Increase CPU/memory per container
2. **Horizontal scaling**: Add more container replicas
3. **Load balancing**: Distribute traffic across instances
4. **Caching**: Implement Redis for session management

### Monitoring Performance

Key metrics to monitor:

- **Response time**: Target < 2 seconds for single products
- **Throughput**: Target > 50 products/minute for bulk processing
- **Error rate**: Target < 1% error rate
- **Resource usage**: Target < 80% CPU/memory utilization

## Support and Documentation

### Getting Help

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Comprehensive guides and API documentation
- **Community**: Join our community discussions
- **Professional Support**: Enterprise support available

### Additional Resources

- [API Documentation](API.md)
- [Configuration Reference](CONFIG.md)
- [Security Guide](SECURITY.md)
- [Performance Tuning](PERFORMANCE.md)
- [Monitoring Guide](MONITORING.md)

---

For questions or support, please open an issue on GitHub or contact our support team.
