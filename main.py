from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
from telethon.sync import TelegramClient, events
from telethon.tl.types import User, Chat
from telethon.tl.custom.message import Message
import asyncio
import aiohttp
import json

app = FastAPI()

# Конфигурация
api_id = 123456
api_hash = '123456'
OPENROUTER_API_KEY = "sk-or-v1-784..."

client = TelegramClient("session4", api_id, api_hash)
processed_messages = set()
handler_call_count = 0  

allowed_chat_prompts = {
  123456789: "Behave normally, respond politely" # telegram chat ID and prompt for behavior in chat
}

class MessageItem(BaseModel):
    id: int
    sender_id: int
    text: str
    date: str

class SendMessageRequest(BaseModel):
    chat_id: int
    text: str

async def get_openrouter_response(prompt):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "Secure Neural Chat",
        }

        payload = {
            #"model": "google/gemma-3-4b-it:free",
            "model": "tencent/hunyuan-a13b-instruct:free",
            "messages": prompt,
            "temperature": 0.7
        }

        try:
            async with session.post("https://openrouter.ai/api/v1/chat/completions",
                                    headers=headers, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"API error {response.status}: {await response.text()}")

                result = await response.json()
                print("API Response:", result)  

                if 'choices' not in result:
                    raise ValueError("Ответ API не содержит ключа 'choices'")

                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"❌ Ошибка при отправке запроса или обработке ответа: {e}")
            raise


async def build_prompt(chat_id: int, base_prompt: str):
    messages = await client.get_messages(chat_id, limit=30)
    messages = list(reversed(messages))

    dialog = [{"role": "system", "content": base_prompt}]
    for msg in messages:
        if not msg.text or not msg.text.strip():
            continue
        role = "assistant" if msg.out else "user"
        dialog.append({"role": role, "content": msg.text.strip()})

    if len(dialog) == 1:
        raise ValueError("Недостаточно текста в сообщениях для построения prompt")

    return dialog

async def cleanup_processed_messages():
    while True:
        await asyncio.sleep(300)
        processed_messages.clear()
        print("🧹 Множество processed_messages очищено")

# Обработчик событий
@client.on(events.NewMessage(incoming=True))
async def handler(event):
    global handler_call_count
    handler_call_count += 1
    print(f"🔄 Handler вызван #{handler_call_count}")

    if event.out:
        print("❌ Это исходящее сообщение — пропускаем")
        return

    myself = await client.get_me()
    if event.sender_id == myself.id:
        print("❌ Это моё сообщение — игнорируем")
        return

    chat_id = event.chat_id
    msg_id = event.message.id
    unique_key = (chat_id, msg_id)

    if unique_key in processed_messages:
        print(f"⚠️ Повторное сообщение {unique_key} — пропускаем")
        return
    processed_messages.add(unique_key)

    print(f"📩 Получено сообщение из чата {chat_id}, текст: {event.message.text}")

    if chat_id in allowed_chat_prompts:
        try:
            prompt = await build_prompt(chat_id, allowed_chat_prompts[chat_id])
            print("🧠 GPT prompt:", json.dumps(prompt, ensure_ascii=False, indent=2))

            gpt_response = await get_openrouter_response(prompt)
            await event.reply(gpt_response)
            print(f"✅ Ответ отправлен: {gpt_response}")
        except Exception as e:
            print(f"❌ Ошибка при генерации или отправке ответа: {e}")
    else:
        print(f"⛔️ Чат {chat_id} не найден в списке разрешённых — игнорируем")

@app.on_event("startup")
async def startup():
    await client.start()
    print("✅ Telethon клиент запущен")
    asyncio.create_task(cleanup_processed_messages())

@app.on_event("shutdown")
async def shutdown():
    await client.disconnect()
    print("⛔️ Telethon клиент остановлен")

@app.get("/chats")
async def get_chats():
    dialogs = await client.get_dialogs()
    result = []
    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, User) and not entity.bot:
            result.append({
                "id": entity.id,
                "name": entity.first_name,
                "username": entity.username
            })
        elif isinstance(entity, Chat):
            result.append({
                "id": entity.id,
                "name": entity.title,
                "username": None
            })
    return result

@app.get("/chat_history", response_model=List[MessageItem])
async def get_chat_history(chat_id: int = Query(...), limit: int = 20):
    messages = []
    async for message in client.iter_messages(chat_id, limit=limit):
        if not message.text:
            continue
        messages.append({
            "id": message.id,
            "sender_id": message.sender_id if message.sender_id else 0,
            "text": message.text,
            "date": message.date.isoformat()
        })
    return list(reversed(messages))

@app.post("/send_message")
async def send_message(request: SendMessageRequest):
    try:
        print(f"➡️ Сообщение отправляется: {request.text}")
        await client.send_message(request.chat_id, request.text)
        return {"status": "Сообщение успешно отправлено"}
    except Exception as e:
        return {"error": str(e)}
