import logging
import litellm
from typing import Optional, Dict, Any, List
import json
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

litellm.drop_params = True

class AIClient:

    def __init__(self):
        self.provider = settings.ai_provider
        self.model = self._get_model_string()
        self._configure_provider()
        self._db: Optional[Session] = None

    def _get_model_string(self) -> str:
        model = settings.ai_model

        if self.provider == "openrouter":
            if not model.startswith("openrouter/"):
                return f"openrouter/{model}"
            return model
        elif self.provider == "ollama":
            if not model.startswith("ollama/"):
                return f"ollama/{model}"
            return model
        elif self.provider == "anthropic":
            return model
        elif self.provider == "openai":
            return model
        else:
            return model

    def _configure_provider(self):
        if self.provider == "openrouter":
            litellm.api_key = settings.openrouter_api_key
            litellm.api_base = "https://openrouter.ai/api/v1"
        elif self.provider == "ollama":
            litellm.api_base = settings.ai_base_url or "http://localhost:11434"
        elif self.provider == "anthropic":
            litellm.api_key = settings.anthropic_api_key
        elif self.provider == "openai":
            litellm.api_key = settings.openai_api_key

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        json_mode: bool = False
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        import os
        env_key = None

        try:
            if self.provider == "openrouter" and settings.openrouter_api_key:
                env_key = settings.openrouter_api_key
                os.environ["OPENROUTER_API_KEY"] = env_key
            elif self.provider == "anthropic" and settings.anthropic_api_key:
                env_key = settings.anthropic_api_key
                os.environ["ANTHROPIC_API_KEY"] = env_key
            elif self.provider == "openai" and settings.openai_api_key:
                env_key = settings.openai_api_key
                os.environ["OPENAI_API_KEY"] = env_key

            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI completion error: {e}")
            raise
        finally:
            if env_key:
                if self.provider == "openrouter":
                    os.environ.pop("OPENROUTER_API_KEY", None)
                elif self.provider == "openai":
                    os.environ.pop("OPENAI_API_KEY", None)
                elif self.provider == "anthropic":
                    os.environ.pop("ANTHROPIC_API_KEY", None)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )

        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return json.loads(cleaned.strip())

    def should_obfuscate(self, provider: Optional[str] = None) -> bool:
        """
        Check if obfuscation is enabled for the current/specified provider.

        Requires database session to check privacy settings.
        """
        if self._db is None:
            return False

        from app.models.privacy_settings import get_or_create_privacy_settings
        privacy_settings = get_or_create_privacy_settings(self._db)

        if not privacy_settings.obfuscation_enabled:
            return False

        provider = provider or self.provider

        if provider == "ollama":
            return privacy_settings.ollama_obfuscation
        elif provider == "openrouter":
            return privacy_settings.openrouter_obfuscation
        elif provider == "anthropic":
            return privacy_settings.anthropic_obfuscation
        elif provider == "openai":
            return privacy_settings.openai_obfuscation

        # Default to obfuscating unknown providers
        return True


_ai_client: Optional[AIClient] = None

def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
