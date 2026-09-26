"""Local activity infrastructure, independent of screen capture and LLM availability."""

from .store import ActivityStore

__all__ = ["ActivityStore"]
