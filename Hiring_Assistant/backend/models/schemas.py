# =============================================================================
# models/schemas.py
# TalentScout request/response models
# provider + api_key are sent by the frontend with every request
# =============================================================================

from pydantic import BaseModel, field_validator
from typing import Optional, Literal


SUPPORTED_PROVIDERS = Literal["openai", "anthropic", "gemini"]


class StartRequest(BaseModel):
    provider: SUPPORTED_PROVIDERS
    api_key:  str

    @field_validator("api_key")
    @classmethod
    def api_key_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("api_key must not be empty")
        return v.strip()


class StartResponse(BaseModel):
    session_id: str
    reply:      str
    phase:      str


class MessageRequest(BaseModel):
    session_id: str
    provider:   SUPPORTED_PROVIDERS
    api_key:    str
    message:    str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("message must not be empty")
        return v.strip()


class MessageResponse(BaseModel):
    session_id: str
    reply:      str
    phase:      str
    is_closed:  bool = False


class VoiceMessageResponse(BaseModel):
    session_id:         str
    transcript:         str
    detected_language:  Optional[str] = None
    reply:              str
    phase:              str
    is_closed:          bool = False
    voice_id:           str
    audio_mime_type:    str
    audio_base64:       str


class CVIntakeResponse(BaseModel):
    session_id:         str
    extracted_profile:  str
    reply:              str
    phase:              str
    is_closed:          bool = False
