import os
import pytest
from telegram import Bot
from telegram.request import HTTPXRequest
import httpx

async def get_telegram_response():
    url = "https://telegram-gpt-14zy.onrender.com/webhook"
    payload = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {
                "id": 1160346964,
                "is_bot": False,
                "first_name": "John",
                "username": "johndoe",
                "language_code": "en"
            },
            "chat": {
                "id": 67890,
                "first_name": "John",
                "username": "johndoe",
                "type": "private"
            },
            "date": 1634239084,
            "text": "Explain the theory of relativity in simple terms"
        }
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        response = await client.post(url, json=payload)
        return response

@pytest.mark.asyncio
async def test_telegram_response():
    response = await get_telegram_response()
    assert response.status_code == 200
