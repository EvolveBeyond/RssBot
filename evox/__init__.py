"""
Evox - Modern Python Microservices Framework

A lightweight, plugin-first microservices framework built on FastAPI with
hybrid orchestration, self-healing proxies, dynamic discovery, and intelligent caching.

Version 0.0.1-alpha - Early public alpha release
"""

__version__ = "0.0.1-alpha"

# Export core components
from .core import (
    service, get, post, put, delete, endpoint,
    proxy, data_io, data_intent, inject, scheduler,
    PriorityLevel, get_priority_queue, initialize_queue
)

__all__ = [
    "service", "get", "post", "put", "delete", "endpoint",
    "proxy", "data_io", "data_intent", "inject", "scheduler",
    "PriorityLevel", "get_priority_queue", "initialize_queue"
]