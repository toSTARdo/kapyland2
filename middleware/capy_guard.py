import json
import datetime
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from database.postgres_db import get_db_connection

class CapyGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        if isinstance(event, types.CallbackQuery):
            if event.message.reply_to_message and event.message.reply_to_message.from_user.id != user.id:
                return await event.answer("Ах ти підступна капібара! 🐾 Це не твій профіль!", show_alert=True)

        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user.id)
            if row:
                meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
                
                if meta.get("status") == "sleep":
                    wake_up_str = meta.get("wake_up")
                    if wake_up_str:
                        wake_time = datetime.datetime.fromisoformat(wake_up_str)
                        if datetime.datetime.now() < wake_time:
                            if isinstance(event, types.Message) and event.text in ["🐾 Профіль"]:
                                return await handler(event, data)
                            
                            msg = "💤 Твоя капібара бачить десятий сон... Не турбуй її."
                            if isinstance(event, types.CallbackQuery):
                                return await event.answer(msg, show_alert=True)
                            else:
                                return await event.answer(msg)
                        else:
                            meta["status"] = "active"
                            await conn.execute(
                                "UPDATE capybaras SET meta = $1 WHERE owner_id = $2",
                                json.dumps(meta, ensure_ascii=False), user.id
                            )
            
            return await handler(event, data)
            
        finally:
            await conn.close()