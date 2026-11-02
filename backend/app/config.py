"""Configuration settings for QuantNiti."""
import os
from typing import Dict
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""
    
    # Cache TTL configuration (in seconds)
    MARKET_DATA_TTL_1M_SECONDS: int = int(os.getenv("MARKET_DATA_TTL_1M_SECONDS", "60"))
    MARKET_DATA_TTL_5M_SECONDS: int = int(os.getenv("MARKET_DATA_TTL_5M_SECONDS", "120"))
    MARKET_DATA_TTL_15M_SECONDS: int = int(os.getenv("MARKET_DATA_TTL_15M_SECONDS", "300"))
    MARKET_DATA_TTL_1H_SECONDS: int = int(os.getenv("MARKET_DATA_TTL_1H_SECONDS", "900"))
    MARKET_DATA_TTL_1D_SECONDS: int = int(os.getenv("MARKET_DATA_TTL_1D_SECONDS", "3600"))
    
    # Live data toggle
    USE_LIVE_DATA: bool = os.getenv("USE_LIVE_DATA", "true").lower() == "true"
    
    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://quant:quant@localhost:5432/quantniti")
    
    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    
    @property
    def market_data_ttl(self) -> Dict[str, int]:
        """Return TTL mapping for all supported timeframes."""
        return {
            "1m": self.MARKET_DATA_TTL_1M_SECONDS,
            "5m": self.MARKET_DATA_TTL_5M_SECONDS,
            "15m": self.MARKET_DATA_TTL_15M_SECONDS,
            "1h": self.MARKET_DATA_TTL_1H_SECONDS,
            "1d": self.MARKET_DATA_TTL_1D_SECONDS,
        }
    
    def get_ttl(self, timeframe: str) -> int:
        """Get TTL for a specific timeframe."""
        return self.market_data_ttl.get(timeframe, 3600)
    
    def validate_ttl_config(self) -> bool:
        """Validate that all TTL values are positive integers."""
        for key, value in self.market_data_ttl.items():
            if not isinstance(value, int) or value <= 0:
                return False
        return True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()