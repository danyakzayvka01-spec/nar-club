from aiogram import Bot
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from .config import Settings

load_dotenv(Path(__file__).resolve().parent / ".env")

async def main():
    settings = Settings.from_env()
    bot = Bot(settings.bot_token)
    webhook_url = settings.web_app_url.rstrip("/") + "/api/telegram/webhook"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret,
        allowed_updates=["message"],
    )
    info = await bot.get_webhook_info()
    print(f"Webhook установлен: {info.url}")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
