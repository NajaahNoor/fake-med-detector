"""
app/core/exceptions.py
-----------------------
Custom exception classes for the application.
"""


class FakeMedDetectorException(Exception):
    """Base exception for the application."""
    pass


class DatabaseException(FakeMedDetectorException):
    """Database-related errors."""
    pass


class OCRException(FakeMedDetectorException):
    """OCR processing errors."""
    pass


class VerificationException(FakeMedDetectorException):
    """Drug verification errors."""
    pass


class AgentException(FakeMedDetectorException):
    """Agent execution errors."""
    pass


class ConfigurationException(FakeMedDetectorException):
    """Configuration/initialization errors."""
    pass


class FileException(FakeMedDetectorException):
    """File upload/processing errors."""
    pass
