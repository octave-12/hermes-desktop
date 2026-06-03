"""
Text-to-Speech Service for Hermes Desktop
Uses edge-tts (free, no API key needed) for Chinese voice synthesis.
"""
import asyncio
import hashlib
import os
import time
from pathlib import Path

# TTS cache directory
TTS_CACHE_DIR = Path.home() / ".hermes" / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

AVAILABLE = False

# Import edge-tts with a timeout to avoid hanging on first import
try:
    # Test basic import
    import edge_tts as _edge_tts
    # Test that communicate class works (this caches voice data)
    _edge_tts.Communicate
    AVAILABLE = True
    print("[TTS] edge-tts loaded successfully")
except ImportError:
    print("[TTS] edge-tts not installed. Run: pip install edge-tts")
except Exception as e:
    print(f"[TTS] edge-tts init error (will retry at runtime): {e}")


async def text_to_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> str | None:
    """
    Convert text to speech, return path to audio file.
    
    Args:
        text: Text to convert (max 2000 chars)
        voice: Edge TTS voice name
    
    Returns:
        Path to generated MP3, or None on failure
    """
    if not text or not text.strip():
        return None

    text = text.strip()[:2000]
    
    cache_key = hashlib.md5(f"{voice}:{text}".encode()).hexdigest()
    cache_path = TTS_CACHE_DIR / f"{cache_key}.mp3"

    # Return cached version if exists
    if cache_path.exists():
        return str(cache_path)

    try:
        communicate = _edge_tts.Communicate(text, voice)
        await asyncio.wait_for(
            communicate.save(str(cache_path)),
            timeout=30.0  # 30s timeout for TTS generation
        )
        return str(cache_path)
    except asyncio.TimeoutError:
        print(f"[TTS] Timeout generating speech (text length: {len(text)})")
        return None
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return None


async def get_available_voices() -> list[dict]:
    """Get list of available TTS voices."""
    if not AVAILABLE:
        return []

    try:
        voices = await asyncio.wait_for(
            _edge_tts.list_voices(),
            timeout=10.0
        )
        return [
            {
                "name": v["Name"],
                "short_name": v["ShortName"],
                "locale": v["Locale"],
                "gender": v["Gender"],
            }
            for v in voices
        ]
    except Exception as e:
        print(f"[TTS] Failed to list voices: {e}")
        return []
