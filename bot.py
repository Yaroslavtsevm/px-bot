import os
import json
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "8313221258:AAG9XsV4y1fJ-z5tpccc9t9eesJRzXMhpwI")
ADMIN_USER_ID = 1423028519

DATA_FILE = Path("data/data.json")
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ===================== ВАЛИДАЦИЯ =====================
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
    except:
        return None

def is_admin(init_data_str: str) -> bool:
    data = validate_init_data(init_data_str)
    return data and data.get("user", {}).get("id") == ADMIN_USER_ID

# ===================== CLOUDINARY HELPERS =====================
def get_public_id(url: str) -> str:
    try:
        parts = url.split("/upload/")
        if len(parts) > 1:
            path = parts[1].split("?")[0]
            if path.startswith("v"):
                path = "/".join(path.split("/")[1:])
            return path.rsplit(".", 1)[0]
        return url
    except:
        return url

async def delete_from_cloudinary(url: str, resource_type: str = "image"):
    if not url: return
    try:
        public_id = get_public_id(url)
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception as e:
        print(f"Cloudinary delete failed: {e}")

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"models": [], "categories": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app_data = load_data()

# ===================== ROUTES =====================
@app.get("/")
async def serve_webapp():
    return FileResponse("index.html")

@app.get("/api/check_admin")
async def check_admin(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    return {"is_admin": bool(init_data) and is_admin(init_data)}

@app.get("/api/models")
async def get_models(page: int = Query(1, ge=1), limit: int = Query(20), search: str = Query(None)):
    items = app_data["models"]
    if search:
        s = search.lower()
        items = [m for m in items if s in m.get("name_ru","").lower() or s in m.get("name_en","").lower()]
    total = len(items)
    start = (page-1)*limit
    return {"items": items[start:start+limit], "total": total, "page": page, "pages": (total + limit - 1) // limit}

@app.get("/api/categories")
async def get_categories(page: int = Query(1, ge=1), limit: int = Query(20), search: str = Query(None)):
    items = app_data["categories"]
    if search:
        s = search.lower()
        items = [c for c in items if s in c.get("hashtag","").lower()]
    total = len(items)
    start = (page-1)*limit
    return {"items": items[start:start+limit], "total": total, "page": page, "pages": (total + limit - 1) // limit}

async def upload_file(file: UploadFile, resource_type: str = "auto"):
    result = cloudinary.uploader.upload(
        file.file,
        resource_type=resource_type,
        folder="pornoxram",
        transformation=[{"width": 1200, "crop": "limit"}, {"quality": "auto", "fetch_format": "auto"}]
    )
    return result["secure_url"]

# Добавь остальные эндпоинты (add_model, add_media_to_model и т.д.) из предыдущей версии, они остались теми же.

# ... (вставь сюда все @app.post и @app.delete из предыдущего сообщения — они работают)

# ===================== ЗАПУСК =====================
# Render сам запускает uvicorn, этот блок не нужен
