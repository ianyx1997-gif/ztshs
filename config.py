"""
ZebraTur SHS Integration - Configuration
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SHS API Configuration
SHS_BASE_URL = os.environ.get("SHS_BASE_URL", "https://api.shsbooking.com")
SHS_REPORT_BASE_URL = os.environ.get("SHS_REPORT_BASE_URL", "https://shsbooking.com")
SHS_FILES_BASE_URL = os.environ.get("SHS_FILES_BASE_URL", "https://shsbooking.com/files")

# Resend email notifications
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_NmbHN67g_CroQSKJPk94e6wqpT77NT6sJ")
RESEND_FROM = os.environ.get("RESEND_FROM", "Zebra Tur <onboarding@resend.dev>")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "ianyx1997@gmail.com")

# B2B operator authentication
B2B_PASSWORD = os.environ.get("B2B_PASSWORD", "zebra-tur-2026")
B2B_USERNAME = os.environ.get("B2B_USERNAME", "admin")

# CORS — comma-separated list of allowed origins for widget/embed
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://zebratur.md,https://www.zebratur.md,https://ai.zebratur.md,http://localhost:3000,*"
).split(",")

# Public base URL (used to build absolute URLs in emails, widget, etc.)
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")

# Claude AI chat for managers
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
CHAT_PASSWORD = os.environ.get("CHAT_PASSWORD", "zebra-chat-2026")  # shared password for all managers
CHAT_DAILY_LIMIT_PER_SESSION = int(os.environ.get("CHAT_DAILY_LIMIT_PER_SESSION", "100"))
# API key for server-to-server access (Kommo bot etc.) — bypasses session cookie auth
CHAT_API_KEY = os.environ.get("CHAT_API_KEY", "")
SHS_USERNAME = os.environ.get("SHS_USERNAME", "ianyx1997@gmail.com")
SHS_PASSWORD = os.environ.get("SHS_PASSWORD", "aRxHghmAQH5Fdolr7kdMwNPMtpOFdM")
SHS_REPORT_TOKEN = os.environ.get("SHS_REPORT_TOKEN", "aRxHghmAQH5Fdolr7kdMwNPMtpOFdM")

# JWT cache: tokens valid 1h, refresh at 55min
JWT_TTL_SECONDS = int(os.environ.get("JWT_TTL_SECONDS", "3300"))

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "zebra-tur-shs-2026-secret-change-in-prod")
DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5050"))

# Database
DB_PATH = DATA_DIR / "zebra.db"

# Business
AGENCY_NAME = "Zebra Tur"
AGENCY_CURRENCY = "EUR"
DEFAULT_MARKUP_PERCENT = float(os.environ.get("DEFAULT_MARKUP_PERCENT", "0"))
DEFAULT_NATIONALITY = "MOLDOVA"
DEFAULT_LANG = "ro"

# UI
SUPPORTED_LANGS = ["ro", "ru", "en"]
