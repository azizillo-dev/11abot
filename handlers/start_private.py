from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from ai_service import generate_response
from utils.prompts import SYSTEM_PROMPT_PRIVATE
from utils.stickers import get_random_sticker, get_random_emoji

router = Router()

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: Message):
    first_name = message.from_user.first_name if message.from_user else "Sinfdosh"
    
    welcome_text = (
        f"Assalomu alaykum, {first_name}! {get_random_emoji()}\n\n"
        f"Men **11-a sinf oqibat botiman**. Sinfdoshlarimizning o'zaro oqibatini mustahkamlash, "
        f"guruhda suhbatni qizg'itish va har biringizga yaxshi kayfiyat ulashish uchun yaralganman! 😊\n\n"
        f"🌟 **Nimalar qila olaman?**\n"
        f"• Menga istalgan savol yoki gap yozing — chiroyli va hazilkash suhbatlashamiz!\n"
        f"• 🤫 `/anonim [xabar]` — guruhimizga anonim xabar yuborish uchun! "
        f"(Masalan: `/anonim Bugun kechqurun futbol bormi? ⚽️`)\n"
        f"• Guruhimizda hech kim yozmay qolsa, o'zim sinfdoshlarni yoqlab xabar yozib turaman! ✨🤝"
    )
    
    await message.answer(welcome_text, parse_mode="Markdown")
    try:
        await message.answer_sticker(get_random_sticker())
    except Exception:
        pass

# Shaxsiy chatda suhbatlashish (erkin xabar yozganda AI javob beradi)
@router.message(F.chat.type == "private", ~F.text.startswith("/"))
async def handle_private_chat(message: Message):
    if not message.text:
        return
    
    sender_name = message.from_user.first_name if message.from_user else "Sinfdosh"
    
    # "yozmoqda..." statusini ko'rsatamiz
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    reply_text = await generate_response(
        chat_id=message.chat.id,
        user_message=message.text,
        system_prompt=SYSTEM_PROMPT_PRIVATE,
        sender_name=sender_name
    )
    
    await message.answer(f"{reply_text} {get_random_emoji()}")
