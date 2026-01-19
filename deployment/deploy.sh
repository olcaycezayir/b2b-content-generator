#!/bin/bash

# B2B AI E-commerce Content Generator - Deployment Script
# Supports multiple environments: development, staging, production

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_ENV="development"
DEFAULT_PROFILE="basic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
B2B AI E-commerce Content Generator - Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy      Deploy the application
    stop        Stop the application
    restart     Restart the application
    logs        Show application logs
    status      Show application status
    cleanup     Clean up unused resources
    backup      Backup application data
    restore     Restore application data

Options:
    -e, --env ENV           Environment (development|staging|production) [default: $DEFAULT_ENV]
    -p, --profile PROFILE   Docker Compose profile (basic|production|monitoring) [default: $DEFAULT_PROFILE]
    -f, --force            Force operation without confirmation
    -v, --verbose          Verbose output
    -h, --help             Show this help message

Examples:
    $0 deploy                           # Deploy in development mode
    $0 -e production -p production deploy  # Deploy in production with full stack
    $0 -e staging logs                  # Show logs for staging environment
    $0 cleanup                          # Clean up unused Docker resources

Environment Files:
    development: Uses .env (or .env.example if .env doesn't exist)
    staging:     Uses .env.staging
    production:  Uses .env.production

Profiles:
    basic:      App only (default)
    production: App + Nginx + Redis
    monitoring: App + Nginx + Redis + Prometheus + Grafana

EOF
}

# Parse command line arguments
parse_args() {
    ENVIRONMENT="$DEFAULT_ENV"
    PROFILE="$DEFAULT_PROFILE"
    FORCE=false
    VERBOSE=false
    COMMAND=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--profile)
                PROFILE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            deploy|stop|restart|logs|status|cleanup|backup|restore)
                COMMAND="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
}

# Validate environment
validate_environment() {
    case "$ENVIRONMENT" in
        development|staging|production)
            log_info "Environment: $ENVIRONMENT"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Valid environments: development, staging, production"
            exit 1
            ;;
    esac

    case "$PROFILE" in
        basic|production|monitoring)
            log_info "Profile: $PROFILE"
            ;;
        *)
            log_error "Invalid profile: $PROFILE"
            log_error "Valid profiles: basic, production, monitoring"
            exit 1
            ;;
    esac
}

# Setup environment file
setup_env_file() {
    local env_file=""
    
    case "$ENVIRONMENT" in
        development)
            if [[ -f "$PROJECT_ROOT/.env" ]]; then
                env_file="$PROJECT_ROOT/.env"
            else
                log_warning ".env file not found, using .env.example"
                env_file="$PROJECT_ROOT/.env.example"
            fi
            ;;
        staging)
            env_file="$PROJECT_ROOT/.env.staging"
            ;;
        production)
            env_file="$PROJECT_ROOT/.env.production"
            ;;
    esac

    if [[ ! -f "$env_file" ]]; then
        log_error "Environment file not found: $env_file"
        exit 1
    fi

    # Copy environment file to .env for Docker Compose
    cp "$env_file" "$PROJECT_ROOT/.env"
    log_info "Using environment file: $env_file"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Get Docker Compose command
get_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

# Deploy application
deploy_app() {
    log_info "Deploying B2B AI E-commerce Content Generator..."
    
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    
    # Build and start services
    if [[ "$PROFILE" == "basic" ]]; then
        $compose_cmd up -d --build app
    else
        $compose_cmd --profile "$PROFILE" up -d --build
    fi

    # Wait for application to be ready
    log_info "Waiting for application to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
            log_success "Application is ready!"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Application failed to start within expected time"
            exit 1
        fi
        
        log_info "Attempt $attempt/$max_attempts - waiting for application..."
        sleep 10
        ((attempt++))
    done

    log_success "Deployment completed successfully!"
    show_status
}

# Stop application
stop_app() {
    log_info "Stopping application..."
    
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    
    if [[ "$PROFILE" == "basic" ]]; then
        $compose_cmd stop app
    else
        $compose_cmd --profile "$PROFILE" stop
    fi
    
    log_success "Application stopped"
}

# Restart application
restart_app() {
    log_info "Restarting application..."
    stop_app
    deploy_app
}

# Show logs
show_logs() {
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    
    log_info "Showing application logs..."
    
    if [[ "$PROFILE" == "basic" ]]; then
        $compose_cmd logs -f app
    else
        $compose_cmd --profile "$PROFILE" logs -f
    fi
}

# Show status
show_status() {
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    
    log_info "Application Status:"
    echo "===================="
    
    if [[ "$PROFILE" == "basic" ]]; then
        $compose_cmd ps app
    else
        $compose_cmd --profile "$PROFILE" ps
    fi
    
    echo ""
    log_info "Application URLs:"
    echo "Main Application: http://localhost:8501"
    
    if [[ "$PROFILE" == "production" || "$PROFILE" == "monitoring" ]]; then
        echo "Nginx Proxy: http://localhost:80"
    fi
    
    if [[ "$PROFILE" == "monitoring" ]]; then
        echo "Prometheus: http://localhost:9090"
        echo "Grafana: http://localhost:3000"
    fi
}

# Cleanup resources
cleanup_resources() {
    log_info "Cleaning up unused Docker resources..."
    
    if [[ "$FORCE" == "true" ]]; then
        docker system prune -f
        docker volume prune -f
    else
        docker system prune
        docker volume prune
    fi
    
    log_success "Cleanup completed"
}

# Backup data
backup_data() {
    log_info "Creating backup..."
    
    local backup_dir="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup volumes
    docker run --rm -v b2b-ai-content-generator_app_logs:/data -v "$backup_dir":/backup alpine tar czf /backup/logs.tar.gz -C /data .
    docker run --rm -v b2b-ai-content-generator_app_uploads:/data -v "$backup_dir":/backup alpine tar czf /backup/uploads.tar.gz -C /data .
    docker run --rm -v b2b-ai-content-generator_app_downloads:/data -v "$backup_dir":/backup alpine tar czf /backup/downloads.tar.gz -C /data .
    
    log_success "Backup created: $backup_dir"
}

# Restore data
restore_data() {
    if [[ $# -eq 0 ]]; then
        log_error "Please specify backup directory"
        exit 1
    fi
    
    local backup_dir="$1"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory not found: $backup_dir"
        exit 1
    fi
    
    log_info "Restoring from backup: $backup_dir"
    
    # Restore volumes
    if [[ -f "$backup_dir/logs.tar.gz" ]]; then
        docker run --rm -v b2b-ai-content-generator_app_logs:/data -v "$backup_dir":/backup alpine tar xzf /backup/logs.tar.gz -C /data
    fi
    
    if [[ -f "$backup_dir/uploads.tar.gz" ]]; then
        docker run --rm -v b2b-ai-content-generator_app_uploads:/data -v "$backup_dir":/backup alpine tar xzf /backup/uploads.tar.gz -C /data
    fi
    
    if [[ -f "$backup_dir/downloads.tar.gz" ]]; then
        docker run --rm -v b2b-ai-content-generator_app_downloads:/data -v "$backup_dir":/backup alpine tar xzf /backup/downloads.tar.gz -C /data
    fi
    
    log_success "Restore completed"
}

# Main function
main() {
    parse_args "$@"
    validate_environment
    check_prerequisites
    setup_env_file
    
    cd "$PROJECT_ROOT"
    
    case "$COMMAND" in
        deploy)
            deploy_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            restart_app
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        cleanup)
            cleanup_resources
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$@"
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"