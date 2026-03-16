from pathlib import Path
import os

BASE_DIR = Path(__file__).parent

AUDIO_DIR = BASE_DIR / "audio"
UPLOAD_DIR = BASE_DIR / "uploads"

AUDIO_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

AUDIO_FILE = AUDIO_DIR / "input.wav"

SAMPLE_RATE = 16000
CHANNELS = 1

# Voice activity detection
SILENCE_THRESHOLD = 250
SILENCE_DURATION = 2.0
MAX_RECORD_SECONDS = 20

# Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# MongoDB
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "voice_billing"

# Receipt
RECEIPT_DIR = BASE_DIR / "audio"
RECEIPT_DIR.mkdir(exist_ok=True)
PDF_FILE = RECEIPT_DIR / "latest_receipt.pdf"

# Optional: if ffmpeg is inside project
FFMPEG_DIR = BASE_DIR / "ffmpeg"
ffmpeg_bin = FFMPEG_DIR / "bin"
if ffmpeg_bin.exists():
    os.environ["PATH"] += os.pathsep + str(ffmpeg_bin)