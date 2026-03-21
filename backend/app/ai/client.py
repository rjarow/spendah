import logging
import litellm
from typing import Optional, Dict, Any, Literal
import json
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

litellm.drop_params = True

TaskType = Literal["categorize", "merchant_clean", "format_detect", "coach"]


class AIClient:
    def __init__(self, db: Optional[Session] = None, task: Optional[TaskType] = None):
        self.provider = settings.ai_provider
        self._db = db
        self._task = task
        self.model = self._get_model_string()
        self._configure_provider()

    def _get_task_model(self) -> Optional[str]:
        """Get task-specific model from database if configured."""
        if not self._db or not self._task:
            return None

        from app.models.ai_settings import get_or_create_ai_settings

        ai_settings = get_or_create_ai_settings(self._db)

        task_model_map = {
            "categorize": ai_settings.categorize_model,
            "merchant_clean": ai_settings.merchant_clean_model,
            "format_detect": ai_settings.format_detect_model,
            "coach": ai_settings.coach_model,
        }

        return task_model_map.get(self._task)

    def _get_model_string(self) -> str:
        task_model = self._get_task_model()
        model = task_model or settings.ai_model

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

    def _get_api_key(self, provider: str) -> Optional[str]:
        if self._db is not None:
            from app.models.ai_settings import get_or_create_ai_settings

            ai_settings = get_or_create_ai_settings(self._db)

            if provider == "openrouter" and ai_settings.openrouter_api_key:
                return ai_settings.openrouter_api_key
            elif provider == "anthropic" and ai_settings.anthropic_api_key:
                return ai_settings.anthropic_api_key
            elif provider == "openai" and ai_settings.openai_api_key:
                return ai_settings.openai_api_key

        if provider == "openrouter":
            return settings.openrouter_api_key
        elif provider == "anthropic":
            return settings.anthropic_api_key
        elif provider == "openai":
            return settings.openai_api_key

        return None

    def _configure_provider(self):
        """Configure provider-specific settings (base URL only, keys passed per-request)."""
        if self.provider == "openrouter":
            self._api_base = "https://openrouter.ai/api/v1"
        elif self.provider == "ollama":
            self._api_base = settings.ai_base_url or "http://localhost:11434"
        else:
            self._api_base = None

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        json_mode: bool = False,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            api_key = self._get_api_key(self.provider)
            if api_key:
                kwargs["api_key"] = api_key
            if self._api_base:
                kwargs["api_base"] = self._api_base

            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI completion error: {e}")
            raise

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )

        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {e}")
            logger.debug(f"Raw response was: {cleaned[:500]}")
            raise ValueError("AI returned an invalid response format")

    def should_obfuscate(self, provider: Optional[str] = None) -> bool:
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

        return True


_ai_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client


def get_ai_client_with_db(db: Session, task: Optional[TaskType] = None) -> AIClient:
    return AIClient(db=db, task=task)
