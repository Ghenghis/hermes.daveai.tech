#!/usr/bin/env python3
"""
Phase 4 Task 4.1 — Azure Voice Gateway
FastAPI micro-service (port 8001) that handles:
  POST /tts   — text-to-speech for a given agent (returns audio/wav)
  POST /stt   — speech-to-text (accepts audio/wav, returns JSON transcript)
  GET  /voices — list agent voice assignments
"""
import io
import json
import os

import azure.cognitiveservices.speech as speechsdk
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

# ─── Voice assignments ────────────────────────────────────────────────────────

AGENT_VOICES = {
    "hermes1": {"voice": "en-GB-MaisieNeural",       "style": "customerservice", "rate": "1.0",  "pitch": "medium"},
    "hermes2": {"voice": "en-AU-CarlyNeural",         "style": "cheerful",        "rate": "1.1",  "pitch": "+10%"},
    "hermes3": {"voice": "en-KE-AsiliaNeural",        "style": "calm",            "rate": "0.95", "pitch": "medium"},
    "hermes4": {"voice": "en-US-TonyNeural",          "style": "empathetic",      "rate": "0.9",  "pitch": "medium"},
    "hermes5": {"voice": "en-US-ChristopherNeural",   "style": "serious",         "rate": "0.85", "pitch": "-10%"},
}

SPEECH_KEY    = os.environ.get("AZURE_SPEECH_KEY",    "")
SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "eastus")

app = FastAPI(title="Hermes Voice Gateway", version="1.0.0")


# ─── Models ───────────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    agent_id: str
    text: str
    voice_override: str = ""


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "hermes-voice-gateway"}


@app.get("/voices")
def list_voices():
    return {"agent_voices": AGENT_VOICES}


@app.post("/tts")
def text_to_speech(req: TTSRequest):
    """Return WAV audio for the given agent_id and text."""
    if req.agent_id not in AGENT_VOICES:
        raise HTTPException(400, f"Unknown agent_id '{req.agent_id}'")
    if not SPEECH_KEY:
        raise HTTPException(503, "AZURE_SPEECH_KEY not configured")

    vc = AGENT_VOICES[req.agent_id]
    voice = req.voice_override or vc["voice"]

    cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)

    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'
                   xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>
        <voice name='{voice}'>
            <mstts:express-as style='{vc["style"]}'>
                <prosody rate='{vc["rate"]}' pitch='{vc["pitch"]}'>
                    {_escape_xml(req.text)}
                </prosody>
            </mstts:express-as>
        </voice>
    </speak>"""

    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    result = synth.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise HTTPException(500, f"TTS failed: {result.reason}")

    return Response(content=result.audio_data, media_type="audio/wav")


@app.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = "en-US",
):
    """Transcribe uploaded WAV audio."""
    if not SPEECH_KEY:
        raise HTTPException(503, "AZURE_SPEECH_KEY not configured")

    raw = await audio.read()

    cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    cfg.speech_recognition_language = language

    stream = speechsdk.audio.PushAudioInputStream()
    stream.write(raw)
    stream.close()

    audio_cfg = speechsdk.audio.AudioConfig(stream=stream)
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_cfg)
    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return {"transcript": result.text, "language": language}
    if result.reason == speechsdk.ResultReason.NoMatch:
        return {"transcript": "", "language": language, "note": "no speech detected"}

    raise HTTPException(500, f"STT failed: {result.reason}")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _escape_xml(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
