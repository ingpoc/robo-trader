# Complete Implementation Plan: Claude's Real-Time Prompt Optimization System

## **Overview**

This document outlines the comprehensive implementation of Claude's real-time prompt optimization system, where Claude self-optimizes Perplexity prompts by iteratively refining them until satisfied with data quality.

## **Phase 1: Core Prompt Optimization Infrastructure**

### **1.1 Database Schema & Migration**

```sql
-- File: migrations/add_prompt_optimization.sql

-- Store optimized prompts with version control
CREATE TABLE optimized_prompts (
    id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,  -- 'earnings', 'news', 'fundamentals', 'metrics'
    original_prompt TEXT NOT NULL,
    current_prompt TEXT NOT NULL,  -- Claude's latest optimized version
    quality_score REAL NOT NULL,  -- Claude's satisfaction rating (1-10)
    optimization_version INTEGER DEFAULT 1,  -- How many times optimized
    total_optimizations INTEGER DEFAULT 0,  -- Count of all optimizations
    claude_feedback TEXT,  -- Why current version is better
    session_id TEXT,  -- Session that created this optimization
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_optimized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    avg_quality_rating REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,  % of times data met quality threshold
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Track each optimization attempt for full transparency
CREATE TABLE prompt_optimization_attempts (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,  -- 1, 2, 3 within a session
    prompt_text TEXT NOT NULL,
    data_received TEXT NOT NULL,  -- Perplexity response
    quality_score REAL NOT NULL,
    claude_analysis TEXT,  -- Detailed analysis of what was good/bad
    missing_elements TEXT,  -- JSON array of what Claude needed
    redundant_elements TEXT,  -- JSON array of what was unnecessary
    optimization_time_ms INTEGER,  -- How long the optimization took
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES optimized_prompts(id)
);

-- Link prompts to trading sessions for analysis
CREATE TABLE session_prompt_usage (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    quality_achieved REAL NOT NULL,
    symbols_analyzed TEXT,  -- JSON array of symbols
    trading_decisions_influenced INTEGER DEFAULT 0,  -- How many trades used this data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES optimized_prompts(id)
);

-- Indexes for performance
CREATE INDEX idx_optimized_prompts_type_active ON optimized_prompts(data_type, is_active);
CREATE INDEX idx_optimization_attempts_prompt ON prompt_optimization_attempts(prompt_id);
CREATE INDEX idx_session_prompt_usage_session ON session_prompt_usage(session_id);
CREATE INDEX idx_prompts_last_optimized ON optimized_prompts(last_optimized_at);
```

### **1.2 Core Services Implementation**

**File**: `src/services/prompt_optimization_service.py`

