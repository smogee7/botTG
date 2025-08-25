import asyncio
import secrets
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import Column, Integer, String, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# ==========================
# Настройки
# ==========================
TELEGRAM_BOT_TOKEN = "8264778693:AAGlA2MTQMKqHsj7V8AV9_Z3Uw7Asyt9LCU"
SITE_BASE_URL = "http://localhost:5500"  # URL вашего сайта
DATABASE_URL = "sqlite+aiosqlite:///./app.db"  # SQLite, можно заменить на PostgreSQL

# ==========================
# База данных и модели
# ==========================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tg_id = Column(String, unique=True, nullable=False)  # Telegram ID
    username = Column(String, nullable=True)
    role = Column(String, default="buyer", nullable=False)

    tokens = relationship("LoginToken", back_populates="user")

class LoginToken(Base):
    __tablename__ = 'login_tokens'

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, nullable=False)
    tg_id = Column(String, ForeignKey('users.tg_id'), nullable=False)

    user = relationship("User", back_populates="tokens")

# Создаём асинхронный движок и сессию
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ==========================
# Telegram-бот
# ==========================
router = Router()

@router.message(F.text.regexp(r"^/start"))
async def start_cmd(msg: Message):
    tg_id = str(msg.from_user.id)
    token = secrets.token_urlsafe(24)

    try:
        async with SessionLocal() as db:
            # Проверяем, есть ли пользователь
            res = await db.execute(select(User).where(User.tg_id == tg_id))
            user = res.scalar_one_or_none()

            if not user:
                # Если пользователя нет, создаём нового
                user = User(tg_id=tg_id, username=msg.from_user.username or None, role="buyer")
                db.add(user)
                await db.flush()

            # Создаём токен для авторизации
            lt = LoginToken(token=token, tg_id=tg_id)
            db.add(lt)
            await db.commit()

        # Генерируем ссылку на сайт
        auth_link = f"{SITE_BASE_URL}/login.html?token={token}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Войти на сайт", url=auth_link)]]
        )
        await msg.answer(
            "👋 Добро пожаловать в P2P PokerOK\nНажмите кнопку, чтобы войти на сайт.",
            reply_markup=kb,
            disable_web_page_preview=True
        )

    except Exception as e:
        await msg.answer(f"Произошла ошибка: {e}")

# ==========================
# Основная функция
# ==========================
async def main():
    # Создаём таблицы, если их нет
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
