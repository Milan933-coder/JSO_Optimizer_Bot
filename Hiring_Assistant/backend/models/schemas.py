# =============================================================================
# models/schemas.py
# TalentScout request/response models
# provider + api_key are sent by the frontend with every request
# =============================================================================

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


SUPPORTED_PROVIDERS = Literal["openai", "anthropic", "gemini"]
SUPPORTED_CODING_LANGUAGES = Literal["python", "cpp", "java", "javascript"]


class CodingLanguage(BaseModel):
    slug: str
    label: str
    judge0_language_id: int
    starter_code: str


class CodingSample(BaseModel):
    index: int
    title: str
    input: str
    output: str


class CodingSampleResult(BaseModel):
    sample_index: int
    input: str
    expected_output: str
    actual_output: str
    passed: bool
    judge0_status: str
    judge0_status_id: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    time: Optional[str] = None
    memory: Optional[int] = None


class CodingAttemptResult(BaseModel):
    mode: Literal["run", "submit"]
    passed: bool
    verdict: str
    status_summary: str
    passed_samples: int
    total_samples: int
    sample_results: list[CodingSampleResult] = Field(default_factory=list)


class CodingProblem(BaseModel):
    source: str
    source_url: str
    mirror_url: str
    title: str
    codeforces_id: str
    contest_id: int
    index: str
    rating: int
    solved_count: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    statement: str
    input_spec: str
    output_spec: str
    notes: Optional[str] = None
    time_limit: str
    memory_limit: str
    samples: list[CodingSample] = Field(default_factory=list)
    available_languages: list[CodingLanguage] = Field(default_factory=list)


class CodingRoundPayload(BaseModel):
    status: str
    is_active: bool
    is_completed: bool
    time_limit_minutes: int
    max_attempts: int
    attempts_used: int
    attempts_left: int
    remaining_seconds: int
    started_at: Optional[str] = None
    expires_at: Optional[str] = None
    completion_reason: Optional[str] = None
    problem: CodingProblem
    last_result: Optional[CodingAttemptResult] = None


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
    coding_round: Optional[CodingRoundPayload] = None


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
    coding_round: Optional[CodingRoundPayload] = None


class VoiceMessageResponse(BaseModel):
    session_id:         str
    transcript:         str
    detected_language:  Optional[str] = None
    reply:              str
    phase:              str
    is_closed:          bool = False
    coding_round:       Optional[CodingRoundPayload] = None
    voice_id:           str
    audio_mime_type:    str
    audio_base64:       str


class CVIntakeResponse(BaseModel):
    session_id:         str
    extracted_profile:  str
    reply:              str
    phase:              str
    is_closed:          bool = False
    coding_round:       Optional[CodingRoundPayload] = None


class CodingRoundAttemptRequest(BaseModel):
    session_id: str
    source_code: str
    language_slug: SUPPORTED_CODING_LANGUAGES
    sample_index: int = Field(default=0, ge=0)
    judge0_api_key: Optional[str] = None
    judge0_base_url: Optional[str] = None

    @field_validator("source_code")
    @classmethod
    def source_code_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("source_code must not be empty")
        return v


class CodingRoundStartRequest(BaseModel):
    session_id: str


class CodingRoundActionResponse(BaseModel):
    session_id: str
    action: Literal["run", "submit"]
    phase: str
    is_closed: bool = False
    reply: Optional[str] = None
    coding_round: Optional[CodingRoundPayload] = None
    result: CodingAttemptResult
