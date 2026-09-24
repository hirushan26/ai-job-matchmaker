import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Read Gemini API key(s) from environment, geminiapikey.txt, and sibling directory if present
API_KEY_FILE = BASE_DIR / "geminiapikey.txt"
GEMINI_API_KEYS = []

env_key = os.getenv("GEMINI_API_KEY", "").strip()
if env_key:
    for k in env_key.split(","):
        k = k.strip()
        if k and k not in GEMINI_API_KEYS:
            GEMINI_API_KEYS.append(k)

if API_KEY_FILE.exists():
    try:
        with open(API_KEY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                k = line.strip()
                if k and not k.startswith("#") and k not in GEMINI_API_KEYS:
                    GEMINI_API_KEYS.append(k)
    except Exception:
        pass

# Check sibling directory (Jobmaiker_v3) if available
jobmaker_key_file = BASE_DIR.parent / "Jobmaiker_v3" / "geminiapikey.txt"
if jobmaker_key_file.exists():
    try:
        with open(jobmaker_key_file, "r", encoding="utf-8") as f:
            for line in f:
                k = line.strip()
                if k and not k.startswith("#") and k not in GEMINI_API_KEYS:
                    GEMINI_API_KEYS.append(k)
    except Exception:
        pass

GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

# Read TheirStack API key from environment or ThierstackAPIKey.txt / theirstackapikey.txt
THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY", "")
if not THEIRSTACK_API_KEY:
    possible_key_files = [
        BASE_DIR / "ThierstackAPIKey.txt",
        BASE_DIR / "theirstackapikey.txt",
        BASE_DIR / "TheirstackAPIKey.txt",
        BASE_DIR / "thierstackapikey.txt"
    ]
    # Also check any file matching *theirstack* or *thierstack* in BASE_DIR
    for f in BASE_DIR.glob("*.txt"):
        name_lower = f.name.lower()
        if "theirstack" in name_lower or "thierstack" in name_lower:
            possible_key_files.append(f)

    for kf in possible_key_files:
        if kf.exists():
            try:
                with open(kf, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        THEIRSTACK_API_KEY = content
                        break
            except Exception:
                pass

# Read RapidAPI key from environment or rapidapikey.txt / jsearchapikey.txt
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
if not RAPIDAPI_KEY:
    for kf in [BASE_DIR / "rapidapikey.txt", BASE_DIR / "jsearchapikey.txt"]:
        if kf.exists():
            try:
                with open(kf, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        RAPIDAPI_KEY = content
                        break
            except Exception:
                pass

# MySQL Database Configuration (XAMPP default)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "jobmaker_db")

# Upload configurations
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max
