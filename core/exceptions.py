from __future__ import annotations


class AIERPError(Exception):
    pass


class CoreError(AIERPError):
    pass


class ConfigurationError(CoreError):
    pass


class ValidationError(CoreError):
    pass


class SerializationError(CoreError):
    pass