```python
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

from ..core.event_bus import EventHandler, Event, EventType, EventBus
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
from ..core.di import DependencyContainer
from ..background_scheduler.clients.perplexity_client import PerplexityClient
from ..models.claude_agent import ClaudeSessionResult
from ..auth.claude_auth import get_claude_status_cached
from loguru import logger

class PromptOptimizationService(EventHandler):
    """
    Claude's real-time prompt optimization service.

    Claude self-optimizes Perplexity prompts by:
    1. Analyzing data quality immediately after receiving it
    2. Identifying missing/unnecessary elements
    3. Rewriting prompts to address gaps
    4. Testing improved prompts in real-time
    5. Saving optimized versions for future use
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: EventBus,
        container: DependencyContainer,
        perplexity_client: PerplexityClient
    ):
        self.config = config
        self.event_bus = event_bus
        self.container = container
        self.perplexity_client = perplexity_client
        self._initialized = False

        # Claude's optimization settings
        self.max_optimization_attempts = config.get("max_optimization_attempts", 3)
        self.quality_threshold = config.get("quality_threshold", 8.0)
        self.enable_real_time_optimization = config.get("enable_real_time_optimization", True)

    async def get_optimized_data(
        self,
        data_type: str,
        symbols: List[str],
        session_id: str,
        force_optimization: bool = False
    ) -> Tuple[str, float, str, Dict[str, Any]]:
        """
        Get data using Claude's optimized prompt system.

        Returns:
            Tuple of (final_data, quality_score, final_prompt, optimization_metadata)
        """

        # 1. Get current active prompt for this data type
        current_prompt = await self._get_active_prompt(data_type)
        if not current_prompt:
            # Fallback to original if no optimized version exists
            current_prompt = await self._get_original_prompt(data_type)

        optimization_metadata = {
            "session_id": session_id,
            "data_type": data_type,
            "symbols": symbols,
            "attempts": [],
            "original_prompt": current_prompt,
            "optimization_triggered": False
        }

        # 2. Optimization loop - Claude iteratively improves prompt
        for attempt in range(self.max_optimization_attempts):
            attempt_start = datetime.utcnow()

            # Get data with current prompt
            data = await self._fetch_data_with_prompt(current_prompt, data_type, symbols)
            if not data:
                logger.warning(f"Failed to fetch {data_type} data on attempt {attempt + 1}")
                continue

            # Claude analyzes the data quality
            quality_analysis = await self._analyze_data_quality_with_claude(
                data_type=data_type,
                data=data,
                prompt_used=current_prompt,
                attempt_number=attempt + 1
            )

            quality_score = quality_analysis["quality_score"]
            missing_elements = quality_analysis["missing_elements"]
            redundant_elements = quality_analysis["redundant_elements"]
            feedback = quality_analysis["feedback"]

            # Record this attempt
            attempt_metadata = {
                "attempt_number": attempt + 1,
                "prompt_used": current_prompt,
                "quality_score": quality_score,
                "missing_elements": missing_elements,
                "redundant_elements": redundant_elements,
                "feedback": feedback,
                "data_preview": data[:500] + "..." if len(data) > 500 else data
            }
            optimization_metadata["attempts"].append(attempt_metadata)

            # Check if Claude is satisfied with data quality
            if quality_score >= self.quality_threshold:
                logger.info(f"Claude satisfied with {data_type} data quality: {quality_score}/10 on attempt {attempt + 1}")

                # Save successful optimization if we improved the prompt
                if attempt > 0 or force_optimization:
                    await self._save_optimized_prompt(
                        data_type=data_type,
                        original_prompt=optimization_metadata["original_prompt"],
                        optimized_prompt=current_prompt,
                        quality_score=quality_score,
                        session_id=session_id,
                        optimization_attempts=optimization_metadata["attempts"]
                    )

                # Update usage stats
                await self._update_prompt_usage_stats(data_type, current_prompt, quality_score, session_id)

                optimization_metadata["final_quality"] = quality_score
                optimization_metadata["optimization_successful"] = attempt > 0
                return data, quality_score, current_prompt, optimization_metadata

            # If not satisfied and we have more attempts, improve the prompt
            if attempt < self.max_optimization_attempts - 1:
                logger.info(f"Claude improving {data_type} prompt - quality {quality_score}/10 on attempt {attempt + 1}")

                improvement_result = await self._improve_prompt_with_claude(
                    data_type=data_type,
                    current_prompt=current_prompt,
                    missing_elements=missing_elements,
                    redundant_elements=redundant_elements,
                    quality_feedback=feedback,
                    attempt_number=attempt + 1
                )

                current_prompt = improvement_result["improved_prompt"]
                optimization_metadata["optimization_triggered"] = True

        # Max attempts reached - use best we got
        logger.warning(f"Max optimization attempts reached for {data_type}, using best quality: {quality_score}/10")

        # Save the optimization attempt even if not fully successful
        await self._save_optimized_prompt(
            data_type=data_type,
            original_prompt=optimization_metadata["original_prompt"],
            optimized_prompt=current_prompt,
            quality_score=quality_score,
            session_id=session_id,
            optimization_attempts=optimization_metadata["attempts"]
        )

        optimization_metadata["final_quality"] = quality_score
        optimization_metadata["optimization_successful"] = False
        optimization_metadata["max_attempts_reached"] = True

        return data, quality_score, current_prompt, optimization_metadata

    # ... (rest of the service implementation continues as shown in the conversation)
```

### **1.3 Claude MCP Tools for Prompt Optimization**

**File**: `src/services/claude_agent/prompt_optimization_tools.py`

```python
from typing import Dict, Any, List
import json
from loguru import logger

class PromptOptimizationTools:
    """MCP tools for Claude to optimize prompts in real-time."""

    def __init__(self, prompt_service):
        self.prompt_service = prompt_service

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of available prompt optimization tools."""
        return [
            {
                "name": "analyze_data_quality",
                "description": "Analyze the quality of data received from Perplexity for trading decisions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data received"
                        },
                        "data": {
                            "type": "string",
                            "description": "The actual data received from Perplexity"
                        },
                        "prompt_used": {
                            "type": "string",
                            "description": "The prompt that was used to get this data"
                        }
                    },
                    "required": ["data_type", "data", "prompt_used"]
                }
            },
            {
                "name": "improve_prompt",
                "description": "Improve a Perplexity prompt based on data quality analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data being fetched"
                        },
                        "current_prompt": {
                            "type": "string",
                            "description": "Current prompt that needs improvement"
                        },
                        "missing_elements": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Elements that are missing from the data"
                        },
                        "redundant_elements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Elements that are redundant or unnecessary"
                        },
                        "quality_feedback": {
                            "type": "string",
                            "description": "Claude's feedback on current data quality"
                        }
                    },
                    "required": ["data_type", "current_prompt", "missing_elements", "redundant_elements", "quality_feedback"]
                }
            },
            {
                "name": "save_optimized_prompt",
                "description": "Save an optimized prompt for future use",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["earnings", "news", "fundamentals", "metrics"],
                            "description": "Type of data this prompt fetches"
                        },
                        "original_prompt": {
                            "type": "string",
                            "description": "Original prompt before optimization"
                        },
                        "optimized_prompt": {
                            "type": "string",
                            "description": "Claude's optimized version of the prompt"
                        },
                        "quality_score": {
                            "type": "number",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Claude's satisfaction with data quality (1-10)"
                        },
                        "optimization_notes": {
                            "type": "string",
                            "description": "Claude's notes on why this version is better"
                        }
                    },
                    "required": ["data_type", "original_prompt", "optimized_prompt", "quality_score"]
                }
            }
        ]

    # ... (tool implementations continue as shown in conversation)
```

