"""
llm.py
======
Helpers for normalizing LLM responses across providers.
"""

from typing import Any


def extract_text(content: Any) -> str:
    """
    Normalize LLM message content into plain text.
    Handles strings, lists of parts (dicts with 'text'), and nested objects.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    # LangChain / provider sometimes returns list-of-parts
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                if "text" in part:
                    parts.append(str(part.get("text", "")))
                elif "content" in part:
                    parts.append(str(part.get("content", "")))
            else:
                parts.append(str(part))
        return "\n".join(p for p in parts if p).strip()

    # Fallback for AIMessage-like objects
    if hasattr(content, "content"):
        return extract_text(content.content)

    return str(content).strip()

