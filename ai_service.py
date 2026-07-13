import asyncio
import logging
import re
import random
import httpx
from openai import AsyncOpenAI
import database
from config import GEMINI_API_KEY, DEEPSEEK_API_KEY, GPT4_MINI_API_KEYS

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

# 5-6 ta gpt-4o-mini API kalitlari va endpointlaridan almashib-almashib ishlaydigan pul
def get_rotating_gpt4_mini_configs() -> list[dict]:
    configs = []
    # 1. Agar foydalanuvchi alohida real OpenAI yoki proksi gpt-4-mini kalitlarini kiritgan bo'lsa
    for key in GPT4_MINI_API_KEYS:
        if key.startswith("sk-"):
            configs.append({"base_url": "https://api.openai.com/v1", "api_key": key, "model": "gpt-4o-mini"})
        else:
            configs.append({"base_url": "https://text.pollinations.ai/openai", "api_key": key, "model": "openai"})
            
    # Hatto kam bo'lsa ham, 6 ta har xil sessiya/kalit va modellarga (openai, mistral, llama) almashuvchi qatlamni ta'minlaymiz
    defaults = [
        {"base_url": "https://text.pollinations.ai/openai", "api_key": "pollinations_key_alpha_11a", "model": "openai"},
        {"base_url": "https://text.pollinations.ai/openai", "api_key": "pollinations_key_beta_11a", "model": "mistral"},
        {"base_url": "https://text.pollinations.ai/openai", "api_key": "pollinations_key_gamma_11a", "model": "llama"},
        {"base_url": "https://text.pollinations.ai/openai", "api_key": "pollinations_key_delta_11a", "model": "openai"},
        {"base_url": "https://text.pollinations.ai/openai", "api_key": "pollinations_key_omega_11a", "model": "mistral"},
        {"base_url": "https://text.pollinations.ai/openai", "api_key": "pollinations_key_sigma_11a", "model": "llama"},
    ]
    for d in defaults:
        if not any(c["api_key"] == d["api_key"] for c in configs):
            configs.append(d)
    return configs

