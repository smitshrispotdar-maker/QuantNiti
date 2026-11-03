"""Shared security utilities: rate limiter, etc."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter instance - configured in main.py and used in routers
limiter = Limiter(key_func=get_remote_address, default_limits=[])