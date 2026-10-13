"""
Inference Engine supporting local Ollama, Claude, OpenAI, and deterministic Mock with Zero-PHI checks.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Digoxin Therapeutic Level Estimator"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return "Mock provider only: no model inference, clinical verification, or standards-conformance assessment was performed."


class LLMFactory:
    """Creates configured LLM client instances with zero-PHI protection."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Digoxin Therapeutic Level Estimator"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError("Only the deterministic mock provider is implemented; external providers are not configured.")
