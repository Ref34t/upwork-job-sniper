"""
Notification services for the Upwork Job Sniper application.

This package contains notification service implementations for sending
notifications to various platforms (e.g., Pushover, Email, etc.).
"""

from .pushover import PushoverNotifier

__all__ = ['PushoverNotifier']
