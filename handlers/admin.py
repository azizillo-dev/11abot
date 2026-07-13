import html
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import database
from config import ADMIN_IDS, INACTIVITY_TIMEOUT_HOURS

router = Router()

class AdminBroadcastState(StatesGroup):
    waiting_for_broadcast_text = State()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar (ID-First Name)", callback_data="admin_users"),
            InlineKeyboardButton(text="🤫 Anonim Xabarlar", callback_data="admin_anonim_logs")
        ],
        [
            InlineKeyboardButton(text="📊 AI & Bot Statistikasi", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Broadcast Yuborish", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
        ]
    ])

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        await message.answer("⚠️ Ushbu buyruqdan faqat bot adminlari foydalana oladi.")
        return
    
    await message.answer(
        "🛠 **11-A Sinf Oqibat Boti — Admin Paneli**\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    users = await database.get_all_users()
    if not users:
        await callback.message.edit_text("Hozircha foydalanuvchilar mavjud emas.", reply_markup=get_admin_keyboard())
        return

    # ID - First Name ko'rinishida formatlash (HTML parse mode orqali xatosiz ishlash)
    lines = [f"👥 <b>Jami foydalanuvchilar (ID - First Name ko'rinishida): {len(users)} ta</b>\n"]
    for u in users[:35]: # Telegram xabar uzunligi cheklovidan o'tmaslik uchun 35 ta ko'rsatamiz
        uid = u["user_id"]
        fname = html.escape(u["first_name"] or "Noma'lum")
        uname = f" (@{html.escape(u['username'])})" if u["username"] else ""
        lines.append(f"• <code>{uid}</code> - <b>{fname}</b>{uname}")
    
    if len(users) > 35:
        lines.append(f"\n...va yana {len(users) - 35} ta foydalanuvchi.")
        
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_anonim_logs")
async def cb_admin_anonim_logs(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    logs = await database.get_recent_anonymous_messages(limit=15)
    if not logs:
        await callback.message.edit_text("Hozircha anonim xabarlar yo'q.", reply_markup=get_admin_keyboard())
        return

    lines = ["🤫 <b>Oxirgi anonim xabarlar (Admin nazorati):</b>\n"]
    for log in logs:
        sender_id = log["sender_id"]
        fname = html.escape(log["sender_first_name"] or "Noma'lum")
        text = html.escape(log["message_text"])
        lines.append(f"• <code>{sender_id}</code> - <b>{fname}</b> yubordi:\n  💬 <i>\"{text}\"</i>\n")
        
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    stats = await database.get_stats()
    users = await database.get_all_users()
    
    # Guruhlar sonini ham aniqlash
    async with database.aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM groups") as cursor:
            row = await cursor.fetchone()
            group_count = row[0] if row else 0

    gemini_calls = stats.get("gemini_calls", 0)
    deepseek_calls = stats.get("deepseek_calls", 0)
    failovers = stats.get("failover_count", 0)
    reminders = stats.get("auto_reminders_sent", 0)

    text = (
        f"📊 **Bot va AI Statistikasi**\n\n"
        f"👥 Jami foydalanuvchilar: **{len(users)} ta**\n"
        f"🎯 Ulangan guruhlar: **{group_count} ta**\n"
        f"⏱ Jimjitlik taymeri: **{INACTIVITY_TIMEOUT_HOURS} soat**\n\n"
        f"🤖 **AI Klaster Ishlash Holati:**\n"
        f"• Gemini API javoblari: **{gemini_calls} ta**\n"
        f"• DeepSeek API javoblari (yada failover): **{deepseek_calls} ta**\n"
        f"• Avto-Failover ishga tushdi: **{failovers} marta**\n\n"
        f"✨ Avtomatik oqibat eslatmalari: **{reminders} ta**"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    await callback.message.edit_text(
        "📢 **Guruhlarga xabar yuborish (Broadcast):**\n\n"
        "Yubormoqchi bo'lgan xabaringizni yozing. U barcha ulangan sinfdoshlar guruhiga yuboriladi!\n"
        "(Bekor qilish uchun /cancel bosing)"
    )
    await state.set_state(AdminBroadcastState.waiting_for_broadcast_text)

@router.message(StateFilter(AdminBroadcastState.waiting_for_broadcast_text))
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.text:
        await message.answer("Matnli xabar yuboring.")
        return
    
    await state.clear()
    text = message.text.strip()
    
    # Barcha guruhlarga yuborish
    async with database.aiosqlite.connect(database.DB_PATH) as db:
        db.row_factory = database.aiosqlite.Row
        async with db.execute("SELECT chat_id, title FROM groups") as cursor:
            groups = await cursor.fetchall()
            
    sent_count = 0
    for grp in groups:
        try:
            await message.bot.send_message(
                chat_id=grp["chat_id"],
                text=f"📢 **Sinfdoshlar uchun e'lon:**\n\n{text}",
                parse_mode="Markdown"
            )
            sent_count += 1
        except Exception as e:
            pass
            
    await message.answer(f"✅ Xabar **{sent_count} ta** guruhga muvaffaqiyatli yuborildi!", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    await callback.message.delete()
