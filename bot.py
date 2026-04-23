import os
import json
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from urllib.parse import parse_qsl, unquote_plus

app = FastAPI(title="PX Models — Telegram WebApp")

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
CHANNEL_LINK = "https://t.me/+u8svaG24-xo5MDMy"   # ← ваш приватный канал

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "data.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

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
    data = validate_init_data(init_data_str)
    return data and data.get("user", {}).get("id") == ADMIN_USER_ID

# ===================== ДАННЫЕ =====================
def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"models": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app_data = load_data()

# ===================== СТАТИКА =====================
if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ===================== СЕРВИС =====================
@app.get("/", response_class=HTMLResponse)
async def serve_webapp():
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1 style='color:red;text-align:center;margin-top:100px;'>index.html not found</h1>", 404)
    return HTMLResponse(index_path.read_text(encoding="utf-8"))

@app.get("/api/check_admin")
async def check_admin(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return {"is_admin": is_admin(init_data)}

# ===================== МОДЕЛИ =====================
@app.get("/api/models")
async def get_models(page: int = Query(1, ge=1), limit: int = Query(200, ge=1, le=500), search: str = Query(None)):
    items = app_data["models"]
    if search:
        s = search.lower()
        items = [m for m in items if s in str(m.get("name_ru", "")).lower() or s in str(m.get("hashtags", "")).lower()]
    total = len(items)
    start = (page - 1) * limit
    return {
        "items": items[start:start + limit],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@app.post("/api/models")
async def add_model(
    initData: str = Form(...),
    name_ru: str = Form(...),
    hashtags: str = Form(""),
    cover: UploadFile = File(...)
):
    if not is_admin(initData):
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    # Загрузка обложки
    contents = await cover.read()
    result = cloudinary.uploader.upload(
        contents,
        resource_type="image",
        folder="pornoxram",
        use_filename=True,
        unique_filename=True,
        transformation=[{"width": 1200, "crop": "limit"}, {"quality": "auto"}]
    )
    cover_url = result["secure_url"]

    new_id = max((m.get("id", 0) for m in app_data["models"]), default=0) + 1

    model = {
        "id": new_id,
        "name_ru": name_ru.strip(),
        "hashtags": hashtags.strip(),
        "cover_url": cover_url,
        "media": []
    }

    app_data["models"].append(model)
    save_data(app_data)

    return {"success": True, "id": new_id, "message": "Модель добавлена и готова к использованию в канале"}

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int, request: Request):
    if not is_admin(request.headers.get("X-Telegram-Init-Data", "")):
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    original_len = len(app_data["models"])
    app_data["models"] = [m for m in app_data["models"] if m["id"] != model_id]

    if len(app_data["models"]) == original_len:
        raise HTTPException(status_code=404, detail="Модель не найдена")

    save_data(app_data)
    return {"success": True, "message": f"Модель {model_id} удалена"}
