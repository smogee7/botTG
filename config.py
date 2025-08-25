from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = "8264778693:AAGlA2MTQMKqHsj7V8AV9_Z3Uw7Asyt9LCU"
    SITE_BASE_URL: str = "http://localhost:5500"
    JWT_SECRET: str = "qwertyuiopasdfghjklzxcvbnmqwerty"
    JWT_EXPIRE_MINUTES: int = 7 * 24 * 60
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"  # файл БД в корне проекта
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]
    LOGIN_TOKEN_TTL_SEC: int = 10 * 60  # 10 минут
    MODERATOR_TG_IDS: List[str] = ["643408817"]    # например ["12345678"]

settings = Settings()
