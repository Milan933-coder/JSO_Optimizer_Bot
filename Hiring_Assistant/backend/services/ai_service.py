# =============================================================================
# services/ai_service.py
# Multi-provider AI service — OpenAI, Anthropic (Claude), Google Gemini
# The provider + api_key are passed in per-request by the user.
# =============================================================================

import json
from io import BytesIO
from typing import List, Optional, Tuple

import httpx


# ─── Supported providers ─────────────────────────────────────────────────────

SUPPORTED_PROVIDERS = {"openai", "anthropic", "gemini"}


# ─── Model defaults per provider ─────────────────────────────────────────────

DEFAULT_MODELS = {
    "openai":    "gpt-4o-mini",
    "anthropic": "claude-opus-4-5",
    "gemini":    "gemini-1.5-pro",
}


DEFAULT_WHISPER_MODEL = "whisper-v3"
DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"
DEFAULT_ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"


# =============================================================================
# chat_completion — returns (reply_text, usage_dict)
# =============================================================================

async def chat_completion(
    provider:     str,
    api_key:      str,
    system_prompt: str,
    messages:     List[dict],
    temperature:  float = 0.7,
    max_tokens:   int   = 2000,
) -> tuple[str, dict]:
    """
    Unified chat completion across providers.
    All providers receive the same system_prompt + messages list.
    Returns (reply_text, usage_dict).
    """
    provider = provider.lower().strip()

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider '{provider}'. Choose from: {SUPPORTED_PROVIDERS}")

    if provider == "openai":
        return await _openai_chat(api_key, system_prompt, messages, temperature, max_tokens)

    if provider == "anthropic":
        return await _anthropic_chat(api_key, system_prompt, messages, temperature, max_tokens)

    if provider == "gemini":
        return await _gemini_chat(api_key, system_prompt, messages, temperature, max_tokens)


# =============================================================================
# json_completion — forces structured JSON output, returns parsed dict
# =============================================================================

async def json_completion(
    provider:     str,
    api_key:      str,
    system_prompt: str,
    user_message: str,
    temperature:  float = 0.3,
) -> dict:
    """
    Completion that returns parsed JSON.
    Used for: candidate info extraction, question generation.
    """
    provider = provider.lower().strip()

    if provider == "openai":
        return await _openai_json(api_key, system_prompt, user_message, temperature)

    if provider == "anthropic":
        return await _anthropic_json(api_key, system_prompt, user_message, temperature)

    if provider == "gemini":
        return await _gemini_json(api_key, system_prompt, user_message, temperature)

    raise ValueError(f"Unsupported provider: {provider}")


# =============================================================================
# ── OPENAI ────────────────────────────────────────────────────────────────────
# =============================================================================

async def _openai_chat(api_key, system_prompt, messages, temperature, max_tokens):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    response = await client.chat.completions.create(
        model       = DEFAULT_MODELS["openai"],
        messages    = [{"role": "system", "content": system_prompt}] + messages,
        temperature = temperature,
        max_tokens  = max_tokens,
    )
    reply = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens":     response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens":      response.usage.total_tokens,
    }
    return reply, usage


