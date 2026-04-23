import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from urllib.parse import parse_qsl, unquote_plus

# ===================== НАСТРОЙКИ =====================
app = FastAPI(title="PX Models API")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8313221258:AAG9XsV4y1fJ-z5tpccc9t9eesJRzXMhpwI")
ADMIN_USER_ID = 1423028519

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "data.json"
INDEX_FILE = BASE_DIR / "index.html"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ===================== CLOUDINARY =====================
import cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ===================== ВАЛИДАЦИЯ INIT DATA =====================
def validate_init_data(init_data: str):
    try:
        init_data = unquote_plus(init_data)
        data_dict = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = data_dict.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(sorted(f"{k}={v}" for k, v in data_dict.items()))
        secret_key = hmac_new(key=b"WebAppData", msg=BOT_TOKEN.encode(), digestmod=sha256).digest()
        calculated_hash = hmac_new(key=secret_key, msg=data_check_string.encode(), digestmod=sha256).hexdigest()

        if not compare_digest(calculated_hash, received_hash):
            return None

        if "user" in data_dict:
            data_dict["user"] = json.loads(data_dict["user"])
        return data_dict
    except Exception:
        return None

# ===================== ДАННЫЕ =====================
def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"models": []}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

app_data = load_data()

# ===================== РОУТЕРЫ =====================
from routers.admin import router as admin_router
app.include_router(admin_router)

# ===================== СТАТИКА =====================
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ===================== ОСНОВНЫЕ РОУТЫ =====================
@app.get("/", response_class=HTMLResponse)
async def serve_webapp():
    if not INDEX_FILE.exists():
        return HTMLResponse("<h1 style='color:red;text-align:center;margin-top:100px;'>index.html not found</h1>", 404)
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

@app.get("/api/models")
async def get_models(page: int = 1, limit: int = 50, search: str = None):
    items = app_data["models"]
    if search:
        s = search.lower()
        items = [m for m in items if s in str(m.get("name_ru", "")).lower()]
    start = (page - 1) * limit
    return {
        "items": items[start:start + limit],
        "total": len(items),
        "page": page
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
