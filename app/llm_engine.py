"""LLM 引擎 —— 对接 Ollama（优先）和 OpenAI 兼容接口."""

import json
import os
import re
from typing import Any

import requests

# ── 配置（可通过 configure() 或环境变量覆盖） ──────────────────────

config: dict[str, Any] = {
    "api": os.getenv("FLUENT_AGENT_LLM_API", "ollama"),
    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "ollama_model": os.getenv("OLLAMA_MODEL", "llama3"),
    "openai_api_key": os.getenv("OPENAI_API_KEY", "").strip(),
    "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "timeout": int(os.getenv("FLUENT_AGENT_TIMEOUT", "300")),
}


def configure(**kwargs: Any) -> None:
    """批量覆盖配置项。"""
    config.update(kwargs)


# ── 底层调用 ──────────────────────────────────────────────────────

def _chat_ollama(messages: list[dict]) -> str:
    resp = requests.post(
        f"{config['ollama_base_url']}/api/chat",
        json={
            "model": config["ollama_model"],
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": 2048,
                "temperature": 0.3,
            },
        },
        timeout=config["timeout"],
    )
    resp.raise_for_status()
    msg = resp.json()["message"]
    return msg.get("content") or msg.get("thinking", "")


def _chat_openai(messages: list[dict]) -> str:
    # 延迟导入，避免未安装 openai 包时崩溃
    from openai import OpenAI  # type: ignore

    client = OpenAI(
        api_key=config["openai_api_key"],
        base_url=config["openai_base_url"],
        timeout=config["timeout"],
    )
    completion = client.chat.completions.create(
        model=config["openai_model"],
        messages=messages,
        temperature=0.3,
    )
    return completion.choices[0].message.content or ""


def _chat(messages: list[dict]) -> str:
    if config["api"] == "openai":
        return _chat_openai(messages)
    return _chat_ollama(messages)


# ── 核心翻译 + 生词提取 ───────────────────────────────────────────

TRANSLATE_SYSTEM_PROMPT = """\
You are a professional language-learning assistant. Your job:
1. Translate the user's text into {target_lang}.
2. Pick 3-5 key words or phrases from the ORIGINAL text that are worth learning.
3. For each word/phrase, give its translation into {target_lang} and a natural, \
idiomatic example sentence in the original language.

Return ONLY valid JSON (no markdown fences, no extra text):
{{
  "translation": "<full translation>",
  "words": [
    {{"word": "<original word/phrase>", "translation": "<meaning>", "example": "<natural sentence>"}},
    ...
  ]
}}"""


def translate_and_extract(
    text: str,
    source_lang: str = "auto",
    target_lang: str = "zh",
) -> dict:
    """翻译文本并提取 3-5 个建议学习的生词。

    Returns:
        {"translation": str, "words": [{"word": str, "translation": str, "example": str}, ...]}
    """
    messages = [
        {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT.format(target_lang=target_lang)},
        {"role": "user", "content": text},
    ]

    raw = _chat(messages)
    return _parse_response(raw)


# ── 场景对话 ────────────────────────────────────────────────────────

CONVERSATION_SYSTEM_PROMPT = """\
You are a language-learning conversation partner.

Role: {role}
Scenario: {scenario}
Target language: {target_lang}

Rules:
1. Stay in character and respond naturally in {target_lang}.
2. Keep your response at an intermediate difficulty level (B1-B2).
3. Your response should be 2-4 sentences — concise and conversational.
4. After your response, correct any grammar, vocabulary, or phrasing mistakes
   the learner made. If their message was perfect, leave <corrections> empty.

You MUST reply in this EXACT XML format (no markdown fences, no extra text):

<response>
Your in-character reply in {target_lang}. Keep it 2-4 sentences.
</response>
<corrections>
<item>
  <original>learner's exact error phrase</original>
  <corrected>the corrected version</corrected>
  <explanation>brief explanation in Chinese</explanation>
</item>
</corrections>"""