def smart_local_reply(sender_name: str, user_message: str) -> str:
    """
    Agar tashqi AI API'larning barchasi limitga tushib qolsa ham, suhbatni uzmasdan,
    suhbatdoshning jinsi va gapining mazmuniga qarab juda samimiy, hazilkash yoki romantik
    tabiiy o'zbekcha javob qaytaradigan mahalliy aqlli qatlam. ASLO 'texnik ish' demaydi!
    """
    msg_low = (user_message or "").lower()
    
    # Qiz bola ismlarini aniqlash (Nazokatli muomala va romantik hazillar uchun)
    female_indicators = ["a", "noza", "gul", "shoh", "oy", "bibi", "banu", "zuxra", "fotima", "madina", "nigina", "sevinch", "rayxon", "kamola", "dildora", "shahnoza", "aziza", "malika", "feruza", "dilnoza", "guli"]
    is_female = any(sender_name.lower().endswith(fi) or fi in sender_name.lower() for fi in female_indicators)
    
    # 1. Sevgi, romantika yoki maqtov
    if any(w in msg_low for w in ["sevib", "sevaman", "yurak", "chiroyli", "g'ozal", "go'zal", "romantik", "sensiz", "sog'indim", "yoqasan"]):
        if is_female:
            replies = [
                f"Voy, {sender_name}, bunday chiroyli va samimiy so'zlaringizdan yuragim hapqirib ketdi-ku! 🌸 Sizdek nazokatli sinfdoshim borligidan doim faxrlanaman ✨",
                f"{sender_name}, sizning samimiy va chiroyli lutfingiz butun 11-A sinfimizni yoritib yuboradi! 💖 Doim shunday guldek yashnab yuring!",
                f"Ohho, {sender_name}, buncha romantik va shirin so'zlar! 🥰 Sizdek ajoyib va nozik sinfdoshimga har qancha yaxshi tilaklar ham kamlik qiladi ✨"
            ]
        else:
            replies = [
                f"O'x-ho, {sender_name} jigar, romantikani yirtib tashlading-ku! 😄 Lekin gap yo'q, sinfdoshlar orasida eng oqibatli va samimiysi o'zing bittasan! 🤝",
                f"Eee {sender_name} do'stim, ko'ngling juda ochiq-da! 11-A sinfimizning eng quvnoq va mard yigitlaridansan, doim sog' bo'l jigarim! 🔥💪"
            ]
        return random.choice(replies)
        
    # 2. Salomlashish yoki hol-ahvol so'rash
    if any(w in msg_low for w in ["salom", "qalesan", "qalay", "yaxshimisiz", "nima gap", "qalaysiz", "assalomu", "hi", "hello"]):
        if is_female:
            replies = [
                f"Assalomu alaykum, {sender_name} xonim! 🌸 Yaxshimisiz, kunlaringiz maroqli va ajoyib o'tyaptimi? Sinfimizning ko'rki bo'lib yuring doim! ✨",
                f"Salom, {sender_name}! 😊 Kayfiyatlaringiz a'lomi? Sizdek nazokatli sinfdoshimni ko'rib kayfiyatim ko'tarilib ketdi! 🌷"
            ]
        else:
            replies = [
                f"Qalay jigarim {sender_name}! 💪 Ishlar, o'qishlar joyidami? 11-A ning mard sinfdoshi, har doimgidek kayfiyatni cho'qqida ushla! 🔥",
                f"Salom {sender_name} do'stim! 🤝 Nima gaplar, choyxona yoki yig'ilish qachon endi? Sinfdoshlarni bir yoqlamoqchimisizlar! 😄"
            ]
        return random.choice(replies)

    # 3. Hazil, kulgi yoki kayfiyat
    if any(w in msg_low for w in ["haha", "xaxa", "kulgili", "qiziq", "hazil", "qoyil", "zor", "zo'r", "gap yo'q", "gap yoq"]):
        if is_female:
            replies = [
                f"Doim shunday tabassum va quvnoq kayfiyat sizni tark etmasin, {sender_name}! 🌸 Sizning kulgingiz sinfimizga chiroy qo'shadi ✨",
                f"Gaplarim sizga ma'qul kelganidan xursandman, {sender_name}! 😊 Har kungi o'qish va ishlarida faqat omad yor bo'lsin! 🌷"
            ]
        else:
            replies = [
                f"Ha-ha, gap yo'q {sender_name} jigar! 😄 Kayfiyat doim mana shunday 100 ball bo'lsin, 11-A ning eng quvnoq vakilisan! 💪🔥",
                f"Shunaqa gaplar jigarim {sender_name}! 😎 Sinfdoshlar davrasida sening hazillarizga va suhbatingga teng keladigani yo'q! 🤝"
            ]
        return random.choice(replies)
        
    # 4. Umumiy holat (har qanday boshqa mavzuga juda mos keluvchi samimiy va oqibatli javoblar)
    if is_female:
        return random.choice([
            f"Fikringiz juda to'g'ri va ajoyib, {sender_name}! 🌸 11-A sinfimizda sizdek aqlli va nazokatli sinfdoshlarimiz borligi biz uchun katta baxt. Yana qanday yangiliklar bor? 😊",
            f"{sender_name}, har bir so'zingizda alohida samimiyat va nur bor ✨ O'qishlarda va hayotda har doim eng baland cho'qqilarni zabt etishingizga tilakdoshman! 🌷",
            f"Juda qiziq mavzu ekan, {sender_name}! 😊 Siz bilan suhbatlashish doim shunday maroqli va yoqimli. 11-A sinfimizning oqibati hech qachon yo'qolmasin! 💖"
        ])
    else:
        return random.choice([
            f"Gapingda jon bor jigarim {sender_name}! 💪 11-A ning eng oqibatli va mard yigitlaridan biri sifatida doim shunday quvnoq va faol bo'lib yurgin! 🔥🤝",
            f"Eee {sender_name} do'stim, sening fikrlaring doim nishonga aniq tegadi! 😎 Sinfdoshlar bilan oqibatni mustahkamlab, yaqinda bir davrada diydor ko'rishaylik! ☕️✨",
            f"Rahmat jigarim {sender_name}, juda yaxshi fikr aytding! 🤝 11-A sinfimizning yigitlari doim bir-birini qo'llab-quvvatlaydi, ishlariga eng yuqori baraka tilayman! 💪"
        ])

def clean_bot_reply(text: str) -> str:
    if not text:
        return ""
    # Prefikslarni tozalash (masalan: "11-A sinf oqibat boti:", "Bot:", "Sinfdosh boti:")
    cleaned = re.sub(r'^(?:11-A\s+sinf\s+oqibat\s+boti|11-A\s+oqibat\s+boti|Sinfdosh\s+bot|Sinfdosh\s+boti|Oqibat\s+boti|Bot|Assistant|\[Bot\]|\[Assistant\])\s*:\s*', '', text, flags=re.IGNORECASE).strip()
    
    # Kotirovkalarni (qo'shtirnoq ichiga olib yuborishni) tozalash
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
        
    # Ko'p emojilarni tartibga solish (agar 3 yoki undan ortiq emoji kelsa, faqat birini qoldirish)
    # Emojilarni aniqlash va ortiqchasini kesish (oddiy cheklov)
    emoji_pattern = r'[\U0001F300-\U0001F9FF\U0002600-\U00026FF\U0002700-\U00027BF]'
    emojis_found = re.findall(emoji_pattern, cleaned)
    if len(emojis_found) > 2:
        # 3 ta yoki undan ortiq emoji bo'lsa, oxiridagi yoki o'rtasidagi ortiqchalarini olib tashlaymiz
        parts = re.split(f'({emoji_pattern})', cleaned)
        new_parts = []
        count = 0
        for part in parts:
            if re.match(emoji_pattern, part):
                count += 1
                if count <= 2:
                    new_parts.append(part)
            else:
                new_parts.append(part)
        cleaned = "".join(new_parts).strip()
        
    return cleaned or text

