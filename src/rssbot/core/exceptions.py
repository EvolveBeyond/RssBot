"""
Custom exceptions for RSS Bot platform
"""


class ServiceError(Exception):
    """Base exception for service-related errors"""
    def __init__(self, message: str, service_name: str = None, status_code: int = 500):
        self.message = message
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(self.message)


class ServiceUnavailableError(ServiceError):
    """Exception raised when a service is unavailable"""
    def __init__(self, service_name: str, attempted_methods: list = None):
        self.attempted_methods = attempted_methods or []
        message = f"Service '{service_name}' is unavailable"
        if attempted_methods:
            message += f" (tried: {', '.join(attempted_methods)})"
        super().__init__(message, service_name, 503)


class ConfigurationError(ServiceError):
    """Exception raised for configuration-related errors"""
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        super().__init__(message, status_code=500)


class DiscoveryError(ServiceError):
    """Exception raised during service discovery"""
    def __init__(self, message: str, service_name: str = None):
        super().__init__(message, service_name, 500)


class HealthCheckError(ServiceError):
    """Exception raised during health checks"""
    def __init__(self, message: str, service_name: str = None):
        super().__init__(message, service_name, 503)