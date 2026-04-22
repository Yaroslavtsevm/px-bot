import os
import json
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cloudinary
import cloudinary.uploader
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from urllib.parse import parse_qsl, unquote_plus

app = FastAPI(title="PornoXram API")

# ===================== CLOUDINARY =====================
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8313221258:AAG9XsV4y1fJ-z5tpccc9t9eesJRzXMhpwI")
ADMIN_USER_ID = 1423028519

DATA_FILE = Path("data/data.json")
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ===================== ВАЛИДАЦИЯ INIT DATA =====================
def validate_init_data(init_data: str) -> dict | None:
    try:
        init_data = unquote_plus(init_data)
        data_dict = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = data_dict.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(sorted(f"{key}={value}" for key, value in data_dict.items()))

        secret_key = hmac_new(key=b"WebAppData", msg=BOT_TOKEN.encode(), digestmod=sha256).digest()
        calculated_hash = hmac_new(key=secret_key, msg=data_check_string.encode(), digestmod=sha256).hexdigest()

        if not compare_digest(calculated_hash, received_hash):
            return None

        if "user" in data_dict:
            data_dict["user"] = json.loads(data_dict["user"])
        return data_dict
    except Exception:
        return None

def is_admin(init_data_str: str) -> bool:
    user_data = validate_init_data(init_data_str)
    if not user_data or "user" not in user_data:
        return False
    return user_data["user"].get("id") == ADMIN_USER_ID

# ===================== ДАННЫЕ =====================
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"models": [], "categories": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app_data = load_data()

# ===================== API =====================
@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/api/check_admin")
async def check_admin(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    return {"is_admin": bool(init_data) and is_admin(init_data)}

@app.get("/api/models")
async def get_models():
    return app_data["models"]

@app.get("/api/categories")
async def get_categories():
    return app_data["categories"]

# ===================== ЗАГРУЗКА В CLOUDINARY =====================
async def upload_to_cloudinary(file: UploadFile, resource_type: str = "auto"):
    """Загружает файл в Cloudinary и возвращает secure_url"""
    result = cloudinary.uploader.upload(
        file.file,
        resource_type=resource_type,   # auto / image / video
        folder="pornoxram",
        use_filename=True,
        unique_filename=True
    )
    return result["secure_url"]

# === МОДЕЛИ ===
@app.post("/api/models")
async def add_model(
    initData: str = Form(...),
    name_ru: str = Form(...),
    name_en: str = Form(...),
    cover: UploadFile = File(...)
):
    if not is_admin(initData):
        raise HTTPException(403, "Доступ запрещён")

    cover_url = await upload_to_cloudinary(cover, resource_type="image")

    new_id = max((m["id"] for m in app_data["models"]), default=0) + 1

    model = {
        "id": new_id,
        "name_ru": name_ru,
        "name_en": name_en,
        "cover_url": cover_url,
        "media": []
    }
    app_data["models"].append(model)
    save_data(app_data)
    return {"success": True, "id": new_id}

@app.post("/api/models/{model_id}/media")
async def add_media_to_model(
    model_id: int,
    initData: str = Form(...),
    type: str = Form(...),                    # "photo" или "video"
    description_ru: str = Form(""),
    description_en: str = Form(""),
    file: UploadFile = File(...)
):
    if not is_admin(initData):
        raise HTTPException(403, "Доступ запрещён")

    model = next((m for m in app_data["models"] if m["id"] == model_id), None)
    if not model:
        raise HTTPException(404, "Модель не найдена")

    resource_type = "video" if type == "video" else "image"
    url = await upload_to_cloudinary(file, resource_type=resource_type)

    media_item = {
        "id": len(model["media"]) + 1,
        "type": type,
        "url": url,
        "description_ru": description_ru,
        "description_en": description_en
    }
    model["media"].append(media_item)
    save_data(app_data)
    return {"success": True}

# === КАТЕГОРИИ ===
@app.post("/api/categories")
async def add_category(initData: str = Form(...), hashtag: str = Form(...)):
    if not is_admin(initData):
        raise HTTPException(403, "Доступ запрещён")

    new_id = max((c["id"] for c in app_data["categories"]), default=0) + 1

    cat = {"id": new_id, "hashtag": hashtag, "media": []}
    app_data["categories"].append(cat)
    save_data(app_data)
    return {"success": True, "id": new_id}

@app.post("/api/categories/{cat_id}/media")
async def add_media_to_category(
    cat_id: int,
    initData: str = Form(...),
    type: str = Form(...),
    description_ru: str = Form(""),
    description_en: str = Form(""),
    file: UploadFile = File(...)
):
    if not is_admin(initData):
        raise HTTPException(403, "Доступ запрещён")

    cat = next((c for c in app_data["categories"] if c["id"] == cat_id), None)
    if not cat:
        raise HTTPException(404, "Категория не найдена")

    resource_type = "video" if type == "video" else "image"
    url = await upload_to_cloudinary(file, resource_type=resource_type)

    media_item = {
        "id": len(cat["media"]) + 1,
        "type": type,
        "url": url,
        "description_ru": description_ru,
        "description_en": description_en
    }
    cat["media"].append(media_item)
    save_data(app_data)
    return {"success": True}

# Удаление (пока только из базы, файлы в Cloudinary остаются)
@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int, request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not is_admin(init_data):
        raise HTTPException(403)
    app_data["models"] = [m for m in app_data["models"] if m["id"] != model_id]
    save_data(app_data)
    return {"success": True}

@app.delete("/api/categories/{cat_id}")
async def delete_category(cat_id: int, request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not is_admin(init_data):
        raise HTTPException(403)
    app_data["categories"] = [c for c in app_data["categories"] if c["id"] != cat_id]
    save_data(app_data)
    return {"success": True}

# ===================== ЗАПУСК =====================
if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
