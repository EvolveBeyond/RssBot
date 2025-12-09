"""
Centralized configuration management
"""
import os
from typing import Optional
from pydantic import Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class Config(BaseSettings):
    """Centralized configuration with environment variable support"""
    
    # Database
    database_url: str = Field(default="sqlite:///./rssbot.db", env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Telegram Bot
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_SECRET")
    telegram_webhook_mode: bool = Field(default=False, env="TELEGRAM_WEBHOOK_MODE")
    
    # Service Security
    service_token: str = Field(
        default="dev_service_token_change_in_production",
        env="SERVICE_TOKEN"
    )
    
    # Service Ports
    db_service_port: int = Field(default=8001, env="DB_SERVICE_PORT")
    bot_service_port: int = Field(default=8002, env="BOT_SERVICE_PORT")
    payment_service_port: int = Field(default=8003, env="PAYMENT_SERVICE_PORT")
    controller_service_port: int = Field(default=8004, env="CONTROLLER_SERVICE_PORT")
    ai_service_port: int = Field(default=8005, env="AI_SERVICE_PORT")
    formatting_service_port: int = Field(default=8006, env="FORMATTING_SERVICE_PORT")
    channel_mgr_service_port: int = Field(default=8007, env="CHANNEL_MGR_SERVICE_PORT")
    user_service_port: int = Field(default=8008, env="USER_SERVICE_PORT")
    miniapp_service_port: int = Field(default=8009, env="MINIAPP_SERVICE_PORT")
    admin_service_port: int = Field(default=8010, env="ADMIN_SERVICE_PORT")
    
    # Service Communication
    local_router_mode: bool = Field(default=False, env="LOCAL_ROUTER_MODE")
    service_discovery_interval: int = Field(default=45, env="SERVICE_DISCOVERY_INTERVAL")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Payment
    stripe_secret_key: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    
    # AI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ai_model: str = Field(default="gpt-3.5-turbo", env="AI_MODEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_service_port(self, service_name: str) -> int:
        """Get port for a service by name"""
        port_map = {
            "db_svc": self.db_service_port,
            "bot_svc": self.bot_service_port,
            "payment_svc": self.payment_service_port,
            "controller_svc": self.controller_service_port,
            "ai_svc": self.ai_service_port,
            "formatting_svc": self.formatting_service_port,
            "channel_mgr_svc": self.channel_mgr_service_port,
            "user_svc": self.user_service_port,
            "miniapp_svc": self.miniapp_service_port,
            "admin_svc": self.admin_service_port,
        }
        return port_map.get(service_name, 8000)
    
    def get_service_url(self, service_name: str, host: str = "localhost") -> str:
        """Get full URL for a service"""
        port = self.get_service_port(service_name)
        return f"http://{host}:{port}"
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    def validate_service_token(self):
        """Validate service token configuration"""
        if self.is_production() and self.service_token == "dev_service_token_change_in_production":
            raise ValueError(
                "CRITICAL SECURITY: You must set SERVICE_TOKEN in production! "
                "The default development token is not secure."
            )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
        # Validate security in production
        if _config.is_production():
            _config.validate_service_token()
    return _config