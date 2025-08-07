from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio

scheduler = AsyncIOScheduler()
scheduler.start()

def schedule_reminder(bot, chat_id, text, time_str):
    try:
        hour, minute = map(int, time_str.split(":"))
        now = datetime.now()
        remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_time < now:
            remind_time = remind_time.replace(day=now.day + 1)

        scheduler.add_job(
            bot.send_message,
            'date',
            run_date=remind_time,
            args=[chat_id, f"🔔 Нагадування: {text}"]
        )
    except Exception as e:
        print("Помилка при плануванні:", e)