def converse(
    user_message: str,
    role: str,
    scenario: str,
    target_lang: str = "en",
    history: list[dict] | None = None,
) -> dict:
    """生成场景对话回复，含纠错反馈。

    Returns:
        {"response": str, "corrections": [{"original": str, "corrected": str, "explanation": str}]}
    """
    messages: list[dict] = [
        {
            "role": "system",
            "content": CONVERSATION_SYSTEM_PROMPT.format(
                role=role,
                scenario=scenario,
                target_lang=target_lang,
            ),
        },
    ]

    if history:
        for h in history[-10:]:  # Keep last 10 exchanges for context
            role_tag = "assistant" if h["role"] == "assistant" else "user"
            content = h["content"]
            if h["role"] == "assistant" and h.get("corrections"):
                # Strip corrections from assistant history to keep prompt clean
                content = content
            messages.append({"role": role_tag, "content": content})

    messages.append({"role": "user", "content": user_message})

    raw = _chat(messages)
    return _parse_conversation_response(raw)


def _parse_conversation_response(raw: str) -> dict:
    """Parse XML-format conversation response, with multiple fallbacks."""
    response = _extract_tag(raw, "response")
    corrections = _extract_corrections_xml(raw)

    if response:
        return {"response": response, "corrections": corrections}

    # Fallback: try old JSON format for backward compatibility
    try:
        data = json.loads(raw)
        return _normalize_conversation(data)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            data = json.loads(match.group(1))
            return _normalize_conversation(data)
        except json.JSONDecodeError:
            pass

    # Last resort: return raw text as response
    return {"response": raw, "corrections": []}


def _extract_tag(text: str, tag: str) -> str:
    """Extract content from XML-style tag. Returns empty string if not found."""
    pattern = rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _extract_corrections_xml(raw: str) -> list[dict]:
    """Extract correction <item> blocks from XML."""
    items = []
    # Match each <item>...</item> block
    item_pattern = re.compile(r"<item>\s*([\s\S]*?)\s*</item>", re.DOTALL)
    for item_match in item_pattern.finditer(raw):
        block = item_match.group(1)
        original = _extract_tag(block, "original")
        corrected = _extract_tag(block, "corrected")
        explanation = _extract_tag(block, "explanation")
        if original:
            items.append({
                "original": original,
                "corrected": corrected,
                "explanation": explanation,
            })
    return items


def _normalize_conversation(data: dict) -> dict:
    response = str(data.get("response", ""))
    raw_corrections = data.get("corrections", [])
    if not isinstance(raw_corrections, list):
        raw_corrections = []

    corrections = []
    for c in raw_corrections:
        if not isinstance(c, dict):
            continue
        original = str(c.get("original", "")).strip()
        if not original:
            continue
        corrections.append(
            {
                "original": original,
                "corrected": str(c.get("corrected", "")).strip(),
                "explanation": str(c.get("explanation", "")).strip(),
            }
        )

    return {"response": response, "corrections": corrections}


def _parse_response(raw: str) -> dict:
    # 尝试直接解析 JSON
    try:
        data = json.loads(raw)
        return _normalize(data)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取 JSON
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            data = json.loads(match.group(1))
            return _normalize(data)
        except json.JSONDecodeError:
            pass

    # 回退：返回原始文本作为翻译，无生词
    return {"translation": raw, "words": []}


def _normalize(data: dict) -> dict:
    translation = str(data.get("translation", ""))
    raw_words = data.get("words", [])
    if not isinstance(raw_words, list):
        raw_words = []

    words = []
    for w in raw_words:
        if not isinstance(w, dict):
            continue
        word = str(w.get("word", "")).strip()
        if not word:
            continue
        words.append(
            {
                "word": word,
                "translation": str(w.get("translation", "")).strip(),
                "example": str(w.get("example", "")).strip(),
            }
        )

    return {"translation": translation, "words": words[:5]}
