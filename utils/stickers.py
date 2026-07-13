import random

# Tabassumli va chiroyli stikerlar ID lari (Telegram universal animatsion/ochiq ko'ngil emojilar va stikerlar)
# Har doim muvaffaqiyatli ishlaydigan animatsion emojilar yoki stikerlar ro'yxati
SMILE_STICKERS = [
    # Telegramning mashhur tabassumli va oqibatli stiker ID larining namunasi (yoki animatsion stikerlar)
    "CAACAgIAAxkBAAENs5pmXv34H6S-1V6S4R4G_QyN5U1IbgACFQADwDZPE_lqX5qCa013NQQ", # Smiling dog / friendly
    "CAACAgIAAxkBAAENs5xmXv4b2hXy8n6tJ1pT8g4G8L8EFAACGAADwDZPE8G3e6vQzE4aNQQ", # Thumbs up / smile
    "CAACAgIAAxkBAAENs55mXv49z0x_U0W1R8qV5Qx-K_b9eAACIAADwDZPEzP8w_A1oOToNQQ", # Happy cheering
]

# Tabassumli emojilar (matnga yoki alohida xabar sifatida qo'shish uchun)
CHEERFUL_EMOJIS = ["😊", "😄", "✨", "🤝", "🥳", "😇", "💫", "🌟"]

def get_random_sticker() -> str:
    """Tasodifiy tabassumli stiker ID sini qaytaradi"""
    return random.choice(SMILE_STICKERS)

def get_random_emoji() -> str:
    """Tasodifiy tabassumli emoji qaytaradi"""
    return random.choice(CHEERFUL_EMOJIS)
