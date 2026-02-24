import asyncio
from aiogram import Bot
from config import DEV_ID

async def send_goodnight(bot: Bot):
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow("SELECT goodnight_id FROM world_state LIMIT 1")
        current_id = row['goodnight_id'] if row else 1000

        message_text = f"🌙 <b>Капібарної ночі всім чатерам!</b>\nhttps://t.me/dobranich_kapy/{current_id}"

        chat_rows = await conn.fetch("SELECT DISTINCT unnest(chats) as chat_id FROM users")
        
        target_ids = set()
        for r in chat_rows:
            try:
                cid = int(r['chat_id'])
                if cid < 0: target_ids.add(cid)
            except: continue
        
        target_ids.add(DEV_ID)

        success, errors = 0, 0
        for cid in target_ids:
            try:
                await bot.send_message(
                    chat_id=cid,
                    text=message_text,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
                success += 1
                await asyncio.sleep(0.35) 
            except Exception as e:
                errors += 1
                continue

        await conn.execute("UPDATE world_state SET goodnight_id = goodnight_id + 1")

        report = (
            f"📊 <b>Звіт розсилки:</b>\n"
            f"✅ Успішно: {success}\n"
            f"❌ Помилок: {errors}\n"
            f"🆔 Наступний пост: {current_id + 1}"
        )
        await bot.send_message(ADMIN_ID, report, parse_mode="HTML")

    finally:
        await conn.close()
