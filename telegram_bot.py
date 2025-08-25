import asyncio, secrets
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from config import settings
from database import SessionLocal
from models import LoginToken, User

router = Router()

@router.message(F.text.regexp(r"^/start"))
async def start_cmd(msg: Message):
    tg_id = str(msg.from_user.id)
    token = secrets.token_urlsafe(24)
    async with SessionLocal() as db:
        res = await db.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(tg_id=tg_id, username=msg.from_user.username or None, role="buyer")
            db.add(user)
            await db.flush()
        lt = LoginToken(token=token, tg_id=tg_id)
        db.add(lt)
        await db.commit()
    auth_link = f"{settings.SITE_BASE_URL}/login.html?token={token}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Войти на сайт", url=auth_link)]])
    await msg.answer("👋 Добро пожаловать в P2P PokerOK\nНажмите кнопку, чтобы войти на сайт.", reply_markup=kb, disable_web_page_preview=True)

async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
