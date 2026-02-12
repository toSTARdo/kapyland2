import json
import datetime
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from database.postgres_db import get_db_connection

class CapyGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Update, Dict[str, Any]], Awaitable[Any]],
        event: types.Update,
        data: Dict[str, Any],
    ) -> Any:
        
        payload = event.message or event.callback_query
        if not payload:
            return await handler(event, data)

        user_id = payload.from_user.id

        if event.callback_query:
            msg = event.callback_query.message
            if msg.reply_to_message and msg.reply_to_message.from_user.id != user_id:
                return await event.callback_query.answer("Ах ти підступна капібара! 🐾 Це не твій профіль!", show_alert=True)

        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
            if row:
                meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
                
                if meta.get("status") == "sleep":
                    wake_up_str = meta.get("wake_up")
                    if wake_up_str:
                        wake_time = datetime.datetime.fromisoformat(wake_up_str)
                        if datetime.datetime.now() < wake_time:
                            if event.message and event.message.text in ["/start", "🐾 Профіль"]:
                                return await handler(event, data)
                            
                            warning = "💤 Твоя капібара бачить десятий сон... Не турбуй її."
                            if event.callback_query:
                                return await event.callback_query.answer(warning, show_alert=True)
                            else:
                                return await event.message.answer(warning)
                        else:
                            meta["status"] = "active"
                            await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), user_id)
            
            return await handler(event, data)
        finally:
            await conn.close()