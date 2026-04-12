from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from coding_round.constants import DEFAULT_JUDGE0_BASE_URL


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None

    text = value.strip()
    return text or None


def resolve_provider_api_key(provider: str, request_api_key: str | None = None) -> str:
    provider_name = (provider or "").strip().lower()
    env_var = PROVIDER_ENV_VARS.get(provider_name)

    key = _clean(request_api_key)
    if key:
        return key

    if env_var:
        key = _clean(os.getenv(env_var))
        if key:
            return key

    if env_var:
        raise ValueError(
            f"No API key configured for {provider_name}. Add {env_var} to .env or enter a key in the UI."
        )

    raise ValueError(f"Unsupported provider '{provider_name}'.")


def resolve_whisper_api_key(
    provider: str,
    request_whisper_api_key: str | None = None,
    request_provider_api_key: str | None = None,
) -> str:
    whisper_key = _clean(request_whisper_api_key)
    if whisper_key:
        return whisper_key

    openai_env_key = _clean(os.getenv("WHISPER_API_KEY")) or _clean(os.getenv("OPENAI_API_KEY"))
    if openai_env_key:
        return openai_env_key

    provider_name = (provider or "").strip().lower()
    if provider_name == "openai":
        provider_key = _clean(request_provider_api_key)
        if provider_key:
            return provider_key

    raise ValueError(
        "A Whisper/OpenAI API key is required. Add WHISPER_API_KEY or OPENAI_API_KEY to .env, "
        "or provide it in the UI."
    )


def resolve_elevenlabs_api_key(request_api_key: str | None = None) -> str:
    key = _clean(request_api_key) or _clean(os.getenv("ELEVENLABS_API_KEY"))
    if key:
        return key

    raise ValueError(
        "An ElevenLabs API key is required. Add ELEVENLABS_API_KEY to .env or provide it in the UI."
    )


def resolve_elevenlabs_voice_id(request_voice_id: str | None = None) -> str:
    return (
        _clean(request_voice_id)
        or _clean(os.getenv("ELEVENLABS_VOICE_ID"))
        or DEFAULT_ELEVENLABS_VOICE_ID
    )


def resolve_elevenlabs_model_id(request_model_id: str | None = None) -> str:
    return (
        _clean(request_model_id)
        or _clean(os.getenv("ELEVENLABS_MODEL_ID"))
        or DEFAULT_ELEVENLABS_MODEL_ID
    )


def resolve_judge0_api_key(request_api_key: str | None = None) -> str | None:
    return _clean(request_api_key) or _clean(os.getenv("JUDGE0_API_KEY"))


def resolve_judge0_base_url(request_base_url: str | None = None) -> str:
    return _clean(request_base_url) or _clean(os.getenv("JUDGE0_BASE_URL")) or DEFAULT_JUDGE0_BASE_URL


def get_public_runtime_config() -> dict[str, Any]:
    return {
        "providers": {
            provider: {
                "configured": bool(_clean(os.getenv(env_var))),
                "envVar": env_var,
            }
            for provider, env_var in PROVIDER_ENV_VARS.items()
        },
        "whisper": {
            "configured": bool(_clean(os.getenv("WHISPER_API_KEY")) or _clean(os.getenv("OPENAI_API_KEY"))),
            "envVar": "WHISPER_API_KEY",
        },
        "elevenlabs": {
            "configured": bool(_clean(os.getenv("ELEVENLABS_API_KEY"))),
            "envVar": "ELEVENLABS_API_KEY",
            "defaultVoiceId": resolve_elevenlabs_voice_id(),
            "defaultModelId": resolve_elevenlabs_model_id(),
        },
        "judge0": {
            "configured": bool(_clean(os.getenv("JUDGE0_API_KEY"))),
            "envVar": "JUDGE0_API_KEY",
            "baseUrl": resolve_judge0_base_url(),
        },
    }
