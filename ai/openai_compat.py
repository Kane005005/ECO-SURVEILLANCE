"""
OpenAI-compatible AI provider.
Works with OpenAI API, OpenRouter, Groq, or any OpenAI-compatible endpoint.
"""
from ai.base import AIProvider
from typing import Dict, Any, Optional
import os
import logging

logger = logging.getLogger("ai.openai_compat")


class OpenAICompatProvider(AIProvider):
    """AI provider compatible with OpenAI API format."""
    name = "openai_compat"
    is_optional = True

    def __init__(self, api_key: str = "", model: str = "", base_url: str = "", **kwargs):
        import requests
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL", "")
            or "https://api.openai.com/v1"
        )
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })

    def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "degraded", "reason": "OPENAI_API_KEY missing"}
        try:
            resp = self.session.get(f"{self.base_url}/models", timeout=10)
            resp.raise_for_status()
            return {"status": "ok", "models_available": len(resp.json().get("data", []))}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def close(self) -> None:
        self.session.close()

    def _chat(self, system_prompt: str, user_message: str,
              temperature: float = 0.2, max_tokens: int = 2000) -> str:
        """Generic chat completion."""
        if not self.api_key:
            return ""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("AI chat failed: %s", e)
            return ""

    def interpret_incident(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret an environmental incident using AI."""
        system_prompt = (
            "Tu es un assistant d'analyse environnementale pour le Mali. "
            "Tu analyses des données environnementales structurées (feux, climat, "
            "végétation, qualité de l'air) et tu fournis des interprétations claires. "
            "Tu ne prends pas de décision : tu expliques, contextualises et recommandes. "
            "Tu ne remplaces jamais un calcul scientifique. "
            "Réponds en français, concis et structuré. "
            "Format: 1) Résumé, 2) Analyse, 3) Recommandations."
        )

        user_msg = f"Analyse cet incident environnemental:\n{str(context)}"
        summary = self._chat(system_prompt, user_msg)

        return {
            "summary": summary or "Analyse indisponible",
            "model": self.model,
            "provider": self.name,
        }

    def analyze_risk(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk assessment data and provide recommendations."""
        system_prompt = (
            "Tu es un expert en gestion des risques environnementaux au Mali. "
            "Analyse les données de risque et fournis des recommandations d'action. "
            "Sois spécifique et pragmatique. Réponds en français."
        )
        user_msg = f"Données de risque:\n{str(risk_data)}"
        summary = self._chat(system_prompt, user_msg)

        return {
            "summary": summary or "Analyse indisponible",
            "model": self.model,
            "provider": self.name,
        }

    def summarize_zone(self, zone_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary for a monitoring zone."""
        system_prompt = (
            "Tu es un analyste environnemental. "
            "Résume l'état d'une zone de surveillance du Mali en 3-5 points clés. "
            "Sois factuel et base-toi sur les données fournies. Réponds en français."
        )
        user_msg = f"Données de la zone:\n{str(zone_data)}"
        summary = self._chat(system_prompt, user_msg)

        return {
            "summary": summary or "Résumé indisponible",
            "model": self.model,
            "provider": self.name,
        }
