import time
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import database
from config import GROUP_CHAT_ID, ADMIN_IDS
from utils.stickers import get_random_emoji

router = Router()

class AnonimState(StatesGroup):
    waiting_for_message = State()

@router.message(Command("anonim"), F.chat.type == "private")
async def cmd_anonim(message: Message, state: FSMContext):
    # Agar buyruq bilan birga xabar yozilgan bo'lsa (Masalan: /anonim Salom barchaga)
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) > 1 and parts[1].strip():
        anonim_text = parts[1].strip()
        await send_anonymous_message(message, anonim_text)
    else:
        # Agar faqat /anonim yozilgan bo'lsa, matn kutamiz
        await message.answer(
            "🤫 **Anonim xabar rejimi:**\n\n"
            "Guruhimizga anonim tarzda yubormoqchi bo'lgan xabaringizni hozir yozib yuboring.\n"
            "(Bekor qilish uchun /cancel buyrug'ini bosing)",
            parse_mode="Markdown"
        )
        await state.set_state(AnonimState.waiting_for_message)

@router.message(Command("cancel"), StateFilter(AnonimState.waiting_for_message))
async def cancel_anonim(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Anonim xabar yuborish bekor qilindi.")

@router.message(StateFilter(AnonimState.waiting_for_message), F.chat.type == "private")
async def process_anonim_text(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Iltimos, faqat matnli xabar yuboring yoki /cancel bosing.")
        return
    
    await state.clear()
    await send_anonymous_message(message, message.text.strip())

async def send_anonymous_message(message: Message, text: str):
    sender_id = message.from_user.id if message.from_user else 0
    sender_first_name = message.from_user.first_name if message.from_user else "Sinfdosh"
    
    # Guruh ID sini aniqlash
    target_group_id = GROUP_CHAT_ID
    if not target_group_id or target_group_id == 0:
        # Baza guruhlari jadvalidan birinchi ulangan guruhni izlaymiz
        async with database.aiosqlite.connect(database.DB_PATH) as db:
            db.row_factory = database.aiosqlite.Row
            async with db.execute("SELECT chat_id FROM groups LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    target_group_id = row["chat_id"]
    
    if not target_group_id or target_group_id == 0:
        await message.answer("⚠️ Kechirasiz, bot hali hech qaysi sinfdoshlar guruhiga ulanmagan yoki guruh ID si (`GROUP_CHAT_ID`) sozlanmagan!")
        return

    # 1. Guruhga anonim xabar yo'llash ("bu o'sha yuborgan xabari deb habar yo'lladi")
    group_msg_text = f'Kimdir "{text}" deb habar yo\'lladi 🤫✨'
    
    try:
        await message.bot.send_message(
            chat_id=target_group_id,
            text=group_msg_text
        )
    except Exception as e:
        await message.answer(f"❌ Guruhga xabar yuborishda xatolik yuz berdi. Bot guruhga admin qilinganligini tekshiring.\nXato: {e}")
        return

    # 2. Bazaga anonim xabarni saqlash (Admin ko'rishi uchun)
    msg_id = await database.add_anonymous_message(sender_id, sender_first_name, text)

    # 3. Adminga bildirishnoma yuborish (kim yuborgani haqida ID - First Name ko'rinishida)
    admin_log_text = (
        f"🔍 **[ANONIM XABAR NAZORATI — #{msg_id}]**\n\n"
        f"👤 Yuboruvchi: `{sender_id} - {sender_first_name}`\n"
        f"💬 Xabar matni: *\"{text}\"*\n"
        f"🎯 Guruh ID: `{target_group_id}`"
    )
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(chat_id=admin_id, text=admin_log_text, parse_mode="Markdown")
        except Exception:
            pass # Agar admin botni bloklagan bo'lsa yoki topilmasa

    # 4. Foydalanuvchiga tasdiq xabari
    await message.answer(f"✅ Xabaringiz guruhga anonim qilib yuborildi! 🤫✨ {get_random_emoji()}")
