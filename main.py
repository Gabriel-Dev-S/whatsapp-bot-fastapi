import os

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "SEU_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "SEU_WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "SEU_PHONE_NUMBER_ID")

GRAPH_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

app = FastAPI(title="WhatsApp Bot", version="0.1.0")


async def send_whatsapp_message(to_phone: str, message_text: str) -> dict:
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": message_text},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(GRAPH_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            print(f"Graph API error {exc.response.status_code}: {exc.response.text}")
        except httpx.HTTPError as exc:
            print(f"Failed to send WhatsApp message: {exc}")

    return {"status": "error"}


def extract_message(payload: dict) -> tuple:
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        message = value["messages"][0]
        from_phone = message["from"]
        message_text = message["text"]["body"]
        return from_phone, message_text
    except (KeyError, IndexError, TypeError):
        return None, None


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Invalid verification token")


@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()

    from_phone, message_text = extract_message(payload)

    if from_phone and message_text:
        await send_whatsapp_message(from_phone, f"Recebi: {message_text}")

    return JSONResponse(content={"status": "success"}, status_code=200)
