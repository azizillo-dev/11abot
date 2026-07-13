import asyncio
import logging
import httpx
from openai import AsyncOpenAI
import database
from config import GEMINI_API_KEY, DEEPSEEK_API_KEY

logger = logging.getLogger(__name__)

# DeepSeek klientini tayyorlab qo'yamiz (httpx.AsyncClient bilan)
deepseek_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY or "dummy_key",
    base_url="https://api.deepseek.com",
    http_client=httpx.AsyncClient()
)

# Gemini API uchun ham OpenAI-compatible klientdan foydalanamiz
gemini_openai_client = AsyncOpenAI(
    api_key=GEMINI_API_KEY or "dummy_key",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    http_client=httpx.AsyncClient()
)

# Har qanday geo-cheklov yoki API limitlariga qarshi 3-qatlam: Bepul Pollinations AI (OpenAI gpt-4o-mini)
pollinations_client = AsyncOpenAI(
    api_key="dummy_pollinations_key",
    base_url="https://text.pollinations.ai/openai",
    http_client=httpx.AsyncClient()
)

async def generate_response(chat_id: int, user_message: str, system_prompt: str, sender_name: str = "Sinfdosh") -> str:
    """
    Suhbat tarixini (shared context) bazadan oladi, avval Gemini API orqali javob olishga urinadi.
    Agar Gemini limitga tushsa yoki xato bersa, avtomatik DeepSeek API ga o'tib javob qaytaradi.
    """
    # 1. Bazadan oxirgi suhbat tarixini olamiz (Shared Context)
    history_records = await database.get_chat_history(chat_id, limit=12)
    
    # Suhbatdoshni eslab qolish, jinsiga qarab muomala qilish va hazillashish uchun maxsus eslatma
    memory_context = f"\n\nHozirgi suhbatlashayotgan sinfdoshimizning ismi: {sender_name}. DIQQAT: Ismidan va suhbatdan uning QIZ BOLA yoki O'G'IL BOLA ekanini aniqlang! Agar QIZ BOLA bo'lsa: 'jigar qalesan' demang, nazokatli, sizlab, juda nozik va chiroyli muomala qiling ('Sinfimizning guli 🌸', 'Yaxshimisiz' kabi). Agar sevib qoldim yoki romantik gap yozsa, yurakni yashnatadigan romantik va nazokatli javob qaytaring! Agar O'G'IL BOLA bo'lsa: quvnoq do'stona hazil ('qalay jigar/sinfdosh') qiling!"
    messages = [{"role": "system", "content": system_prompt + memory_context}]
    
    for record in history_records:
        role = record["role"]
        # AI API faqat "user" yoki "assistant" rollarini qabul qiladi
        if role not in ["user", "assistant"]:
            role = "user"
        prefix = f"[{record['sender_name']}]: " if role == "user" else ""
        messages.append({
            "role": role,
            "content": f"{prefix}{record['message_text']}"
        })
    
    # Joriy yangi xabarni qo'shamiz
    messages.append({
        "role": "user",
        "content": f"[{sender_name}]: {user_message}"
    })
    
    # 2. BIRINCHI URANISH (ENG TEZ VA CHEKSIZ): Pollinations AI (OpenAI gpt-4o-mini - geo-bloksiz)
    try:
        response = await pollinations_client.chat.completions.create(
            model="openai",
            messages=messages,
            temperature=0.75,
            max_tokens=600
        )
        reply_text = response.choices[0].message.content.strip()
        if reply_text:
            await database.increment_stat("gemini_calls") # Asosiy AI chaqiruv hisobida saqlaymiz
            await database.add_chat_message(chat_id, sender_name, "user", user_message)
            await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", reply_text)
            return reply_text
    except Exception as e:
        logger.warning(f"[Pollinations API xatosi] {e}. Gemini API ga o'tilmoqda...")

    # 3. IKKINCHI URANISH (Fallback): Google Gemini API
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
        for model_name in models_to_try:
            try:
                response = await gemini_openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.75,
                    max_tokens=600
                )
                reply_text = response.choices[0].message.content.strip()
                if reply_text:
                    await database.increment_stat("failover_count")
                    await database.add_chat_message(chat_id, sender_name, "user", user_message)
                    await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", reply_text)
                    return reply_text
            except Exception as model_err:
                logger.warning(f"[Gemini API xatosi ({model_name})] {model_err}")
                continue

    # 4. UCHINCHI URANISH (Final Fallback): DeepSeek API
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here":
        try:
            response = await deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=600
            )
            reply_text = response.choices[0].message.content.strip()
            if reply_text:
                await database.increment_stat("deepseek_calls")
                await database.add_chat_message(chat_id, sender_name, "user", user_message)
                await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", reply_text)
                return reply_text
        except Exception as e:
            logger.error(f"[DeepSeek API xatosi] {e}")

    await database.increment_stat("api_errors")
    return f"Assalomu alaykum, {sender_name}! 😊 Hozircha AI tizimimizda qisqa yangilanish bo'lmoqda, lekin men baribir 11-a sinfimizning eng oqibatli va samimiy botiman! ✨🤝"
