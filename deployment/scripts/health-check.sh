#!/bin/bash

# B2B AI E-commerce Content Generator - Health Check Script
# Comprehensive health monitoring for production deployments

set -euo pipefail

# Configuration
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://localhost:8501/_stcore/health}"
TIMEOUT="${TIMEOUT:-10}"
RETRIES="${RETRIES:-3}"
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
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

# Health check function
check_health() {
    local endpoint="$1"
    local timeout="$2"
    
    log_info "Checking health endpoint: $endpoint"
    
    # Use curl to check the health endpoint
    if command -v curl &> /dev/null; then
        response=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$timeout" "$endpoint" 2>/dev/null || echo "000")
    elif command -v wget &> /dev/null; then
        response=$(wget -q -O /dev/null -T "$timeout" --server-response "$endpoint" 2>&1 | grep "HTTP/" | tail -1 | awk '{print $2}' || echo "000")
    else
        log_error "Neither curl nor wget is available"
        return 1
    fi
    
    log_info "HTTP response code: $response"
    
    if [[ "$response" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

# Check application dependencies
check_dependencies() {
    log_info "Checking application dependencies..."
    
    local all_good=true
    
    # Check if application is responding
    if ! check_health "$HEALTH_ENDPOINT" "$TIMEOUT"; then
        log_error "Application health check failed"
        all_good=false
    fi
    
    # Check Docker containers (if running in Docker)
    if command -v docker &> /dev/null; then
        log_info "Checking Docker containers..."
        
        # Check if main app container is running
        if docker ps --filter "name=b2b-ai" --format "table {{.Names}}\t{{.Status}}" | grep -q "Up"; then
            log_info "Docker containers are running"
        else
            log_warning "No running Docker containers found with 'b2b-ai' in name"
        fi
    fi
    
    # Check Kubernetes pods (if running in Kubernetes)
    if command -v kubectl &> /dev/null; then
        log_info "Checking Kubernetes pods..."
        
        if kubectl get pods -n b2b-ai-content-generator --no-headers 2>/dev/null | grep -q "Running"; then
            log_info "Kubernetes pods are running"
        else
            log_warning "No running Kubernetes pods found in b2b-ai-content-generator namespace"
        fi
    fi
    
    if [[ "$all_good" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Performance check
check_performance() {
    log_info "Checking application performance..."
    
    local start_time
    local end_time
    local duration
    
    start_time=$(date +%s.%N)
    
    if check_health "$HEALTH_ENDPOINT" "$TIMEOUT"; then
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "unknown")
        
        log_info "Response time: ${duration}s"
        
        # Check if response time is acceptable (< 5 seconds)
        if command -v bc &> /dev/null && (( $(echo "$duration < 5.0" | bc -l) )); then
            log_success "Response time is acceptable"
            return 0
        elif [[ "$duration" == "unknown" ]]; then
            log_warning "Could not measure response time (bc not available)"
            return 0
        else
            log_warning "Response time is slow: ${duration}s"
            return 1
        fi
    else
        log_error "Performance check failed - application not responding"
        return 1
    fi
}

# Resource usage check
check_resources() {
    log_info "Checking resource usage..."
    
    # Check system resources
    if command -v free &> /dev/null; then
        local memory_usage
        memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
        log_info "Memory usage: ${memory_usage}%"
        
        if (( $(echo "$memory_usage > 90.0" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "High memory usage: ${memory_usage}%"
        fi
    fi
    
    # Check disk space
    if command -v df &> /dev/null; then
        local disk_usage
        disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
        log_info "Disk usage: ${disk_usage}%"
        
        if [[ "$disk_usage" -gt 90 ]]; then
            log_warning "High disk usage: ${disk_usage}%"
        fi
    fi
    
    # Check Docker container resources (if available)
    if command -v docker &> /dev/null && docker ps --filter "name=b2b-ai" --format "table {{.Names}}" | grep -q "b2b-ai"; then
        log_info "Docker container resource usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker ps --filter "name=b2b-ai" --format "{{.Names}}")
    fi
}

# Main health check with retries
main_health_check() {
    local attempt=1
    local max_attempts="$RETRIES"
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts"
        
        if check_health "$HEALTH_ENDPOINT" "$TIMEOUT"; then
            log_success "Health check passed"
            return 0
        else
            if [[ $attempt -eq $max_attempts ]]; then
                log_error "Health check failed after $max_attempts attempts"
                return 1
            else
                log_warning "Health check failed, retrying in 5 seconds..."
                sleep 5
            fi
        fi
        
        ((attempt++))
    done
}

# Comprehensive health report
generate_health_report() {
    echo "=================================="
    echo "B2B AI Content Generator Health Report"
    echo "Timestamp: $(date)"
    echo "=================================="
    
    local overall_status="HEALTHY"
    
    # Basic health check
    if main_health_check; then
        log_success "✓ Application is responding"
    else
        log_error "✗ Application is not responding"
        overall_status="UNHEALTHY"
    fi
    
    # Performance check
    if check_performance; then
        log_success "✓ Performance is acceptable"
    else
        log_warning "⚠ Performance issues detected"
        if [[ "$overall_status" == "HEALTHY" ]]; then
            overall_status="DEGRADED"
        fi
    fi
    
    # Dependency check
    if check_dependencies; then
        log_success "✓ Dependencies are healthy"
    else
        log_warning "⚠ Dependency issues detected"
        if [[ "$overall_status" == "HEALTHY" ]]; then
            overall_status="DEGRADED"
        fi
    fi
    
    # Resource check
    check_resources
    
    echo "=================================="
    echo "Overall Status: $overall_status"
    echo "=================================="
    
    # Exit with appropriate code
    case "$overall_status" in
        "HEALTHY")
            exit 0
            ;;
        "DEGRADED")
            exit 1
            ;;
        "UNHEALTHY")
            exit 2
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--endpoint)
            HEALTH_ENDPOINT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -r|--retries)
            RETRIES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --quick)
            # Quick check mode - just basic health
            if main_health_check; then
                echo "HEALTHY"
                exit 0
            else
                echo "UNHEALTHY"
                exit 1
            fi
            ;;
        --report)
            # Full health report
            generate_health_report
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] [--quick|--report]"
            echo ""
            echo "Options:"
            echo "  -e, --endpoint URL    Health check endpoint (default: $HEALTH_ENDPOINT)"
            echo "  -t, --timeout SEC     Request timeout in seconds (default: $TIMEOUT)"
            echo "  -r, --retries NUM     Number of retries (default: $RETRIES)"
            echo "  -v, --verbose         Verbose output"
            echo "  --quick               Quick health check only"
            echo "  --report              Generate full health report"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default action - run full health report
generate_health_report