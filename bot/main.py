import asyncio, hashlib, hmac, html, json, logging, time, uuid
from datetime import datetime
from urllib.parse import parse_qsl
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from fastapi import Request
from aiogram.types import Update
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")
from .catalog import MENU, CATEGORY_CHAT_ENV, MAX_ITEM_QUANTITY, MAX_ORDER_TOTAL
from .config import Settings
from .sheets import SheetsStore

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
settings=Settings.from_env(); bot=Bot(token=settings.bot_token); dispatcher=Dispatcher(); sheets=SheetsStore(settings)
app=FastAPI(title="Nightshift Waiter API",docs_url=None,redoc_url=None)
class ItemRequest(BaseModel):
 product_id:str=Field(min_length=1,max_length=64)
 quantity:int=Field(ge=1,le=MAX_ITEM_QUANTITY)
class OrderRequest(BaseModel):
 table:int=Field(ge=1)
 items:list[ItemRequest]=Field(min_length=1,max_length=40)

def validate_init_data(raw:str)->dict:
 """Проверяет Telegram-подпись и срок действия данных пользователя."""
 if not raw or len(raw)>8192: raise HTTPException(401,"Нет данных авторизации Telegram")
 values=dict(parse_qsl(raw,keep_blank_values=True)); received_hash=values.pop("hash",None)
 if not received_hash: raise HTTPException(401,"В initData отсутствует подпись")
 check_string="\n".join(f"{key}={value}" for key,value in sorted(values.items()))
 secret_key=hmac.new(b"WebAppData",settings.bot_token.encode(),hashlib.sha256).digest()
 expected=hmac.new(secret_key,check_string.encode(),hashlib.sha256).hexdigest()
 if not hmac.compare_digest(expected,received_hash): raise HTTPException(401,"Подпись Telegram не прошла проверку")
 try: auth_date=int(values["auth_date"]); user=json.loads(values["user"])
 except (KeyError,ValueError,json.JSONDecodeError): raise HTTPException(401,"Некорректные данные Telegram")
 if time.time()-auth_date>86400 or auth_date>time.time()+60: raise HTTPException(401,"Данные авторизации устарели")
 if not isinstance(user,dict) or not user.get("id"): raise HTTPException(401,"Не найден Telegram пользователь")
 return user

@dispatcher.message(CommandStart())
async def start(message:Message):
 keyboard=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Открыть заказ",web_app=WebAppInfo(url=settings.web_app_url))]],resize_keyboard=True)
 await message.answer("Нажмите кнопку, чтобы открыть меню и оформить заказ.",reply_markup=keyboard)

@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token")):
 if not secret_token or not hmac.compare_digest(secret_token,settings.webhook_secret):
  raise HTTPException(403,"Неверный секрет Telegram webhook")
 try:
  update=Update.model_validate(await request.json(),context={"bot":bot})
  await dispatcher.feed_update(bot,update)
 except Exception:
  logging.exception("Не удалось обработать обновление Telegram")
  raise HTTPException(500,"Ошибка обработки обновления Telegram")
 return {"ok":True}

@app.get("/api/config")
async def get_config(): return {"table_count":settings.table_count}
@app.get("/api/menu")
async def get_menu(): return MENU
@app.post("/api/orders")
async def create_order(order:OrderRequest,authorization:str|None=Header(default=None)):
 if not authorization or not authorization.startswith("tma "): raise HTTPException(401,"Требуется авторизация Telegram")
 user=validate_init_data(authorization[4:])
 if int(user["id"]) not in settings.staff_ids: raise HTTPException(403,"У вас нет доступа к оформлению заказов")
 if order.table>settings.table_count: raise HTTPException(400,"Такого номера стола нет")
 catalog={item["id"]:item for item in MENU}
 if len({item.product_id for item in order.items})!=len(order.items): raise HTTPException(400,"Объедините одинаковые позиции")
 chosen=[]
 for requested in order.items:
  product=catalog.get(requested.product_id)
  if not product: raise HTTPException(400,"В заказе есть неизвестная позиция")
  chosen.append((product,requested.quantity))
 total=sum(product["price"]*quantity for product,quantity in chosen)
 if total>MAX_ORDER_TOTAL: raise HTTPException(400,"Сумма заказа превышает допустимый предел")
 first=(user.get("first_name") or "").strip(); last=(user.get("last_name") or "").strip()
 waiter=" ".join(part for part in (first,last) if part) or ("@"+user["username"] if user.get("username") else str(user["id"]))
 waiter=html.escape(waiter)
 order_id=uuid.uuid4().hex[:10].upper(); timestamp=datetime.now(ZoneInfo("Europe/Kyiv"))
 composition="; ".join(f"{p['name']} × {q} — {p['price']*q} ₽" for p,q in chosen)
 # Сначала сохраняем строку, чтобы временный сбой чата не потерял заказ.
 try: await asyncio.to_thread(sheets.append_order,[timestamp.strftime("%Y-%m-%d %H:%M:%S"),waiter,str(user["id"]),order.table,composition,total,order_id])
 except Exception:
  logging.exception("Не удалось записать заказ %s в Google Sheets",order_id)
  raise HTTPException(503,"Не удалось сохранить заказ. Повторите отправку или сообщите администратору.")
 delivery={}
 for category,env_name in CATEGORY_CHAT_ENV.items():
  category_items=[(p,q) for p,q in chosen if p["category"]==category]
  if not category_items: continue
  chat_id=getattr(settings,env_name)
  if not chat_id: delivery[category]="chat_id не задан"; logging.error("Не задан chat ID категории %s",category); continue
  lines=[f"🔔 <b>Заказ {order_id}</b>",f"Стол №{order.table} | Официант: {waiter}","<b>Заказ:</b>"]
  lines.extend(f"• {p['name']} × {q}" for p,q in category_items)
  try: await bot.send_message(chat_id,"\n".join(lines),parse_mode="HTML"); delivery[category]="sent"
  except Exception: logging.exception("Ошибка отправки в чат категории %s",category); delivery[category]="failed"
 if any(status!="sent" for status in delivery.values()): logging.error("Заказ %s записан в таблицу, но доставка требует проверки: %s",order_id,delivery)
 return {"order_id":order_id,"total":total,"delivery":delivery}
@app.get("/health")
async def health(): return {"status":"ok"}
if __name__=="__main__":
 uvicorn.run(app,host=settings.web_host,port=settings.web_port,log_level="info")



