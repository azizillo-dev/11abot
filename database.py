import aiosqlite
import time
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Foydalanuvchilar jadvali (ID - First Name ko'rinishda saqlash uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                username TEXT,
                joined_at REAL NOT NULL,
                is_blocked INTEGER DEFAULT 0
            )
        """)
        
        # Guruhlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                joined_at REAL NOT NULL,
                last_active_time REAL NOT NULL,
                reminder_sent INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0
            )
        """)
        
        # AI va suhbat xotirasi (Shared Context)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                sender_name TEXT NOT NULL,
                role TEXT NOT NULL,
                message_text TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        # Anonim xabarlar jadvali (Admin kim yuborganini ko'rishi uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS anonymous_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                sender_first_name TEXT NOT NULL,
                message_text TEXT NOT NULL,
                sent_at REAL NOT NULL
            )
        """)
        
        # AI va bot statistikasi jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            )
        """)
        
        # Botning guruhlarga yuborgan xabarlari jadvali (Admin o'chirishi uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                sent_at REAL NOT NULL
            )
        """)
        
        await db.commit()

async def add_or_update_user(user_id: int, first_name: str, username: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        now = time.time()
        await db.execute("""
            INSERT INTO users (user_id, first_name, username, joined_at, is_blocked)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username,
                is_blocked = 0
        """, (user_id, first_name or "Sinfdosh", username or "", now))
        await db.commit()

async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, first_name, username, joined_at FROM users ORDER BY joined_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def add_or_update_group(chat_id: int, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = time.time()
        await db.execute("""
            INSERT INTO groups (chat_id, title, joined_at, last_active_time, reminder_sent, message_count)
            VALUES (?, ?, ?, ?, 0, 1)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                last_active_time = ?,
                reminder_sent = 0,
                message_count = groups.message_count + 1
        """, (chat_id, title or "Sinfdoshlar Guruhi", now, now, now))
        await db.commit()

async def update_group_activity(chat_id: int, title: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        now = time.time()
        if title:
            await db.execute("""
                INSERT INTO groups (chat_id, title, joined_at, last_active_time, reminder_sent, message_count)
                VALUES (?, ?, ?, ?, 0, 1)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = excluded.title,
                    last_active_time = excluded.last_active_time,
                    reminder_sent = 0,
                    message_count = groups.message_count + 1
            """, (chat_id, title, now, now))
        else:
            await db.execute("""
                UPDATE groups
                SET last_active_time = ?, reminder_sent = 0, message_count = message_count + 1
                WHERE chat_id = ?
            """, (now, chat_id))
        await db.commit()

async def get_inactive_groups(timeout_seconds: float) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cutoff = time.time() - timeout_seconds
        async with db.execute("""
            SELECT chat_id, title, last_active_time FROM groups
            WHERE last_active_time <= ? AND reminder_sent = 0
        """, (cutoff,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def mark_reminder_sent(chat_id: int, sent: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups SET reminder_sent = ? WHERE chat_id = ?", (1 if sent else 0, chat_id))
        await db.commit()

async def add_chat_message(chat_id: int, sender_name: str, role: str, message_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = time.time()
        await db.execute("""
            INSERT INTO chat_history (chat_id, sender_name, role, message_text, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, sender_name, role, message_text, now))
        
        # Faqat oxirgi 20 ta xabarni qoldirib, eskilari tozalab boriladi (Shared context tejamkorligi uchun)
        await db.execute("""
            DELETE FROM chat_history WHERE chat_id = ? AND id NOT IN (
                SELECT id FROM chat_history WHERE chat_id = ? ORDER BY id DESC LIMIT 20
            )
        """, (chat_id, chat_id))
        await db.commit()

async def get_chat_history(chat_id: int, limit: int = 12) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sender_name, role, message_text FROM chat_history
            WHERE chat_id = ? ORDER BY id ASC LIMIT ?
        """, (chat_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def add_anonymous_message(sender_id: int, sender_first_name: str, message_text: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        now = time.time()
        cursor = await db.execute("""
            INSERT INTO anonymous_messages (sender_id, sender_first_name, message_text, sent_at)
            VALUES (?, ?, ?, ?)
        """, (sender_id, sender_first_name, message_text, now))
        await db.commit()
        return cursor.lastrowid

async def get_recent_anonymous_messages(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, sender_id, sender_first_name, message_text, sent_at
            FROM anonymous_messages ORDER BY sent_at DESC LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def increment_stat(key: str, amount: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO stats (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = value + excluded.value
        """, (key, amount))
        await db.commit()

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key, value FROM stats") as cursor:
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}

async def add_bot_group_message(chat_id: int, message_id: int, message_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = time.time()
        await db.execute("""
            INSERT INTO bot_group_messages (chat_id, message_id, message_text, sent_at)
            VALUES (?, ?, ?, ?)
        """, (chat_id, message_id, message_text[:200], now))
        await db.commit()

async def get_bot_group_messages(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, chat_id, message_id, message_text, sent_at
            FROM bot_group_messages ORDER BY sent_at DESC LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def remove_bot_group_messages_db(ids: list[int]):
    if not ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        placeholders = ",".join("?" * len(ids))
        await db.execute(f"DELETE FROM bot_group_messages WHERE id IN ({placeholders})", ids)
        await db.commit()
