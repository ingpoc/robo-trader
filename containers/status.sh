#!/bin/bash

# Check Status of Robo Trader Services

echo "📊 Robo Trader Services Status"
echo "================================"

# Check if Apple Container is available
if ! command -v container &> /dev/null; then
    echo "❌ Apple Container CLI not found"
    echo "💡 Install Apple Container: Check System Settings > General > Software Update"
    exit 1
fi

echo "✅ Apple Container CLI available"
echo ""

# Show network status
echo "🌐 Network Status:"
if container network ls | grep -q "robo-trader-network"; then
    echo "✅ robo-trader-network exists"
else
    echo "❌ robo-trader-network not found"
fi
echo ""

# Show container status
echo "🐳 Container Status:"
SERVICES=("redis-cache" "timescale-db" "prometheus" "grafana" "event-bus" "job-queue-service" "portfolio-service" "risk-service" "execution-service" "analytics-service" "learning-service" "safety-layer")

all_running=true
for service in "${SERVICES[@]}"; do
    container_name="robo-trader-$service"
    if container ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        # Get container status
        status=$(container ps --filter "name=${container_name}" --format "{{.Status}}")
        echo "✅ $service: RUNNING ($status)"
    else
        echo "❌ $service: NOT RUNNING"
        all_running=false
    fi
done

echo ""

# Health checks
echo "🏥 Health Checks:"
for service in "${SERVICES[@]}"; do
    case $service in
        "redis-cache")
            if redis-cli ping > /dev/null 2>&1; then
                echo "✅ $service health check passed"
            else
                echo "❌ $service health check failed"
            fi
            ;;
        "timescale-db")
            if pg_isready -h localhost -p 5432 -U robo_trader > /dev/null 2>&1; then
                echo "✅ $service health check passed"
            else
                echo "❌ $service health check failed"
            fi
            ;;
        "prometheus")
            if curl -f -s "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
                echo "✅ $service health check passed"
            else
                echo "❌ $service health check failed"
            fi
            ;;
        "grafana")
            if curl -f -s "http://localhost:3000/api/health" > /dev/null 2>&1; then
                echo "✅ $service health check passed"
            else
                echo "❌ $service health check failed"
            fi
            ;;
        "job-queue-service")
            if celery -A containers/job-queue-service/tasks inspect active > /dev/null 2>&1; then
                echo "✅ $service health check passed"
            else
                echo "❌ $service health check failed"
            fi
            ;;
        "event-bus"|"portfolio-service"|"risk-service"|"execution-service"|"analytics-service"|"learning-service"|"safety-layer")
            port=""
            case $service in
                "event-bus") port="8000" ;;
                "portfolio-service") port="8001" ;;
                "risk-service") port="8002" ;;
                "execution-service") port="8003" ;;
                "analytics-service") port="8004" ;;
                "learning-service") port="8005" ;;
                "safety-layer") port="8006" ;;
            esac

            if [ -n "$port" ]; then
                if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
                    echo "✅ $service health check passed"
                else
                    echo "❌ $service health check failed"
                fi
            fi
            ;;
    esac
done

echo ""

# Shared volumes
echo "💾 Shared Volumes:"
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../shared" && pwd)"
if [ -d "$SHARED_DIR/db" ]; then
    db_size=$(du -sh "$SHARED_DIR/db" 2>/dev/null | cut -f1)
    echo "✅ Database volume: $db_size"
else
    echo "❌ Database volume not found"
fi

if [ -d "$SHARED_DIR/logs" ]; then
    log_size=$(du -sh "$SHARED_DIR/logs" 2>/dev/null | cut -f1)
    echo "✅ Logs volume: $log_size"
else
    echo "❌ Logs volume not found"
fi

echo ""

# Summary
if [ "$all_running" = true ]; then
    echo "🎉 All services are running and healthy!"
else
    echo "⚠️  Some services are not running"
    echo "💡 Start services with: ./containers/start-all.sh"
fi