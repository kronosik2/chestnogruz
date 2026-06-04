import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from supabase import create_client, Client

# ========== НАСТРОЙКИ (ЗАМЕНИ НА СВОИ!) ==========
SUPABASE_URL = "https://ivcyfesmatauphiflitn.supabase.co"
SUPABASE_KEY = "sb_publishable_vvCmbHarhj33E7mZ0c_Sxw_Hy9XEfHI"
TELEGRAM_BOT_TOKEN = "8727111036:AAEtREM0b27n7m6Ue9jUKQYhPnD4Pz2iF88"

# Инициализация
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_user_by_telegram_id(telegram_id: int):
    """Получить пользователя из Supabase по telegram_id"""
    try:
        result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def get_user_by_phone(phone: str):
    """Получить пользователя по телефону"""
    try:
        result = supabase.table("users").select("*").eq("phone", phone).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def create_user(telegram_id: int, phone: str, name: str, city: str = None):
    """Создать нового пользователя (грузчика)"""
    try:
        data = {
            "telegram_id": telegram_id,
            "phone": phone,
            "name": name,
            "role": "worker",
            "city": city,
            "rating": 5.0,
            "debt": 0
        }
        result = supabase.table("users").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Ошибка создания: {e}")
        return None

def update_user_city(telegram_id: int, city: str):
    """Обновить город пользователя"""
    try:
        supabase.table("users").update({"city": city}).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def get_active_orders_by_city(city: str):
    """Получить активные заказы в городе"""
    try:
        result = supabase.table("orders").select("*").eq("city", city).eq("status", "new").execute()
        return result.data
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def get_order(order_id: str):
    """Получить заказ по ID"""
    try:
        result = supabase.table("orders").select("*").eq("id", order_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def create_response(order_id: str, worker_telegram_id: int):
    """Создать отклик на заказ"""
    try:
        # Сначала получаем worker_id из users
        user = get_user_by_telegram_id(worker_telegram_id)
        if not user:
            return None
        
        data = {
            "order_id": order_id,
            "worker_id": user["id"],
            "status": "pending"
        }
        result = supabase.table("responses").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def get_active_response(worker_telegram_id: int):
    """Получить активный отклик грузчика"""
    try:
        user = get_user_by_telegram_id(worker_telegram_id)
        if not user:
            return None
        
        result = supabase.table("responses").select("*, orders(*)").eq("worker_id", user["id"]).eq("status", "pending").execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def cancel_response(response_id: str):
    """Отозвать отклик"""
    try:
        supabase.table("responses").update({"status": "cancelled"}).eq("id", response_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def get_worker_orders_history(worker_telegram_id: int):
    """Получить историю выполненных заказов грузчика"""
    try:
        user = get_user_by_telegram_id(worker_telegram_id)
        if not user:
            return []
        
        result = supabase.table("responses").select("*, orders(*)").eq("worker_id", user["id"]).eq("status", "completed").execute()
        return result.data
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def update_response_status(response_id: str, status: str):
    """Обновить статус отклика"""
    try:
        supabase.table("responses").update({"status": status}).eq("id", response_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    """Главное меню (4 кнопки)"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Лента заказов")],
            [KeyboardButton(text="📦 Мои заказы")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📩 Входящие")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_city_keyboard():
    """Клавиатура выбора города"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Москва"), KeyboardButton(text="Санкт-Петербург")],
            [KeyboardButton(text="Казань"), KeyboardButton(text="Екатеринбург")],
            [KeyboardButton(text="Новосибирск"), KeyboardButton(text="Другой")]
        ],
        resize_keyboard=True
    )
    return keyboard

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    user = get_user_by_telegram_id(message.from_user.id)
    
    if user:
        await message.answer(
            f"👋 С возвращением, {user['name']}!\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Запрашиваем контакт
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(
        "👋 Добро пожаловать в ЧестноГруз!\n\n"
        "Мы помогаем грузчикам находить заказы без комиссий.\n\n"
        "Для регистрации нажмите кнопку и поделитесь номером телефона:",
        reply_markup=contact_keyboard
    )

@dp.message(lambda message: message.contact)
async def handle_contact(message: types.Message):
    """Обработка полученного контакта"""
    contact = message.contact
    phone = contact.phone_number
    name = contact.first_name
    
    # Сохраняем временные данные (ждём город)
    # Используем кэш в памяти для простоты
    if not hasattr(handle_contact, "temp_users"):
        handle_contact.temp_users = {}
    handle_contact.temp_users[message.from_user.id] = {"phone": phone, "name": name}
    
    await message.answer(
        f"✅ Отлично, {name}!\n\nТеперь выберите город, в котором вы работаете:",
        reply_markup=get_city_keyboard()
    )

@dp.message(lambda message: message.text in ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск", "Другой"])
async def handle_city(message: types.Message):
    """Обработка выбора города"""
    city = message.text
    if city == "Другой":
        await message.answer("📍 Напишите название вашего города:")
        return
    
    # Завершаем регистрацию
    temp_data = getattr(handle_contact, "temp_users", {}).get(message.from_user.id)
    if not temp_data:
        await message.answer("❌ Ошибка. Пожалуйста, начните регистрацию заново с команды /start")
        return
    
    user = create_user(
        telegram_id=message.from_user.id,
        phone=temp_data["phone"],
        name=temp_data["name"],
        city=city
    )
    
    if user:
        await message.answer(
            f"🎉 Регистрация завершена!\n\n"
            f"Добро пожаловать, {user['name']}!\n"
            f"📍 Город: {city}\n\n"
            f"Теперь вы можете получать заказы.",
            reply_markup=get_main_keyboard()
        )
        # Очищаем временные данные
        del handle_contact.temp_users[message.from_user.id]
    else:
        await message.answer("❌ Ошибка регистрации. Попробуйте позже.")

@dp.message(lambda message: message.text == "📋 Лента заказов")
async def show_feed(message: types.Message):
    """Показать ленту заказов"""
    user = get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await cmd_start(message)
        return
    
    if not user.get("city"):
        await message.answer("📍 Сначала укажите город в профиле.")
        return
    
    orders = get_active_orders_by_city(user["city"])
    
    if not orders:
        await message.answer("📭 Пока нет активных заказов в вашем городе.")
        return
    
    for order in orders:
        text = (
            f"🆕 *Новый заказ!*\n\n"
            f"📍 {order['city']}, {order['address']}\n"
            f"📅 {order['date']} {order['time']}\n"
            f"👥 {order['грузчиков']} грузчика\n"
            f"💰 {order.get('rate', 400)}₽/час\n"
            f"💬 {order.get('comment', '—')}\n\n"
            f"*Заказ #{order['id'][:6]}*"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Откликнуться", callback_data=f"respond_{order['id']}")]]
        )
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.message(lambda message: message.text == "📦 Мои заказы")
async def show_my_orders(message: types.Message):
    """Показать мои заказы (активный отклик + история)"""
    user = get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await cmd_start(message)
        return
    
    # Активный отклик
    active = get_active_response(message.from_user.id)
    
    if active:
        order = active.get("orders", {})
        text = (
            f"🏠 *Активный заказ*\n\n"
            f"📍 {order.get('city', '—')}, {order.get('address', '—')}\n"
            f"📅 {order.get('date', '—')} {order.get('time', '—')}\n"
            f"👥 {order.get('грузчиков', '—')} грузчика\n"
            f"💰 {order.get('rate', 400)}₽/час\n\n"
            f"⏳ Статус: *ожидает одобрения клиента*"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отозвать отклик", callback_data=f"cancel_{active['id']}")]]
        )
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.answer("📭 У вас нет активных откликов.")
    
    # История заказов
    history = get_worker_orders_history(message.from_user.id)
    
    if history:
        history_text = "📜 *История выполненных заказов:*\n\n"
        for resp in history[:5]:  # Показываем последние 5
            order = resp.get("orders", {})
            history_text += f"✅ {order.get('date', '—')} — {order.get('city', '—')}, {order.get('address', '—')}\n"
        await message.answer(history_text, parse_mode="Markdown")

@dp.message(lambda message: message.text == "👤 Профиль")
async def show_profile(message: types.Message):
    """Показать профиль"""
    user = get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await cmd_start(message)
        return
    
    text = (
        f"👤 *{user.get('name', '—')}*\n\n"
        f"📱 {user.get('phone', '—')}\n"
        f"⭐ Рейтинг: {user.get('rating', 5.0)}\n"
        f"📍 Город: {user.get('city', '—')}\n"
        f"💰 *Долг: {user.get('debt', 0)} ₽*\n"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить город", callback_data="change_city")],
            [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
        ]
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.message(lambda message: message.text == "📩 Входящие")
async def show_inbox(message: types.Message):
    """Показать входящие (технические сообщения)"""
    # Здесь будут уведомления об одобрении заказов и другие системные сообщения
    await message.answer(
        "📬 *Входящие*\n\n"
        "Здесь будут появляться уведомления:\n"
        "• ✅ Одобрение заказа клиентом\n"
        "• 💳 Напоминания о долгах\n"
        "• 📞 Контакты клиентов\n\n"
        "Пока новых сообщений нет.",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text and not message.text.startswith("/"))
async def handle_free_text(message: types.Message):
    """Обработка свободного текста (для города "Другой")"""
    user = get_user_by_telegram_id(message.from_user.id)
    if user:
        await message.answer("Используйте кнопки меню.", reply_markup=get_main_keyboard())
        return
    
    # Если пользователь не зарегистрирован и ввёл город
    temp_data = getattr(handle_contact, "temp_users", {}).get(message.from_user.id)
    if temp_data:
        city = message.text
        user = create_user(
            telegram_id=message.from_user.id,
            phone=temp_data["phone"],
            name=temp_data["name"],
            city=city
        )
        if user:
            await message.answer(
                f"🎉 Регистрация завершена!\n\n"
                f"Добро пожаловать, {user['name']}!\n"
                f"📍 Город: {city}\n\n"
                f"Теперь вы можете получать заказы.",
                reply_markup=get_main_keyboard()
            )
            del handle_contact.temp_users[message.from_user.id]
        else:
            await message.answer("❌ Ошибка регистрации. Попробуйте /start заново.")

# ========== ОБРАБОТЧИКИ CALLBACK'ОВ ==========

@dp.callback_query(lambda c: c.data.startswith("respond_"))
async def respond_to_order(callback: types.CallbackQuery):
    """Откликнуться на заказ"""
    order_id = callback.data.split("_")[1]
    
    # Создаём отклик
    result = create_response(order_id, callback.from_user.id)
    
    if result:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "✅ Вы откликнулись на заказ!\n\n"
            "Заказ появился в разделе «Мои заказы» в статусе ожидания.\n"
            "Как только клиент одобрит — мы вам сообщим."
        )
    else:
        await callback.message.answer("❌ Не удалось откликнуться. Попробуйте позже.")
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("cancel_"))
async def cancel_response_handler(callback: types.CallbackQuery):
    """Отозвать отклик"""
    response_id = callback.data.split("_")[1]
    
    if cancel_response(response_id):
        await callback.message.edit_text("❌ Отклик отозван.", reply_markup=None)
        await callback.answer("Отклик отозван")
    else:
        await callback.answer("Ошибка при отзыве")

@dp.callback_query(lambda c: c.data == "change_city")
async def change_city(callback: types.CallbackQuery):
    """Изменить город"""
    await callback.message.answer("📍 Выберите новый город:", reply_markup=get_city_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "logout")
async def logout(callback: types.CallbackQuery):
    """Выход"""
    await callback.message.answer("👋 До свидания! Для входа используйте /start")
    await callback.answer()

# ========== ЗАПУСК БОТА ==========

async def main():
    print("🤖 Бот ЧестноГруз запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
