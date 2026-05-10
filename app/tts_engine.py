"""TTS 引擎 —— Edge-TTS（默认）+ GPT-SoVITS 双后端."""

import asyncio
import os
import tempfile
from typing import Any

import edge_tts

config: dict[str, Any] = {
    "api": os.getenv("FLUENT_AGENT_TTS_API", "edge-tts"),
    "edge_tts_voice_en": os.getenv("EDGE_TTS_VOICE_EN", "en-US-AriaNeural"),
    "edge_tts_voice_ja": os.getenv("EDGE_TTS_VOICE_JA", "ja-JP-NanamiNeural"),
    "edge_tts_voice_zh": os.getenv("EDGE_TTS_VOICE_ZH", "zh-CN-XiaoxiaoNeural"),
    "gpt_sovits_url": os.getenv("GPT_SOVITS_URL", "http://localhost:9880"),
    "gpt_sovits_ref_audio": os.getenv(
        "GPT_SOVITS_REF_AUDIO", r"E:\work\GPT-SoVITS-Work\录音.wav"
    ),
    "gpt_sovits_prompt_lang": os.getenv("GPT_SOVITS_PROMPT_LANG", "zh"),
}

LANG_VOICE_MAP: dict[str, str] = {
    "en": config["edge_tts_voice_en"],
    "ja": config["edge_tts_voice_ja"],
    "zh": config["edge_tts_voice_zh"],
}


def configure(**kwargs: Any) -> None:
    config.update(kwargs)
    LANG_VOICE_MAP["en"] = config["edge_tts_voice_en"]
    LANG_VOICE_MAP["ja"] = config["edge_tts_voice_ja"]
    LANG_VOICE_MAP["zh"] = config["edge_tts_voice_zh"]


FALLBACK_VOICES: dict[str, str] = {
    "en": "en-US-AriaNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ko": "ko-KR-SunHiNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
}


def _get_edge_tts_voice(lang: str) -> str:
    if lang in LANG_VOICE_MAP:
        return LANG_VOICE_MAP[lang]
    for prefix in FALLBACK_VOICES:
        if lang.startswith(prefix):
            return FALLBACK_VOICES[prefix]
    return config["edge_tts_voice_en"]


def synthesize_edge_tts(text: str, lang: str = "en") -> bytes:
    """Edge-TTS 合成，返回 MP3 bytes。"""

    async def _run() -> bytes:
        voice = _get_edge_tts_voice(lang)
        communicate = edge_tts.Communicate(text, voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    return asyncio.run(_run())


def synthesize(text: str, lang: str = "en") -> bytes:
    """合成语音，返回 MP3 bytes。"""
    if config["api"] == "edge-tts":
        return synthesize_edge_tts(text, lang)
    raise RuntimeError(f"Unknown TTS API: {config['api']}")


def list_edge_tts_voices() -> list[dict]:
    """列出常用的 Edge-TTS 音色选项。"""

    async def _run() -> list[dict]:
        voices = await edge_tts.VoicesManager.create()
        return [
            {"ShortName": v["ShortName"], "Locale": v["Locale"], "Gender": v["Gender"]}
            for v in voices.voices
            if v["ShortName"].startswith(("en-", "ja-"))
        ]

    return asyncio.run(_run())
