"""Groq LLM client with graceful degradation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Type, TypeVar

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def _ensure_env_loaded() -> None:
    """Re-read .env so model changes apply without restarting langgraph dev."""
    if _ENV_PATH.is_file():
        load_dotenv(_ENV_PATH, override=True)


def _get_api_key() -> Optional[str]:
    _ensure_env_loaded()
    return os.getenv("GROQ_API_KEY")


def get_chat_model(model_env: str, default: str) -> Optional[ChatGroq]:
    _ensure_env_loaded()
    api_key = _get_api_key()
    if not api_key:
        return None
    model = os.getenv(model_env, default)
    return ChatGroq(model=model, api_key=api_key, temperature=0)


def invoke_structured(
    model_env: str,
    default_model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
) -> tuple[Optional[T], Optional[str]]:
    """Returns (parsed_result, error_message)."""
    llm = get_chat_model(model_env, default_model)
    if llm is None:
        return None, "GROQ_API_KEY not configured"
    try:
        structured = llm.with_structured_output(schema)
        result = structured.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return result, None
    except Exception as exc:
        return None, str(exc)


def invoke_json_prompt(
    model_env: str,
    default_model: str,
    system_prompt: str,
    user_prompt: str,
) -> tuple[Optional[dict], Optional[str]]:
    """Plain JSON response fallback when structured output fails."""
    llm = get_chat_model(model_env, default_model)
    if llm is None:
        return None, "GROQ_API_KEY not configured"
    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt + " Respond with valid JSON only."),
                HumanMessage(content=user_prompt),
            ]
        )
        text = response.content if hasattr(response, "content") else str(response)
        text = str(text).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text), None
    except Exception as exc:
        return None, str(exc)
