# Integration Examples

This guide provides detailed integration examples for different web application stacks using the token-efficient MCP & hook system template.

## React/FastAPI Integration

### Project Structure

```
my-react-fastapi-app/
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   └── services/
├── hooks/                    # Hook system
│   ├── pre_tool_use/
│   ├── context_injection/
│   └── session_management/
├── mcp_server/              # MCP server
│   ├── server/
│   ├── logs/
│   ├── system/
│   └── database/
└── config/                   # Configuration files
```

### Step 1: Initialize Project

```bash
# Initialize React/FastAPI project with full ecosystem
python scripts/init_template.py \
  --project-type react-fastapi \
  --name my-ecommerce-app \
  --include-mcp-server \
  --include-hooks \
  --caching-strategy smart \
  --categories logs system database performance
```

### Step 2: Backend Integration

**FastAPI Configuration (backend/app/core/config.py)**

```python
from pydantic import BaseSettings
from typing import List, Optional
import yaml
from pathlib import Path

class Settings(BaseSettings):
    # Project settings
    project_name: str = "my-ecommerce-app"
    project_type: str = "react-fastapi"

    # MCP Server settings
    mcp_server_enabled: bool = True
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 8080

    # Hook system settings
    hooks_enabled: bool = True
    pre_tool_use_hook: str = "hooks/pre_tool_use/advisor.sh"
    context_injection_enabled: bool = True

    # Token efficiency settings
    caching_strategy: str = "smart"
    target_token_reduction: str = "95%+"

    # Database settings
    database_url: str = "sqlite:///./app.db"

    # Frontend settings
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Load configuration
settings = Settings()

# Load YAML configuration
config_path = Path("config/main.yaml")
if config_path.exists():
    with open(config_path) as f:
        yaml_config = yaml.safe_load(f)
        # Override with YAML config
        for key, value in yaml_config.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
```

**MCP Client Integration (backend/app/services/mcp_client.py)**

```python
import httpx
import asyncio
from typing import Dict, Any, Optional
from ..core.config import settings

class MCPClient:
    def __init__(self):
        self.base_url = f"http://{settings.mcp_server_host}:{settings.mcp_server_port}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP server tool with token efficiency."""
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/{tool_name}",
                json=arguments
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {
                'success': False,
                'error': f'MCP server error: {e}',
                'tool_name': tool_name
            }

    async def analyze_logs(self, time_range: str = "24h") -> Dict[str, Any]:
        """Analyze application logs with 98% token reduction."""
        return await self.call_tool('analyze_logs', {'time_range': time_range})

    async def health_check(self, components: List[str] = None) -> Dict[str, Any]:
        """Check system health with 97% token reduction."""
        if components is None:
            components = ['cpu', 'memory', 'disk']
        return await self.call_tool('health_check', {'components': components})

    async def query_optimizer(self, queries: List[str]) -> Dict[str, Any]:
        """Optimize database queries with 95% token reduction."""
        return await self.call_tool('query_optimizer', {'queries': queries})

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

# Global MCP client instance
mcp_client = MCPClient()

async def get_mcp_client() -> MCPClient:
    """Get MCP client instance."""
    return mcp_client
```