## **Phase 2: Enhanced Claude Agent Integration**

### **2.1 Updated Claude Agent Service**

**File**: `src/services/claude_agent_service.py` (Enhanced methods)

```python
# Add to existing ClaudeAgentService class

async def _build_morning_context_with_optimized_data(self, account_type: str) -> Dict[str, Any]:
    """Build morning context using Claude's optimized data acquisition."""

    # Get symbols to analyze (from open positions + watchlist)
    symbols = await self._get_symbols_for_analysis(account_type)

    # Initialize prompt optimization service
    prompt_service = await self.container.get("prompt_optimization_service")

    # Claude gets optimized data for each data type
    optimized_data = {}
    data_quality_summary = {}

    for data_type in ["earnings", "news", "fundamentals"]:
        try:
            data, quality_score, final_prompt, optimization_metadata = await prompt_service.get_optimized_data(
                data_type=data_type,
                symbols=symbols,
                session_id=self.current_session_id,
                force_optimization=False  # Let Claude decide if optimization is needed
            )

            optimized_data[data_type] = data
            data_quality_summary[data_type] = {
                "quality_score": quality_score,
                "optimization_attempts": len(optimization_metadata["attempts"]),
                "prompt_optimized": optimization_metadata["optimization_triggered"],
                "final_prompt": final_prompt
            }

            # Log data quality for transparency
            await self._log_data_quality(
                session_id=self.current_session_id,
                data_type=data_type,
                quality_score=quality_score,
                optimization_metadata=optimization_metadata
            )

        except Exception as e:
            logger.error(f"Failed to get optimized {data_type} data: {e}")
            # Fallback to original data acquisition
            optimized_data[data_type] = await self._get_fallback_data(data_type, symbols)
            data_quality_summary[data_type] = {"quality_score": 0.0, "error": str(e)}

    # Build context with optimized data
    context = await self._build_context_from_optimized_data(
        account_type=account_type,
        optimized_data=optimized_data,
        data_quality_summary=data_quality_summary
    )

    # Add data quality awareness to context
    context["data_quality"] = data_quality_summary
    context["data_acquisition_method"] = "claude_optimized_prompts"

    return context
```

## **Phase 3: Enhanced AI Transparency Frontend**

### **3.1 New Data Pipeline Tab**

**File**: `ui/src/features/ai-transparency/components/DataPipelineAnalysis.tsx`

```typescript
import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Eye, TrendingUp, AlertTriangle, CheckCircle, Clock, Zap } from 'lucide-react'

interface DataPipelineAnalysisProps {
  isLoading?: boolean
}

export const DataPipelineAnalysis: React.FC<DataPipelineAnalysisProps> = ({ isLoading = false }) => {
  const [pipelineData, setPipelineData] = useState(null)
  const [selectedDataType, setSelectedDataType] = useState('earnings')
  const [optimizationHistory, setOptimizationHistory] = useState([])

  const dataTypes = [
    { id: 'earnings', name: 'Earnings', icon: '📊', color: 'blue' },
    { id: 'news', name: 'News', icon: '📰', color: 'green' },
    { id: 'fundamentals', name: 'Fundamentals', icon: '💹', color: 'purple' },
    { id: 'metrics', name: 'Technical Metrics', icon: '📈', color: 'orange' }
  ]

  // ... (component implementation continues as shown in conversation)
}
```

### **3.2 Enhanced Strategy Rationale Tab**

**File**: `ui/src/features/ai-transparency/components/StrategyRationale.tsx`

```typescript
import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Brain, Target, TrendingUp, AlertTriangle, Database, Link } from 'lucide-react'

interface StrategyRationaleProps {
  accountId?: string
}

export const StrategyRationale: React.FC<StrategyRationaleProps> = ({ accountId }) => {
  const [currentStrategy, setCurrentStrategy] = useState(null)
  const [dataSources, setDataSources] = useState([])
  const [reasoningChain, setReasoningChain] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  // ... (component implementation continues as shown in conversation)
}
```

