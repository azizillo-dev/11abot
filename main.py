import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database
import scheduler
from config import BOT_TOKEN
from middlewares.activity import ActivityTrackingMiddleware
from handlers import admin, anonim, start_private, group_chat

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Bot ma'lumotlar bazasini (SQLite) tayyorlash...")
    await database.init_db()
    
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error("BOT_TOKEN sozlanmagan! Iltimos, .env fayliga Telegram bot kalitini kiriting.")
        print("\n[XATOLIK] .env fayliga BOT_TOKEN, GEMINI_API_KEY yoki DEEPSEEK_API_KEY kiritilmagan!")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Middleware ulash (Guruh faolligi va Foydalanuvchi ID-First Name ni saqlash uchun)
    dp.message.middleware(ActivityTrackingMiddleware())

    # Routerlarni ulash (buyruqlar birinchi, umumiy xabarlar oxirida)
    dp.include_router(admin.router)
    dp.include_router(anonim.router)
    dp.include_router(start_private.router)
    dp.include_router(group_chat.router)

    # Fondagi "Sinfdoshlar yozib turila" eslatma schedulerni ishga tushirish
    scheduler.start_scheduler(bot)
    
    logger.info("11-A Sinf Oqibat Boti ishga tushdi! (Polling boshlandi)")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot ishlashi to'xtatildi.")
