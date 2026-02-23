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
            user_click_id = event.callback_query.from_user.id
            
            owner_id = None
            if msg.reply_to_message:
                owner_id = msg.reply_to_message.from_user.id
            elif "ID:" in (msg.text or msg.caption or ""):
                try:
                    owner_id = int(msg.text.split("ID:")[1].strip().split()[0])
                except:
                    pass

            if owner_id and owner_id != user_click_id:
                return await event.callback_query.answer("Ах ти підступна капібара! 🐾 Це не твій профіль!", show_alert=True)

        is_game_command = False
        if event.message and event.message.text:
            text = event.message.text
            game_triggers = ["/", "⚔️", "🗺️", "🧼", "📜", "🎣", "🍎", "💤"]
            if any(text.startswith(trigger) for trigger in game_triggers):
                is_game_command = True
        
        if event.callback_query:
            is_game_command = True

        if not is_game_command:
            return await handler(event, data)

        conn = await get_db_connection()
        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("SELECT meta FROM capybaras WHERE owner_id = $1", user_id)
            
            if not row:
                return await handler(event, data)

            meta = json.loads(row['meta']) if isinstance(row['meta'], str) else row['meta']
            
            if meta.get("status") != "sleep":
                return await handler(event, data)

            wake_up_str = meta.get("wake_up")
            if not wake_up_str:
                return await handler(event, data)

            wake_time = datetime.datetime.fromisoformat(wake_up_str)
            
            if wake_time.tzinfo is None:
                wake_time = wake_time.replace(tzinfo=datetime.timezone.utc)

            if datetime.datetime.now(datetime.timezone.utc) >= wake_time:
                meta["status"] = "overslept"
                await conn.execute("UPDATE capybaras SET meta = $1 WHERE owner_id = $2", json.dumps(meta), user_id)
                return await handler(event, data)

            if event.message and event.message.text:
                safe_commands = ["/start", "🐾 Профіль", "⚙️ Налаштування", "🎒 Інвентар", "🎟️ Лотерея"]
                if event.message.text in safe_commands:
                    return await handler(event, data)

            if event.callback_query:
                call_data = event.callback_query.data
                safe_callbacks = [
                    "profile", "inv_page", "profile_back", "settings",
                    "change_name_start", "toggle_layout", "stats_page", "gacha_spin", 
                    "gacha_guaranteed_10", "equip:", "sell_item:", "inv_pagination:", "inv_page:", "wakeup_now"
                ]
                if any(call_data.startswith(cb) for cb in safe_callbacks):
                    return await handler(event, data)

            warning = "💤 Твоя капібара бачить десятий сон... Не турбуй її."
            if event.callback_query:
                return await event.callback_query.answer(warning, show_alert=True)
            return await event.message.answer(warning)

        finally:
            await conn.close()