from dataclasses import dataclass
import os

def required(name: str) -> str:
    value=os.getenv(name, "").strip()
    if not value: raise RuntimeError(f"Не задана обязательная переменная окружения {name}")
    return value

@dataclass(frozen=True)
class Settings:
    bot_token: str
    web_app_url: str
    web_host: str
    web_port: int
    table_count: int
    staff_ids: frozenset[int]
    bar_chat_id: str
    kitchen_chat_id: str
    hookah_chat_id: str
    spreadsheet_id: str
    worksheet_name: str
    google_credentials_file: str
    google_credentials_json: str
    webhook_secret: str
    @classmethod
    def from_env(cls):
        staff=frozenset(int(x.strip()) for x in required("STAFF_IDS").split(",") if x.strip())
        if not staff: raise RuntimeError("Переменная STAFF_IDS должна содержать Telegram ID официантов")
        return cls(required("BOT_TOKEN"),required("WEB_APP_URL"),os.getenv("WEB_HOST","0.0.0.0"),int(os.getenv("PORT","8000")),int(os.getenv("TABLE_COUNT","30")),staff,os.getenv("BAR_CHAT_ID",""),os.getenv("KITCHEN_CHAT_ID",""),os.getenv("HOOKAH_CHAT_ID",""),required("SPREADSHEET_ID"),os.getenv("WORKSHEET_NAME","Заказы"),os.getenv("GOOGLE_CREDENTIALS_FILE","service-account.json"),os.getenv("GOOGLE_CREDENTIALS_JSON",""),required("WEBHOOK_SECRET"))

