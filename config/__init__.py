"""
Config package for IndiPaperTrade.

Provides centralized configuration management with environment variable support.
"""

from .settings import Settings, INSTRUMENT_TOKENS

__all__ = [
    'Settings',
    'INSTRUMENT_TOKENS',
]
