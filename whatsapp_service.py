import os
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Query, Response, HTTPException
from pydantic import BaseModel
from engine.legal_advisor import LegalAdvisor
from drafting.notice_generator import NoticeGenerator

app = FastAPI(
    title="QanoonSahulat WhatsApp & Messaging Service",
    description="FastAPI service for WhatsApp Business Cloud API & SMS bot integration providing Urdu-First legal guidance.",
    version="1.0.0"
)

# Initialize Legal Advisor and Generator
advisor = LegalAdvisor()
generator = NoticeGenerator()

VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "qanoon_sahulat_verify_token_2026")

class MessageSimulationRequest(BaseModel):
    phone: str = "+923001234567"
    message: str
    language: Optional[str] = "roman_urdu"
    city: Optional[str] = "Lahore"

class MessageSimulationResponse(BaseModel):
    status: str
    reply_text: str
    recommended_template: Optional[str]
    citations: list

@app.get("/")
def home():
    return {
        "service": "QanoonSahulat Legal Bot API",
        "status": "active",
        "description": "Urdu-first Pakistani legal rights and statutory notice generation service.",
        "endpoints": {
            "webhook_get": "/webhook (Meta Verification)",
            "webhook_post": "/webhook (Incoming WhatsApp Messages)",
            "simulate": "/simulate (Interactive Testing Sandbox)"
        }
    }

@app.get("/webhook")
def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """
    Webhook verification for Meta WhatsApp Cloud API.
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """
    Receives incoming webhook payloads from Meta WhatsApp Cloud API.
    Processes user query and sends response.
    """
    body = await request.json()
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        from_phone = msg.get("from")
        msg_type = msg.get("type")

        user_text = ""
        if msg_type == "text":
            user_text = msg.get("text", {}).get("body", "")
        elif msg_type == "audio":
            # For voice notes, in production this would fetch audio bytes & pass to Gemini / Whisper
            user_text = "Voice note received: Transcription in progress..."

        if user_text:
            advice = advisor.advise(user_text, language="roman_urdu")
            reply = advice.get("answer", "")
            # In live production: Send payload via requests.post to https://graph.facebook.com/v20.0/{phone_number_id}/messages
            return {"status": "processed", "recipient": from_phone, "reply_length": len(reply)}

    except Exception as e:
        print(f"Error handling WhatsApp webhook: {e}")
        return {"status": "error", "error": str(e)}

    return {"status": "ignored"}

@app.post("/simulate", response_model=MessageSimulationResponse)
def simulate_whatsapp_message(req: MessageSimulationRequest):
    """
    Interactive test endpoint to simulate a citizen texting the WhatsApp Bot.
    Works immediately without requiring a live Meta Cloud developer account.
    """
    advice = advisor.advise(req.message, language=req.language or "roman_urdu", city=req.city)

    return MessageSimulationResponse(
        status="success",
        reply_text=advice.get("answer", ""),
        recommended_template=advice.get("recommended_template"),
        citations=advice.get("citations", [])
    )
