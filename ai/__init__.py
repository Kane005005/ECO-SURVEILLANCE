"""
AI providers for ECO-SURVEILLANCE MALI.
"""
from ai.base import AIProvider
from ai.groq import GroqProvider
from ai.openai_compat import OpenAICompatProvider

__all__ = ["AIProvider", "GroqProvider", "OpenAICompatProvider"]