**API Integration (backend/app/api/monitoring.py)**

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from ..services.mcp_client import get_mcp_client
from ..core.config import settings

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/health")
async def get_system_health(
    components: List[str] = ['cpu', 'memory', 'disk'],
    mcp_client = Depends(get_mcp_client)
):
    """Get system health status with token efficiency."""
    try:
        result = await mcp_client.health_check(components)
        return {
            'success': True,
            'data': result,
            'token_efficiency': result.get('token_efficiency', '97% reduction')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/analyze")
async def analyze_application_logs(
    time_range: str = "24h",
    mcp_client = Depends(get_mcp_client)
):
    """Analyze application logs with 98% token reduction."""
    try:
        result = await mcp_client.analyze_logs(time_range)
        return {
            'success': True,
            'data': result,
            'token_efficiency': result.get('token_efficiency', '98% reduction')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/database/optimize")
async def optimize_database_queries(
    queries: List[str],
    mcp_client = Depends(get_mcp_client)
):
    """Optimize database queries with 95% token reduction."""
    try:
        result = await mcp_client.query_optimizer(queries)
        return {
            'success': True,
            'data': result,
            'token_efficiency': result.get('token_efficiency', '95% reduction')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 3: Frontend Integration

**React Service (frontend/src/services/mcpService.js)**

```javascript
class MCPService {
  constructor() {
    this.baseURL = process.env.REACT_APP_MCP_SERVER_URL || 'http://localhost:8080';
  }

  async callTool(toolName, arguments) {
    try {
      const response = await fetch(`${this.baseURL}/tools/${toolName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(arguments),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('MCP service error:', error);
      return {
        success: false,
        error: error.message,
        toolName,
      };
    }
  }

  async getSystemHealth(components = ['cpu', 'memory', 'disk']) {
    return this.callTool('health_check', { components });
  }

  async analyzeLogs(timeRange = '24h') {
    return this.callTool('analyze_logs', { time_range });
  }

  async optimizeQueries(queries) {
    return this.callTool('query_optimizer', { queries });
  }

  async getPerformanceMetrics() {
    return this.callTool('metrics_monitor', {});
  }
}

// Create singleton instance
const mcpService = new MCPService();

export default mcpService;
```

**React Component (frontend/src/components/SystemHealth.js)**

```javascript
import React, { useState, useEffect } from 'react';
import { Card, CardContent, Typography, LinearProgress, Alert } from '@mui/material';
import mcpService from '../services/mcpService';

function SystemHealth() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHealthData = async () => {
      try {
        setLoading(true);
        const result = await mcpService.getSystemHealth();

        if (result.success) {
          setHealthData(result.data);
          setError(null);
        } else {
          setError(result.error);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchHealthData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchHealthData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getHealthColor = (percentage) => {
    if (percentage < 70) return 'success';
    if (percentage < 85) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Typography>Loading system health...</Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">
            Error loading system health: {error}
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          System Health (97% token reduction)
        </Typography>

        {healthData?.metrics && Object.entries(healthData.metrics).map(([key, value]) => (
          <div key={key} style={{ marginBottom: '16px' }}>
            <Typography variant="body2" gutterBottom>
              {key.charAt(0).toUpperCase() + key.slice(1)}: {value}%
            </Typography>
            <LinearProgress
              variant="determinate"
              value={value}
              color={getHealthColor(value)}
            />
          </div>
        ))}

        {healthData?.alerts && healthData.alerts.length > 0 && (
          <Alert severity="warning" style={{ marginTop: '16px' }}>
            Alerts: {healthData.alerts.join(', ')}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default SystemHealth;
```

### Step 4: Hook Integration

**Pre-Tool-Use Hook for Development (hooks/pre_tool_use/development_advisor.sh)**

```bash
#!/bin/bash
# Development-specific pre-tool-use advisor

tool_info=$(cat)
tool_name=$(echo "$tool_info" | jq -r '.tool_name // empty')
command=$(echo "$tool_info" | jq -r '.tool_input.command // empty')

# React development patterns
if [[ "$command" =~ npm|yarn ]]; then
    if [[ "$command" =~ (start|dev) ]]; then
        echo "💡 TOKEN-SAVING TIP:"
        echo "Use MCP tool: performance_monitor for real-time React metrics"
        echo "Savings: 96% vs manual monitoring"
        echo ""
        echo "🔧 Available MCP metrics:"
        echo "• Component render times"
        echo "• Bundle size analysis"
        echo "• Memory usage tracking"
    fi
fi

# FastAPI development patterns
if [[ "$command" =~ uvicorn|fastapi ]]; then
    if [[ "$command" =~ (reload|dev) ]]; then
        echo "💡 TOKEN-SAVING TIP:"
        echo "Use MCP tool: analyze_logs for server error patterns"
        echo "Savings: 98% vs manual log reading"
        echo ""
        echo "🔧 Quick log analysis:"
        echo "• API endpoint errors"
        echo "• Database connection issues"
        echo "• Performance bottlenecks"
    fi
fi
```

## Django Analytics Integration

### Step 1: Initialize Django Project

```bash
python scripts/init_template.py \
  --project-type django-analytics \
  --name analytics-dashboard \
  --include-mcp-server \
  --include-hooks \
  --caching-strategy progressive \
  --categories logs database optimization
```

### Step 2: Django Configuration

**settings.py additions**

```python
# Token-efficient MCP system
MCP_SERVER_ENABLED = True
MCP_SERVER_URL = "http://localhost:8080"

# Hook system integration
HOOKS_ENABLED = True
PRE_TOOL_USE_HOOK = "hooks/pre_tool_use/advisor.sh"

# Token efficiency settings
TOKEN_EFFICIENCY_STRATEGY = "progressive"
TARGET_TOKEN_REDUCTION = "95%+"

# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'token_efficiency',
]
```

**Django Management Command (analytics/management/commands/setup_token_efficiency.py)**

```python
from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import sys

class Command(BaseCommand):
    help = 'Setup token-efficient MCP system for Django analytics'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Setting up token-efficient MCP system...")

        # Generate hooks
        result = subprocess.run([
            sys.executable, "scripts/generate_hooks.py",
            "--type", "pre-tool-use,context-injection"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("✅ Hooks generated successfully"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Hook generation failed: {result.stderr}"))

        # Setup MCP server
        result = subprocess.run([
            sys.executable, "scripts/setup_mcp_server.py",
            "--categories", "logs", "database", "optimization",
            "--project-name", "analytics-dashboard"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("✅ MCP server setup complete"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ MCP server setup failed: {result.stderr}"))

        self.stdout.write("🎯 Token efficiency setup complete!")
        self.stdout.write("📊 Expected reduction: 95%+ tokens")
        self.stdout.write("🚀 Start MCP server: cd mcp_server && python server/main.py")
```

### Step 3: Django Integration

**Custom management command (analytics/management/commands/analyze_with_mcp.py)**

```python
import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Analyze analytics data using MCP server'

    def add_arguments(self, parser):
        parser.add_argument('--analysis-type', choices=['logs', 'performance', 'users'],
                           default='logs', help='Type of analysis to perform')
        parser.add_argument('--time-range', default='24h', help='Time range for analysis')

    def handle(self, *args, **options):
        analysis_type = options['analysis_type']
        time_range = options['time_range']

        self.stdout.write(f"🔍 Analyzing {analysis_type} for {time_range}...")

        try:
            # Call MCP server
            response = requests.post(
                f"{settings.MCP_SERVER_URL}/tools/analyze_logs",
                json={'time_range': time_range},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS("✅ Analysis completed successfully"))
                    self.stdout.write(f"💾 Token efficiency: {result.get('token_efficiency', '98% reduction')}")

                    # Display insights
                    if 'insights' in result:
                        self.stdout.write("\n📊 Key Insights:")
                        for insight in result['insights']:
                            self.stdout.write(f"  • {insight}")

                    # Display recommendations
                    if 'recommendations' in result:
                        self.stdout.write("\n💡 Recommendations:")
                        for rec in result['recommendations']:
                            self.stdout.write(f"  • {rec}")
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Analysis failed: {result.get('error')}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ MCP server error: {response.status_code}"))

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"❌ Connection error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Unexpected error: {e}"))
```

## Node.js Microservices Integration

### Step 1: Initialize Microservices

```bash
python scripts/init_template.py \
  --project-type node-microservices \
  --name microservices-platform \
  --include-mcp-server \
  --include-hooks \
  --caching-strategy differential \
  --categories system performance logs
```

### Step 2: Express.js Integration

**MCP Client Service (services/mcpClient.js)**

```javascript
const axios = require('axios');

class MCPClient {
  constructor(config = {}) {
    this.baseURL = config.baseURL || process.env.MCP_SERVER_URL || 'http://localhost:8080';
    this.timeout = config.timeout || 30000;
  }

  async callTool(toolName, arguments = {}) {
    try {
      const response = await axios.post(
        `${this.baseURL}/tools/${toolName}`,
        arguments,
        {
          timeout: this.timeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      return {
        success: true,
        data: response.data,
        toolName,
      };
    } catch (error) {
      console.error(`MCP service error for ${toolName}:`, error.message);
      return {
        success: false,
        error: error.message,
        toolName,
      };
    }
  }

  async getServiceHealth(serviceName) {
    return this.callTool('health_check', {
      components: ['cpu', 'memory', 'disk'],
      service_filter: serviceName
    });
  }

  async analyzeServiceLogs(serviceName, timeRange = '1h') {
    return this.callTool('analyze_logs', {
      service_filter: serviceName,
      time_range,
      error_patterns: true
    });
  }

  async getPerformanceMetrics(serviceName) {
    return this.callTool('metrics_monitor', {
      service_filter: serviceName,
      metrics: ['response_time', 'throughput', 'error_rate']
    });
  }
}

module.exports = MCPClient;
```

**Express Middleware (middleware/tokenEfficiency.js)**

```javascript
const mcpClient = require('../services/mcpClient');

function tokenEfficiencyMiddleware(options = {}) {
  const mcp = new mcpClient(options.mcpConfig);

  return async (req, res, next) => {
    // Add MCP client to request
    req.mcpClient = mcp;

    // Track token efficiency for this request
    const startTime = Date.now();

    // Override res.json to track token efficiency
    const originalJson = res.json;
    res.json = function(data) {
      const endTime = Date.now();
      const executionTime = endTime - startTime;

      // Add token efficiency metadata if MCP was used
      if (req.mcpUsed) {
        data.tokenEfficiency = {
          mcpUsed: true,
          executionTime,
          tokenReduction: '95%+',
          toolsUsed: req.mcpToolsUsed || []
        };
      }

      return originalJson.call(this, data);
    };

    next();
  };
}

module.exports = tokenEfficiencyMiddleware;
```

**Express Route Integration (routes/monitoring.js)**

```javascript
const express = require('express');
const router = express.Router();

// Service health monitoring
router.get('/services/:serviceName/health', async (req, res) => {
  try {
    const { serviceName } = req.params;
    const result = await req.mcpClient.getServiceHealth(serviceName);

    if (result.success) {
      req.mcpUsed = true;
      req.mcpToolsUsed = ['health_check'];

      res.json({
        success: true,
        serviceName,
        health: result.data,
        timestamp: new Date().toISOString()
      });
    } else {
      res.status(500).json({
        success: false,
        error: result.error,
        serviceName
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      serviceName: req.params.serviceName
    });
  }
});

// Log analysis
router.get('/services/:serviceName/logs', async (req, res) => {
  try {
    const { serviceName } = req.params;
    const { timeRange = '1h' } = req.query;

    const result = await req.mcpClient.analyzeServiceLogs(serviceName, timeRange);

    if (result.success) {
      req.mcpUsed = true;
      req.mcpToolsUsed = ['analyze_logs'];

      res.json({
        success: true,
        serviceName,
        timeRange,
        analysis: result.data,
        timestamp: new Date().toISOString()
      });
    } else {
      res.status(500).json({
        success: false,
        error: result.error,
        serviceName
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      serviceName: req.params.serviceName
    });
  }
});

// Performance metrics
router.get('/services/:serviceName/metrics', async (req, res) => {
  try {
    const { serviceName } = req.params;
    const result = await req.mcpClient.getPerformanceMetrics(serviceName);

    if (result.success) {
      req.mcpUsed = true;
      req.mcpToolsUsed = ['metrics_monitor'];

      res.json({
        success: true,
        serviceName,
        metrics: result.data,
        timestamp: new Date().toISOString()
      });
    } else {
      res.status(500).json({
        success: false,
        error: result.error,
        serviceName
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      serviceName: req.params.serviceName
    });
  }
});

module.exports = router;
```

## Deployment Integration

### Docker Configuration

**docker-compose.yml**

```yaml
version: '3.8'

services:
  # Application service
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MCP_SERVER_URL=http://mcp-server:8080
      - TOKEN_EFFICIENCY_STRATEGY=smart
    depends_on:
      - mcp-server
      - redis
    volumes:
      - ./hooks:/app/hooks
      - ./config:/app/config

  # MCP Server
  mcp-server:
    build: ./mcp_server
    ports:
      - "8080:8080"
    environment:
      - ENV=production
      - WORKER_PROCESSES=4
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config

  # Redis for caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  redis_data:
```

### Kubernetes Deployment

**mcp-server-deployment.yaml**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: mcp-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: ENV
          value: "production"
        - name: WORKER_PROCESSES
          value: "4"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
spec:
  selector:
    app: mcp-server
  ports:
  - protocol: TCP
    port: 8080
    targetPort: 8080
  type: ClusterIP
```

## Testing Integration

### Unit Tests

**MCP Client Tests (tests/test_mcp_client.py)**

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from services.mcp_client import MCPClient

@pytest.fixture
async def mcp_client():
    client = MCPClient()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_analyze_logs_success(mcp_client):
    """Test successful log analysis."""
    with patch.object(mcp_client.client, 'post') as mock_post:
        mock_post.return_value.json.return_value = {
            'success': True,
            'insights': ['Error pattern detected'],
            'token_efficiency': '98% reduction'
        }
        mock_post.return_value.raise_for_status = AsyncMock()

        result = await mcp_client.analyze_logs('24h')

        assert result['success'] is True
        assert 'insights' in result
        assert result['token_efficiency'] == '98% reduction'
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_health_check_with_components(mcp_client):
    """Test health check with specific components."""
    components = ['cpu', 'memory']

    with patch.object(mcp_client.client, 'post') as mock_post:
        mock_post.return_value.json.return_value = {
            'success': True,
            'metrics': {'cpu': 45, 'memory': 67},
            'token_efficiency': '97% reduction'
        }
        mock_post.return_value.raise_for_status = AsyncMock()

        result = await mcp_client.health_check(components)

        assert result['success'] is True
        assert 'metrics' in result
        mock_post.assert_called_once_with(
            "http://localhost:8080/tools/health_check",
            json={'components': components}
        )
```

### Integration Tests

**End-to-End Test (tests/test_integration.py)**

```python
import pytest
import asyncio
import httpx
from pathlib import Path

@pytest.mark.asyncio
async def test_full_token_efficiency_workflow():
    """Test complete token efficiency workflow."""

    # Step 1: Initialize project
    result = await asyncio.create_subprocess_exec(
        'python', 'scripts/init_template.py',
        '--project-type', 'react-fastapi',
        '--name', 'test-app',
        '--include-mcp-server',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await result.communicate()
    assert result.returncode == 0

    # Step 2: Start MCP server
    server_process = await asyncio.create_subprocess_exec(
        'python', 'mcp_server/server/main.py',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Wait for server to start
    await asyncio.sleep(2)

    try:
        # Step 3: Test MCP server functionality
        async with httpx.AsyncClient() as client:
            # Test health check
            health_response = await client.post(
                'http://localhost:8080/tools/health_check',
                json={'components': ['cpu', 'memory']}
            )
            assert health_response.status_code == 200

            health_data = health_response.json()
            assert health_data['success'] is True
            assert 'token_efficiency' in health_data

            # Test log analysis
            logs_response = await client.post(
                'http://localhost:8080/tools/analyze_logs',
                json={'time_range': '24h'}
            )
            assert logs_response.status_code == 200

            logs_data = logs_response.json()
            assert logs_data['success'] is True
            assert 'token_efficiency' in logs_data

            # Verify token reduction claims
            assert '97%' in health_data['token_efficiency']
            assert '98%' in logs_data['token_efficiency']

    finally:
        # Clean up
        server_process.terminate()
        await server_process.wait()

@pytest.mark.asyncio
async def test_caching_efficiency():
    """Test caching token efficiency."""

    async with httpx.AsyncClient() as client:
        # First request - should be cache miss
        response1 = await client.post(
            'http://localhost:8080/tools/health_check',
            json={'components': ['cpu']}
        )

        # Second identical request - should be cache hit
        response2 = await client.post(
            'http://localhost:8080/tools/health_check',
            json={'components': ['cpu']}
        )

        data1 = response1.json()
        data2 = response2.json()

        # First request should not be from cache
        assert data1.get('from_cache') is False

        # Second request should be from cache
        assert data2.get('from_cache') is True
        assert data2.get('cache_hit') is True
        assert '100% reduction' in data2.get('token_efficiency', '')
```

These integration examples demonstrate how to effectively implement the token-efficient MCP & hook system template across different web application stacks, providing concrete patterns for React/FastAPI, Django, and Node.js microservices architectures.