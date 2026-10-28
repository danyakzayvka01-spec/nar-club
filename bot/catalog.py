# Серверный каталог: цены из браузера никогда не принимаются.
MENU = [
    {"id": "cola", "category": "Бар", "name": "Кола 0,33 л", "price": 350},
    {"id": "water", "category": "Бар", "name": "Вода 0,5 л", "price": 250},
    {"id": "gin_tonic", "category": "Бар", "name": "Джин-тоник", "price": 850},
    {"id": "fries", "category": "Кухня", "name": "Картофель фри", "price": 550},
    {"id": "cheese_plate", "category": "Кухня", "name": "Сырная тарелка", "price": 1200},
    {"id": "club_sandwich", "category": "Кухня", "name": "Клаб-сэндвич", "price": 950},
    {"id": "hookah_light", "category": "Кальян", "name": "Кальян — лёгкий", "price": 2500},
    {"id": "hookah_strong", "category": "Кальян", "name": "Кальян — крепкий", "price": 2800},
]

CATEGORY_CHAT_ENV = {
    "Бар": "bar_chat_id",
    "Кухня": "kitchen_chat_id",
    "Кальян": "hookah_chat_id",
}

MAX_ITEM_QUANTITY = 20
MAX_ORDER_TOTAL = 1_000_000
