# telegram_ai_autoresponder

An automatic Telegram responder using FastAPI and Telethon, powered by OpenRouter (LLM API) to generate contextual replies in chats.

## 📌 Features

- Asynchronous Telegram client via Telethon.
- Autoreply support using OpenRouter LLM.
- Prompt building from latest messages in chat.
- REST API to view chat list, message history, and manually send messages.
- Ignores outgoing messages, duplicates, and unauthorized chats.
- Clears processed message cache every 5 minutes.

## 🔐 Security

- Replies are generated **only** for authorized chats listed in `allowed_chat_prompts`.
- Each chat can have a custom prompt style (e.g., tone, personality).

## 📡 API Endpoints

| Method | Path             | Description                        |
|--------|------------------|------------------------------------|
| GET    | `/chats`         | Get list of chats                  |
| GET    | `/chat_history`  | Get recent messages from a chat    |
| POST   | `/send_message`  | Send a message manually            |

## 🧠 Technologies Used

- **FastAPI** — HTTP server
- **Telethon** — Telegram client
- **aiohttp** — HTTP client for OpenRouter
- **OpenRouter API** — Text generation (LLM)

## 📄 License

This project is licensed under the MIT License.
