import random
from aiogram import Router, F
from aiogram.types import Message
from ai_service import generate_response
from utils.prompts import SYSTEM_PROMPT_GROUP
from utils.stickers import get_random_sticker, get_random_emoji
import database

router = Router()

# Guruhdagi har qanday xabar
@router.message(F.chat.type.in_(["group", "supergroup"]))
async def handle_group_messages(message: Message):
    if not message.text:
        return

    # Guruh bazada ro'yxatdan o'tgani aniqlanadi (agar middleware qo'shmagan bo'lsa ham javob berayotganda)
    await database.add_or_update_group(message.chat.id, message.chat.title or "Sinfdoshlar Guruhi")
    
    bot_info = await message.bot.get_me()
    bot_id = bot_info.id
    bot_username = bot_info.username

    # Botga javob yuborish shartlarini aniqlash:
    # 1. Agar xabar botning o'ziga reply qilingan bo'lsa
    is_reply_to_bot = (
        message.reply_to_message 
        and message.reply_to_message.from_user 
        and message.reply_to_message.from_user.id == bot_id
    )
    
    # 2. Agar matnda bot username i yoki nomi tilga olingan bo'lsa
    is_mentioned = bot_username and (f"@{bot_username}" in message.text)
    is_called_by_name = any(word in message.text.lower() for word in ["bot", "oqibat bot", "11-a bot"])
    
    # 3. Guruhda suhbat qizishida tasodifiy (masalan 12% ehtimollik bilan yoki maxsus kalit so'zlar eslatilganda)
    keywords = ["oqibat", "sinfdosh", "yig'ilish", "choyxona", "maktab", "davra", "sog'indik", "11-a"]
    has_keyword = any(kw in message.text.lower() for kw in keywords)
    should_random_reply = (random.random() < 0.12) or has_keyword

    if is_reply_to_bot or is_mentioned or is_called_by_name or should_random_reply:
        sender_name = message.from_user.first_name if message.from_user else "Sinfdosh"
        
        # "yozmoqda..." actioni
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        reply_text = await generate_response(
            chat_id=message.chat.id,
            user_message=message.text,
            system_prompt=SYSTEM_PROMPT_GROUP,
            sender_name=sender_name
        )
        
        await message.reply(reply_text)
        
        # Stikerlarni faqat kerakli, quvnoq joyda va kamroq (15% ehtimollik bilan) yuboramiz
        if "texnik tanaffus" not in reply_text and random.random() < 0.15:
            try:
                await message.answer_sticker(get_random_sticker())
            except Exception:
                pass