### **3.3 Enhanced Paper Trading Page Integration**

**File**: `ui/src/features/paper-trading/components/CurrentStrategyPanel.tsx`

```typescript
import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Brain, Target, Database, TrendingUp, AlertTriangle, Eye, RefreshCw } from 'lucide-react'

interface CurrentStrategyPanelProps {
  accountId: string
  accountType: string
}

export const CurrentStrategyPanel: React.FC<CurrentStrategyPanelProps> = ({
  accountId,
  accountType
}) => {
  const [currentStrategy, setCurrentStrategy] = useState(null)
  const [dataQuality, setDataQuality] = useState({})
  const [liveAnalysis, setLiveAnalysis] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  // ... (component implementation continues as shown in conversation)
}
```

## **Phase 4: Integration & Deployment**

### **4.1 Dependency Injection Registration**

**File**: `src/core/di.py` (Add to existing container)

```python
async def register_prompt_optimization_services(self):
    """Register prompt optimization services."""

    # Register prompt optimization service
    self.register_singleton(
        PromptOptimizationService,
        config=self.config.get("prompt_optimization", {}),
        event_bus=self.get(EventBus),
        container=self,
        perplexity_client=self.get(PerplexityClient)
    )

    # Register prompt optimization tools for Claude
    prompt_service = self.get(PromptOptimizationService)
    optimization_tools = PromptOptimizationTools(prompt_service)

    # Register tools with Claude Agent MCP server
    claude_mcp_server = self.get("claude_mcp_server")
    await claude_mcp_server.register_tools(optimization_tools.get_tools())
```

### **4.2 Configuration Updates**

**File**: `config/config.json` (Add section)

```json
{
  "prompt_optimization": {
    "max_optimization_attempts": 3,
    "quality_threshold": 8.0,
    "enable_real_time_optimization": true,
    "min_data_quality_for_trading": 7.0,
    "optimization_timeout_seconds": 120,
    "enable_auto_prompt_evolution": true,
    "track_prompt_performance": true
  },
  "claude_agent": {
    "daily_token_budget": 15000,
    "enable_prompt_optimization": true,
    "log_data_quality_analysis": true,
    "transparency_level": "full"
  }
}
```

### **4.3 Event Types Extension**

**File**: `src/core/event_bus.py` (Add to EventType enum)

```python
class EventType(Enum):
    # ... existing events ...

    # Prompt optimization events
    PROMPT_OPTIMIZED = "prompt_optimized"
    PROMPT_QUALITY_ANALYSIS = "prompt_quality_analysis"
    CLAUDE_SESSION_STARTED = "claude_session_started"
    CLAUDE_DATA_QUALITY_ANALYSIS = "claude_data_quality_analysis"
    STRATEGY_FORMED = "strategy_formed"
    DATA_ACQUISITION_COMPLETED = "data_acquisition_completed"
```

### **4.4 API Routes**

**File**: `src/web/routes/prompt_optimization.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..dependencies import get_database, get_current_user
from ..services.prompt_optimization_service import PromptOptimizationService

router = APIRouter(prefix="/api/prompts", tags=["prompt-optimization"])

@router.get("/active/{data_type}")
async def get_active_prompt(
    data_type: str,
    db = Depends(get_database),
    current_user = Depends(get_current_user)
):
    """Get current active optimized prompt for data type."""
    # ... (implementation continues as shown in conversation)
```

## **Implementation Benefits**

This comprehensive implementation provides:

1. **Full Autonomy**: Claude self-optimizes prompts without human intervention
2. **Complete Transparency**: Every optimization step is logged and viewable
3. **Real-time Improvement**: Prompts get better during live trading sessions
4. **Quality Awareness**: Claude knows exactly what data quality it's working with
5. **Strategic Context**: Clear link between data quality and trading decisions
6. **Continuous Learning**: System improves over time based on Claude's feedback
7. **Risk Mitigation**: Claude can identify when data quality is insufficient for trading
8. **Performance Tracking**: Full metrics on prompt effectiveness over time

## **Development Timeline**

- **Phase 1** (Week 1-2): Core infrastructure, database schema, and services
- **Phase 2** (Week 2-3): Claude Agent integration and MCP tools
- **Phase 3** (Week 3-4): Frontend components and AI transparency features
- **Phase 4** (Week 4): Integration, testing, and deployment

## **Next Steps**

1. Review and approve this implementation plan
2. Create database migration scripts
3. Implement core services starting with PromptOptimizationService
4. Add MCP tools to Claude Agent server
5. Build frontend components incrementally
6. Test with real trading sessions
7. Deploy to production with monitoring

---

*Document created: 2025-10-24*
*Author: Claude Code Assistant*
*Status: Planning Phase*