async def _openai_json(api_key, system_prompt, user_message, temperature):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    response = await client.chat.completions.create(
        model           = DEFAULT_MODELS["openai"],
        messages        = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature     = temperature,
        max_tokens      = 2000,
        response_format = {"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)


# =============================================================================
# ── ANTHROPIC (Claude) ────────────────────────────────────────────────────────
# =============================================================================

async def _anthropic_chat(api_key, system_prompt, messages, temperature, max_tokens):
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Anthropic requires alternating user/assistant roles — filter system msgs
    filtered = [m for m in messages if m["role"] in ("user", "assistant")]

    response = await client.messages.create(
        model      = DEFAULT_MODELS["anthropic"],
        system     = system_prompt,
        messages   = filtered,
        temperature= temperature,
        max_tokens = max_tokens,
    )
    reply = response.content[0].text if response.content else ""
    usage = {
        "prompt_tokens":     response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens":      response.usage.input_tokens + response.usage.output_tokens,
    }
    return reply, usage


async def _anthropic_json(api_key, system_prompt, user_message, temperature):
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Instruct Claude to return only JSON
    json_system = system_prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."

    response = await client.messages.create(
        model      = DEFAULT_MODELS["anthropic"],
        system     = json_system,
        messages   = [{"role": "user", "content": user_message}],
        temperature= temperature,
        max_tokens = 2000,
    )
    raw = response.content[0].text if response.content else "{}"
    # Strip any accidental markdown fences
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


# =============================================================================
# ── GOOGLE GEMINI ─────────────────────────────────────────────────────────────
# =============================================================================

async def _gemini_chat(api_key, system_prompt, messages, temperature, max_tokens):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name   = DEFAULT_MODELS["gemini"],
        system_instruction = system_prompt,
    )

    # Convert messages to Gemini format
    gemini_history = []
    for m in messages[:-1]:   # all but last
        role = "user" if m["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [m["content"]]})

    chat   = model.start_chat(history=gemini_history)
    result = await chat.send_message_async(
        messages[-1]["content"],
        generation_config=genai.types.GenerationConfig(
            temperature = temperature,
            max_output_tokens = max_tokens,
        ),
    )
    reply = result.text or ""
    usage = {
        "prompt_tokens":     result.usage_metadata.prompt_token_count,
        "completion_tokens": result.usage_metadata.candidates_token_count,
        "total_tokens":      result.usage_metadata.total_token_count,
    }
    return reply, usage


async def _gemini_json(api_key, system_prompt, user_message, temperature):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    json_system = system_prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."

    model  = genai.GenerativeModel(
        model_name         = DEFAULT_MODELS["gemini"],
        system_instruction = json_system,
    )
    result = await model.generate_content_async(
        user_message,
        generation_config=genai.types.GenerationConfig(
            temperature       = temperature,
            max_output_tokens = 2000,
        ),
    )
    raw = result.text or "{}"
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


# =============================================================================
# Audio helpers
# =============================================================================

async def transcribe_audio_whisper(
    openai_api_key: str,
    audio_bytes: bytes,
    filename: str = "audio.webm",
    content_type: Optional[str] = None,
    prompt: Optional[str] = None,
    model: str = DEFAULT_WHISPER_MODEL,
) -> Tuple[str, Optional[str]]:
    """
    Transcribe user audio with OpenAI Whisper and return (transcript, language).
    """
    if not openai_api_key or not openai_api_key.strip():
        raise ValueError("OpenAI API key is required for Whisper transcription.")
    if not audio_bytes:
        raise ValueError("Audio file is empty.")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=openai_api_key.strip())
    file_obj = (filename, audio_bytes, content_type or "application/octet-stream")

    kwargs = {
        "model": model,
        "file": file_obj,
        "response_format": "verbose_json",
    }
    if prompt:
        kwargs["prompt"] = prompt

    try:
        result = await client.audio.transcriptions.create(**kwargs)
    except Exception:
        # "whisper-v3" is requested by product spec; fallback keeps compatibility
        # if the configured API endpoint does not expose this model name.
        if model == "whisper-v3":
            kwargs["model"] = "whisper-1"
            result = await client.audio.transcriptions.create(**kwargs)
        else:
            raise

    text = getattr(result, "text", None)
    language = getattr(result, "language", None)

    if isinstance(result, dict):
        text = text or result.get("text")
        language = language or result.get("language")

    transcript = (text or "").strip()
    if not transcript:
        raise RuntimeError("Whisper returned an empty transcript.")

    return transcript, language


def _mime_from_elevenlabs_output_format(output_format: str) -> str:
    prefix = (output_format or "").split("_", 1)[0].lower()
    if prefix == "mp3":
        return "audio/mpeg"
    if prefix == "pcm":
        return "audio/pcm"
    if prefix == "ulaw":
        return "audio/basic"
    return "application/octet-stream"


async def synthesize_speech_elevenlabs(
    elevenlabs_api_key: str,
    text: str,
    voice_id: str,
    model_id: str = DEFAULT_ELEVENLABS_MODEL,
    output_format: str = DEFAULT_ELEVENLABS_OUTPUT_FORMAT,
) -> Tuple[bytes, str]:
    """
    Convert assistant text output to speech via ElevenLabs.
    Returns (audio_bytes, mime_type).
    """
    if not elevenlabs_api_key or not elevenlabs_api_key.strip():
        raise ValueError("ElevenLabs API key is required for text-to-speech.")
    if not voice_id or not voice_id.strip():
        raise ValueError("ElevenLabs voice_id is required.")
    if not text or not text.strip():
        raise ValueError("Text is empty. Nothing to synthesize.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id.strip()}"
    headers = {
        "xi-api-key": elevenlabs_api_key.strip(),
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "output_format": output_format,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise RuntimeError(
            f"ElevenLabs error ({response.status_code}): {response.text[:400]}"
        )

    audio_bytes = response.content
    if not audio_bytes:
        raise RuntimeError("ElevenLabs returned empty audio.")

    return audio_bytes, _mime_from_elevenlabs_output_format(output_format)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from uploaded PDF CV.
    """
    if not pdf_bytes:
        return ""

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    chunks = []
    for page in reader.pages[:20]:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


async def summarize_cv_text_with_model(
    provider: str,
    api_key: str,
    cv_text: str,
) -> str:
    """
    Convert CV text into a structured candidate profile for the chat flow.
    """
    prompt = (
        "Extract candidate information from this CV and respond in plain text with:\n"
        "- Full Name\n"
        "- Email\n"
        "- Phone\n"
        "- Years of Experience\n"
        "- Desired Position\n"
        "- Current Location\n"
        "- Tech Stack\n"
        "- Short summary (4 lines max)\n\n"
        f"CV content:\n{cv_text[:12000]}"
    )
    reply, _ = await chat_completion(
        provider=provider,
        api_key=api_key,
        system_prompt="You are an expert resume parser. Be accurate and concise.",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=900,
    )
    return reply.strip()