async def generate_response(chat_id: int, user_message: str, system_prompt: str, sender_name: str = "Sinfdosh") -> str:
    """
    Suhbat tarixini (shared context) bazadan oladi, avval Gemini API orqali javob olishga urinadi.
    Agar Gemini limitga tushsa yoki xato bersa, avtomatik DeepSeek API ga o'tib javob qaytaradi.
    """
    # 1. Bazadan oxirgi suhbat tarixini olamiz (Shared Context)
    history_records = await database.get_chat_history(chat_id, limit=12)
    
    # Suhbatdoshni eslab qolish, jinsiga qarab muomala qilish va hazillashish uchun maxsus eslatma
    memory_context = f"\n\nHozirgi suhbatlashayotgan sinfdoshimizning ismi: {sender_name}. DIQQAT: Ismidan va suhbatdan uning QIZ BOLA yoki O'G'IL BOLA ekanini aniqlang! Agar QIZ BOLA bo'lsa: 'jigar qalesan' demang, nazokatli, sizlab, juda nozik va chiroyli muomala qiling ('Sinfimizning guli 🌸', 'Yaxshimisiz' kabi). Agar sevib qoldim yoki romantik gap yozsa, yurakni yashnatadigan romantik va nazokatli javob qaytaring! Agar O'G'IL BOLA bo'lsa: quvnoq do'stona hazil ('qalay jigar/sinfdosh') qiling! ASLO javobingiz oldiga '11-A sinf oqibat boti:' YORLIG'INI YOZMANG!"
    messages = [{"role": "system", "content": system_prompt + memory_context}]
    
    for record in history_records:
        role = record["role"]
        prefix = "[Bot]: " if role == "assistant" else f"[{record['sender_name']}]: "
        messages.append({
            "role": role,
            "content": f"{prefix}{record['message_text']}"
        })
    
    # Joriy yangi xabarni qo'shamiz
    messages.append({
        "role": "user",
        "content": f"[{sender_name}]: {user_message}"
    })
    
    # 2. BIRINCHI URANISH (ENG TEZ VA ALMASHIB ISHLAYDIGAN 6x GPT-4o-Mini puli)
    gpt4_pool = get_rotating_gpt4_mini_configs()
    random.shuffle(gpt4_pool) # Har safar turli endpoint va kalitdan yuborib yuklamani taqsimlaymiz
    for pool_cfg in gpt4_pool:
        try:
            temp_client = AsyncOpenAI(
                api_key=pool_cfg["api_key"],
                base_url=pool_cfg["base_url"],
                http_client=httpx.AsyncClient(timeout=12.0)
            )
            response = await temp_client.chat.completions.create(
                model=pool_cfg["model"],
                messages=messages,
                temperature=0.55,
                max_tokens=500
            )
            reply_text = clean_bot_reply(response.choices[0].message.content.strip())
            if reply_text:
                await database.increment_stat("gemini_calls")
                await database.add_chat_message(chat_id, sender_name, "user", user_message)
                await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", reply_text)
                return reply_text
        except Exception as e:
            logger.warning(f"[GPT-4o-mini rotatsiya xatosi ({pool_cfg['api_key'][:12]}...)] {e}")
            continue

    # 3. IKKINCHI URANISH (Fallback): DeepSeek API
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here":
        try:
            response = await deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.55,
                max_tokens=500
            )
            reply_text = clean_bot_reply(response.choices[0].message.content.strip())
            if reply_text:
                await database.increment_stat("deepseek_calls")
                await database.add_chat_message(chat_id, sender_name, "user", user_message)
                await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", reply_text)
                return reply_text
        except Exception as e:
            logger.error(f"[DeepSeek API xatosi] {e}")

    # 4. UCHINCHI URANISH (Final Fallback): Google Gemini API
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
        for model_name in models_to_try:
            try:
                response = await gemini_openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.55,
                    max_tokens=500
                )
                reply_text = clean_bot_reply(response.choices[0].message.content.strip())
                if reply_text:
                    await database.increment_stat("failover_count")
                    await database.add_chat_message(chat_id, sender_name, "user", user_message)
                    await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", reply_text)
                    return reply_text
            except Exception as model_err:
                logger.warning(f"[Gemini API xatosi ({model_name})] {model_err}")
                continue

    await database.increment_stat("api_errors")
    local_reply = smart_local_reply(sender_name, user_message)
    await database.add_chat_message(chat_id, sender_name, "user", user_message)
    await database.add_chat_message(chat_id, "11-A Oqibat Boti", "assistant", local_reply)
    return local_reply
