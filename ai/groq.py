from ai.base import AIProvider
from typing import Dict, Any, Optional
import requests


class GroqProvider(AIProvider):
    name = "groq"
    is_optional = True

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "degraded", "reason": "GROQ_API_KEY manquant"}
        return {"status": "ok"}

    def close(self) -> None:
        self.session.close()

    def interpret_incident(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            return {"summary": "", "recommendations": [], "explanation": "IA indisponible"}
        system_prompt = (
            "Tu es un assistant d'analyse environnementale. "
            "Tu ne prends pas de décision : tu expliques, contextualises et recommandes. "
            "Tu ne remplaces jamais un calcul scientifique. "
            "Réponds en français, concis et structuré."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(context)},
            ],
            "temperature": 0.2,
        }
        response = self.session.post(self.base_url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return {
            "summary": data["choices"][0]["message"]["content"],
            "model": self.model,
            "provider": self.name,
        }
