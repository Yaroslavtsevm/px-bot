import asyncio
import logging
import json
from urllib.parse import quote

import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, WebAppData
)
from aiogram.utils.web_app import safe_parse_webapp_init_data
from aiohttp import web

# ====================== НАСТРОЙКИ ======================
BOT_TOKEN = "6162146726:AAGjWYQlcPXXp4sdh5BkfIRCiHDhBqNaTFs"                    # ← Замени!
PERSONAL_USERNAME = "PX_MrM"              # ← твой ник без @
ADMIN_USER_ID = 1423028519                        # ← твой Telegram ID

DB_NAME = "database.db"
WEBAPP_URL = "https://px-only.onrender.com/static/index.html"   # ← Замени после деплоя!

logging.basicConfig(level=logging.INFO)

# ====================== БАЗА ДАННЫХ ======================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Звёзды
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                hashtag TEXT UNIQUE,
                photo_url TEXT,
                description TEXT
            )
        """)
        # Категории
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        # Обычный контент
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                file_id TEXT NOT NULL,
                caption TEXT,
                star_id INTEGER,
                category_id INTEGER,
                FOREIGN KEY(star_id) REFERENCES stars(id),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        """)
        # Платный контент
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paid_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                file_id TEXT NOT NULL,
                caption TEXT
            )
        """)
        # Анонимные комментарии
        await db.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                text TEXT NOT NULL,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


# ====================== WEBAPP API ======================
async def api_handler(request, table_name):
    try:
        data = await request.post()
        safe_parse_webapp_init_data(token=BOT_TOKEN, init_data=data.get("_auth"))
    except Exception:
        return web.json_response({"error": "Unauthorized"}, status=401)

    async with aiosqlite.connect(DB_NAME) as db:
        if table_name == "stars":
            async with db.execute("SELECT id, name, hashtag, photo_url FROM stars ORDER BY name") as cur:
                items = [dict(id=r[0], name=r[1], hashtag=r[2], photo_url=r[3]) async for r in cur]
        elif table_name == "categories":
            async with db.execute("SELECT id, name FROM categories ORDER BY name") as cur:
                items = [dict(id=r[0], name=r[1]) async for r in cur]
        elif table_name == "paid":
            async with db.execute("SELECT id, type, file_id, caption FROM paid_content") as cur:
                items = [dict(id=r[0], type=r[1], file
