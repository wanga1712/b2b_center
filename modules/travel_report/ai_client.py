"""Клиент для переписывания текста через OpenRouter."""

from __future__ import annotations

import json
import os
from typing import Optional

import requests
from loguru import logger

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEBUG_LOG_PATH = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"


def _append_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    """Записать отладочную строку в NDJSON-лог (debug mode)."""
    # region agent log
    payload = {
        "sessionId": "debug-session",
        "runId": "openrouter-run",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": __import__("time").time(),
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Логирование не должно ломать основной поток
        pass
    # endregion


def rewrite_text(text: str) -> str:
    """
    Переписать текст деловым стилем через OpenRouter.

    Токен ожидается в переменной окружения OPENROUTER_API_KEY.
    """
    api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Не задан OPENROUTER_API_KEY в окружении")

    # Выбор модели: из окружения или значение по умолчанию
    model_name = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
    try:
        max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "400"))
    except ValueError:
        max_tokens = 400

    prompt = (
        "Перепиши текст грамотно с точки зрения фонетики и пунктуации, "
        "улучи подачу в деловом стиле, соблюдая международные правила "
        "корпоративной переписки. Сохрани фактический смысл.\n\n"
        f"Текст:\n{text}"
    )

    payload = {
        "model": model_name,
        "messages": [
        {"role": "system", "content": "You are a professional business copy editor."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    _append_debug_log(
        "H1",
        "ai_client.py:rewrite_text:before_request",
        "Подготовка запроса к OpenRouter",
        {"text_len": len(text), "model": payload["model"], "max_tokens": max_tokens},
    )

    try:
        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30)
        _append_debug_log(
            "H2",
            "ai_client.py:rewrite_text:after_request",
            "Ответ от OpenRouter получен",
            {"status": response.status_code, "body_len": len(response.text or "")},
        )

        response.raise_for_status()
        data = response.json() if response.text else {}
        choices = data.get("choices", [])
        _append_debug_log(
            "H3",
            "ai_client.py:rewrite_text:after_json",
            "Распарсен JSON ответа",
            {
                "has_choices": bool(choices),
                "choices_len": len(choices),
                "keys": list(data.keys()) if isinstance(data, dict) else [],
            },
        )

        choice = choices[0] if choices else {}
        message = choice.get("message", {})
        raw_content = message.get("content")

        # Поддержка разных форматов контента: строка или список сегментов
        content: Optional[str] = None
        if isinstance(raw_content, str):
            content = raw_content.strip()
        elif isinstance(raw_content, list):
            parts: list[str] = []
            for part in raw_content:
                if isinstance(part, dict):
                    text_part = part.get("text") or part.get("content")
                    if isinstance(text_part, str) and text_part.strip():
                        parts.append(text_part.strip())
            if parts:
                content = " ".join(parts)

        _append_debug_log(
            "H3b",
            "ai_client.py:rewrite_text:content_parsed",
            "Распознан формат контента",
            {
                "raw_type": type(raw_content).__name__,
                "is_str": isinstance(raw_content, str),
                "is_list": isinstance(raw_content, list),
                "resolved_len": len(content) if content else 0,
            },
        )

        if not content:
            raise ValueError("Пустой ответ от модели OpenRouter. Проверьте ключ и лимиты.")

        _append_debug_log(
            "H4",
            "ai_client.py:rewrite_text:success",
            "Получен переписанный текст",
            {"result_len": len(content)},
        )
        return content.strip()
    except Exception as error:
        try:
            logger.error(f"OpenRouter error: {error}")
            if "response" in locals():
                logger.error(f"Status: {response.status_code}, body: {response.text}")
            _append_debug_log(
                "H5",
                "ai_client.py:rewrite_text:error",
                "Ошибка при обращении к OpenRouter",
                {"error_type": type(error).__name__, "error_msg": str(error)},
            )
        finally:
            raise


