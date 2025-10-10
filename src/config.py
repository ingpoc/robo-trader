"""
Configuration management for Robo Trader
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class RiskConfig(BaseModel):
    """Risk management configuration."""
    max_position_size_percent: float = Field(default=5.0, description="Max position size as % of portfolio")
    max_portfolio_risk_percent: float = Field(default=10.0, description="Max portfolio risk %")
    max_single_symbol_exposure_percent: float = Field(default=15.0, description="Max exposure to single symbol %")
    stop_loss_percent: float = Field(default=2.0, description="Default stop loss %")
    take_profit_percent: float = Field(default=5.0, description="Default take profit %")
    max_daily_trades: int = Field(default=10, description="Maximum trades per day")
    max_daily_loss_percent: float = Field(default=3.0, description="Max daily loss %")


class TechnicalConfig(BaseModel):
    """Technical analysis configuration."""
    indicators: List[str] = Field(default=["rsi", "macd", "bollinger", "ema"], description="Enabled indicators")
    timeframes: List[str] = Field(default=["5m", "15m", "1h"], description="Analysis timeframes")
    rsi_period: int = Field(default=14, description="RSI period")
    macd_fast: int = Field(default=12, description="MACD fast period")
    macd_slow: int = Field(default=26, description="MACD slow period")
    macd_signal: int = Field(default=9, description="MACD signal period")
    bollinger_period: int = Field(default=20, description="Bollinger Bands period")
    bollinger_std: float = Field(default=2.0, description="Bollinger Bands standard deviation")
    ema_periods: List[int] = Field(default=[9, 21, 50], description="EMA periods")


class ScreeningConfig(BaseModel):
    """Fundamental screening configuration."""
    min_market_cap: int = Field(default=1000000000, description="Minimum market cap (INR)")
    max_pe_ratio: float = Field(default=25.0, description="Maximum P/E ratio")
    min_roe_percent: float = Field(default=10.0, description="Minimum ROE %")
    max_debt_equity: float = Field(default=0.5, description="Maximum debt-to-equity ratio")
    sectors_allowed: List[str] = Field(default=[], description="Allowed sectors (empty = all)")
    symbols_blacklist: List[str] = Field(default=[], description="Blacklisted symbols")


class ExecutionConfig(BaseModel):
    """Trade execution configuration."""
    default_order_type: str = Field(default="MARKET", description="Default order type")
    default_product: str = Field(default="CNC", description="Default product type")
    default_variety: str = Field(default="REGULAR", description="Default variety")
    slippage_percent: float = Field(default=0.5, description="Allowed slippage %")
    time_in_force: str = Field(default="DAY", description="Time in force")
    auto_approve_paper: bool = Field(default=True, description="Auto-approve in paper mode")
    require_manual_approval_live: bool = Field(default=True, description="Require manual approval in live mode")


class IntegrationConfig(BaseModel):
    """External integration configuration."""
    zerodha_api_key: Optional[str] = Field(default=None, description="Zerodha API key")
    zerodha_api_secret: Optional[str] = Field(default=None, description="Zerodha API secret")
    zerodha_access_token: Optional[str] = Field(default=None, description="Zerodha access token")
    zerodha_request_token: Optional[str] = Field(default=None, description="Zerodha request token")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    perplexity_api_keys: List[str] = Field(default_factory=list, description="Perplexity API keys (with automatic failover)")


class AgentFeatureConfig(BaseModel):
    """Configuration for a specific agent feature."""
    enabled: bool = Field(default=True, description="Enable/disable this feature")
    use_claude: bool = Field(default=True, description="Use Claude AI for this feature")
    frequency_seconds: int = Field(default=60, description="Frequency in seconds (for scheduled tasks)")
    priority: str = Field(default="medium", description="Priority: critical, high, medium, low")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "use_claude": self.use_claude,
            "frequency_seconds": self.frequency_seconds,
            "priority": self.priority
        }


class AgentsConfig(BaseModel):
    """Agent-specific configurations with Claude toggle and frequency control."""

    chat_interface: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=0,
            priority="high"
        ),
        description="Chat interface with AI assistant"
    )

    portfolio_scan: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=3600,
            priority="medium"
        ),
        description="Portfolio analysis and scanning"
    )

    market_screening: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=14400,
            priority="medium"
        ),
        description="Market screening for opportunities"
    )

    market_monitoring: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=30,
            priority="medium"
        ),
        description="Real-time market monitoring"
    )

    stop_loss_monitor: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=False,
            frequency_seconds=15,
            priority="high"
        ),
        description="Stop loss monitoring and alerts"
    )

    earnings_check: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=900,
            priority="medium"
        ),
        description="Earnings announcement tracking"
    )

    news_monitoring: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=300,
            priority="medium"
        ),
        description="News monitoring and analysis"
    )

    ai_daily_planning: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=86400,
            priority="high"
        ),
        description="Daily AI planning (runs at 8:30 AM IST)"
    )

    health_check: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=False,
            frequency_seconds=300,
            priority="low"
        ),
        description="System health checks"
    )

    trade_execution: AgentFeatureConfig = Field(
        default_factory=lambda: AgentFeatureConfig(
            enabled=True,
            use_claude=True,
            frequency_seconds=0,
            priority="high"
        ),
        description="Trade execution with AI risk assessment"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_interface": self.chat_interface.to_dict(),
            "portfolio_scan": self.portfolio_scan.to_dict(),
            "market_screening": self.market_screening.to_dict(),
            "market_monitoring": self.market_monitoring.to_dict(),
            "stop_loss_monitor": self.stop_loss_monitor.to_dict(),
            "earnings_check": self.earnings_check.to_dict(),
            "news_monitoring": self.news_monitoring.to_dict(),
            "ai_daily_planning": self.ai_daily_planning.to_dict(),
            "health_check": self.health_check.to_dict(),
            "trade_execution": self.trade_execution.to_dict()
        }


class SchedulingConfig(BaseModel):
    """Scheduling configuration."""
    portfolio_scan_interval_minutes: int = Field(default=60, description="Portfolio scan interval")
    market_screening_interval_minutes: int = Field(default=240, description="Market screening interval")
    market_hours_start: str = Field(default="09:15", description="Market open time (IST)")
    market_hours_end: str = Field(default="15:30", description="Market close time (IST)")


class Config(BaseModel):
    """Main configuration class."""
    environment: str = Field(default="dry-run", description="Environment: dry-run, paper, live")
    project_dir: Path = Field(default=Path.cwd(), description="Project directory")
    state_dir: Path = Field(default=Path.cwd() / "state", description="State storage directory")
    logs_dir: Path = Field(default=Path.cwd() / "logs", description="Logs directory")
    max_turns: int = Field(default=50, description="Maximum conversation turns")

    risk: RiskConfig = Field(default_factory=RiskConfig)
    technical: TechnicalConfig = Field(default_factory=TechnicalConfig)
    screening: ScreeningConfig = Field(default_factory=ScreeningConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)

    @property
    def permission_mode(self) -> str:
        """Get permission mode based on environment."""
        if self.environment == "dry-run":
            return "plan"
        elif self.environment == "paper":
            return "acceptEdits"
        elif self.environment == "live":
            return "default"
        else:
            return "default"

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from JSON file."""
        if not config_path.exists():
            config = cls()
            config.save(config_path)
            return config

        with open(config_path, 'r') as f:
            data = json.load(f)

        if 'project_dir' in data:
            data['project_dir'] = Path(data['project_dir'])
        if 'state_dir' in data:
            data['state_dir'] = Path(data['state_dir'])
        if 'logs_dir' in data:
            data['logs_dir'] = Path(data['logs_dir'])

        return cls(**data)

    def save(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        data = self.model_dump()

        data['project_dir'] = str(data['project_dir'])
        data['state_dir'] = str(data['state_dir'])
        data['logs_dir'] = str(data['logs_dir'])

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_env_vars(self) -> None:
        """Load sensitive config from environment variables."""
        self.integration.zerodha_api_key = os.getenv('ZERODHA_API_KEY', self.integration.zerodha_api_key)
        self.integration.zerodha_api_secret = os.getenv('ZERODHA_API_SECRET', self.integration.zerodha_api_secret)
        self.integration.zerodha_access_token = os.getenv('ZERODHA_ACCESS_TOKEN', self.integration.zerodha_access_token)
        self.integration.zerodha_request_token = os.getenv('ZERODHA_REQUEST_TOKEN', self.integration.zerodha_request_token)
        self.integration.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', self.integration.anthropic_api_key)

        perplexity_keys = []
        for i in range(1, 10):
            key = os.getenv(f'PERPLEXITY_API_KEY_{i}')
            if key:
                perplexity_keys.append(key)
        if perplexity_keys:
            self.integration.perplexity_api_keys = perplexity_keys

    def validate_environment(self) -> None:
        """Validate that required API keys are set for the current environment."""
        from loguru import logger

        if self.environment == 'live':
            if not self.integration.zerodha_api_key or not self.integration.zerodha_api_secret:
                raise ValueError(
                    "ZERODHA_API_KEY and ZERODHA_API_SECRET required for live trading. "
                    "Set them in .env file or environment variables."
                )
            logger.info("✓ Live trading credentials configured")

        if not self.integration.anthropic_api_key:
            logger.warning(
                "⚠ ANTHROPIC_API_KEY not set - Claude Agent SDK will use built-in authentication. "
                "For API key authentication, set ANTHROPIC_API_KEY in .env file."
            )
        else:
            logger.info("✓ Anthropic API key configured")


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration with environment variable overrides."""
    if config_path is None:
        config_path = Path.cwd() / "config" / "config.json"

    config = Config.from_file(config_path)
    config.load_env_vars()
    config.validate_environment()

    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.logs_dir.mkdir(parents=True, exist_ok=True)

    return config
