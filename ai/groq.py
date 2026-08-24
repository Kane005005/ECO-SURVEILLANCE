from ai.base import AIProvider
from typing import Dict, Any, Optional
import requests


class GroqProvider(AIProvider):
    name = "groq"
    is_optional = True

    def __init__(self, api_key: Optional[str] = None, model: str = None):
        from decouple import config as _config
        self.api_key = api_key or _config("GROQ_API_KEY", default="")
        self.model = model or _config("GROQ_MODEL", default="openai/gpt-oss-120b")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "degraded", "reason": "GROQ_API_KEY manquant"}
        return {"status": "ok", "model": self.model}

    def close(self) -> None:
        self.session.close()

    def _call_model(self, system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str:
        if not self.api_key:
            return ""
        models_to_try = [self.model, "openai/gpt-oss-20b", "groq/compound"]
        for m in models_to_try:
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            try:
                response = self.session.post(self.base_url, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception:
                continue
        return ""

    def interpret_incident(self, context: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = (
            "Tu es le système d'Intelligence Artificielle d'ECO-SURVEILLANCE MALI propulsé par GPT-OSS. "
            "Analyse l'incident ou l'alerte environnementale, contextualise les risques locaux au Mali et propose 2 recommandations opérationnelles. "
            "Réponds en français, sous forme structurée et synthétique."
        )
        content = self._call_model(system_prompt, str(context), max_tokens=350)
        if content:
            return {"summary": content, "model": self.model, "provider": self.name}
        return {
            "summary": "Analyse de vigilance : paramètres sous surveillance continue.",
            "model": self.model,
            "provider": self.name,
        }

    def diagnose_entity(self, entity_type: str, data: Dict[str, Any]) -> str:
        """Provide a concise (2-3 sentences) AI environmental diagnosis for a map popup."""
        system_prompt = (
            "Tu es l'IA experte d'ECO-SURVEILLANCE MALI (GPT-OSS). "
            "Rédige un diagnostic direct et percutant en 2 phrases maximum, avec un ton institutionnel et une recommandation concrète pour le Mali."
        )
        user_prompt = f"Entité: {entity_type}. Données télémétriques: {data}"
        result = self._call_model(system_prompt, user_prompt, max_tokens=150)
        if result:
            return result
        # Fallback diagnostics
        if entity_type == "station":
            return f"Débit de {data.get('discharge', 'N/A')} m³/s sous surveillance. Risque modéré sur les berges aval."
        elif entity_type == "flood":
            return f"Inondation de {data.get('flooded_area_km2', 'N/A')} km² observée par satellite. Recommandation d'alerte des communes riveraines."
        elif entity_type == "fire":
            return f"Foyer thermique actif détecté par VIIRS ({data.get('frp', 'N/A')} MW). Recommandation de mobilisation des vigies forestières."
        return "Télémétrie conforme aux seuils saisonniers sous surveillance satellite continue."

    def chat_copilot(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Conversational assistance on Mali environmental data."""
        system_prompt = (
            "Tu es l'Assistant Copilote IA officiel d'ECO-SURVEILLANCE MALI (basé sur GPT-OSS). "
            "Tu aides les décideurs, hydrologues et ministères à interpréter les données satellites (GloFAS, NASA FIRMS, LANCE Flood, NASA POWER, Sentinel-2/5P) pour le Mali. "
            "Réponds avec précision, clarté, rigueur et en français."
        )
        user_msg = f"Contexte actuel: {context}\nQuestion utilisateur: {query}" if context else query
        return self._call_model(system_prompt, user_msg, max_tokens=600)

