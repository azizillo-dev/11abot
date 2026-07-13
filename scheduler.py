import asyncio
import logging
from aiogram import Bot
import database
from ai_service import generate_response
from utils.prompts import SYSTEM_PROMPT_REMINDER
from utils.stickers import get_random_sticker, get_random_emoji
from config import INACTIVITY_TIMEOUT_HOURS

logger = logging.getLogger(__name__)

async def check_inactivity_task(bot: Bot):
    """
    Guruhdagi jimjitlikni kuzatuvchi va avtomatik "Sinfdoshlar yozib turila" deb xabar yo'llovchi funksiya.
    Har 10-15 daqiqada tekshirib boradi.
    """
    timeout_seconds = INACTIVITY_TIMEOUT_HOURS * 3600.0
    
    while True:
        try:
            inactive_groups = await database.get_inactive_groups(timeout_seconds)
            for group in inactive_groups:
                chat_id = group["chat_id"]
                title = group["title"]
                logger.info(f"[{title} - {chat_id}] guruhida jimjitlik aniqlandi. Avto-xabar yuborilmoqda...")
                
                # AI orqali samimiy va hazilkash oqibat eslatmasini tayyorlaymiz
                prompt = "Sinfdoshlar, jim bo'lib ketdingizlar? Oqibatni yo'qotmaylik deb eslatib qo'ying chiroyli va hazilkash tabassumli so'zlar bilan!"
                reminder_text = await generate_response(
                    chat_id=chat_id,
                    user_message=prompt,
                    system_prompt=SYSTEM_PROMPT_REMINDER,
                    sender_name="Tizim"
                )
                
                # Guruhga yo'llash
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"{reminder_text} {get_random_emoji()}"
                    )
                    # Tabassumli stiker yuborish
                    try:
                        await bot.send_sticker(chat_id=chat_id, sticker=get_random_sticker())
                    except Exception:
                        pass
                    
                    # Eslatma yuborilganligini qayd etamiz (toki yana kimdir yozmaguncha qayta yubormasin)
                    await database.mark_reminder_sent(chat_id, sent=True)
                    await database.increment_stat("auto_reminders_sent")
                except Exception as e:
                    logger.error(f"Guruhga xabar yuborishda xato ({chat_id}): {e}")
                    
        except Exception as e:
            logger.error(f"Scheduler xatosi: {e}")
            
        # 15 daqiqa (900 soniya) kutish
        await asyncio.sleep(900)

def start_scheduler(bot: Bot):
    """Asinxron fonda schedulerni ishga tushirish"""
    asyncio.create_task(check_inactivity_task(bot))
