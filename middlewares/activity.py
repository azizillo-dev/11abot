from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
import database

class ActivityTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat:
            # Agar xabar guruhdan bo'lsa, guruhning faollik vaqtini yangilaymiz
            if event.chat.type in ["group", "supergroup"]:
                await database.update_group_activity(
                    chat_id=event.chat.id,
                    title=event.chat.title or "Sinfdoshlar Guruhi"
                )
            # Agar xabar foydalanuvchidan bo'lsa, foydalanuvchilar jadvaliga ID - First Name ko'rinishida saqlaymiz
            if event.from_user:
                await database.add_or_update_user(
                    user_id=event.from_user.id,
                    first_name=event.from_user.first_name or "Sinfdosh",
                    username=event.from_user.username or ""
                )
        return await handler(event, data)
