# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3

# ========================================================
# НАСТРОЙКА: Вставьте сюда ваш токен от @BotFather
# ========================================================
TOKEN = "8878082403:AAEFq9jyQn3hwLX8C6..."

# ========================================================
# БЛОК 1: РАБОТА С БАЗОЙ ДАННЫХ (SQLite)
# ========================================================
def init_db():
    """Создает базу данных с учетом категорий техники"""
    conn = sqlite3.connect('autotrust.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trucks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER UNIQUE,
            driver_name TEXT,
            category TEXT,
            truck_info TEXT,
            city TEXT,
            status TEXT DEFAULT 'Свободен'
        )
    ''')
    conn.commit()
    conn.close()

def add_or_update_truck(driver_id, driver_name, category, truck_info, city):
    """Записывает машину водителя с привязкой к категории"""
    conn = sqlite3.connect('autotrust.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO trucks (driver_id, driver_name, category, truck_info, city, status)
        VALUES (?, ?, ?, ?, ?, 'Свободен')
    ''', (driver_id, driver_name, category, truck_info, city))
    conn.commit()
    conn.close()

def get_free_trucks_by_category(category):
    """Ищет свободную технику только в выбранной категории"""
    conn = sqlite3.connect('autotrust.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT truck_info, city, driver_name FROM trucks WHERE category = ? AND status = 'Свободен'", 
        (category,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_driver_truck(driver_id):
    """Получает профиль машины водителя"""
    conn = sqlite3.connect('autotrust.db')
    cursor = conn.cursor()
    cursor.execute("SELECT category, truck_info, city, status FROM trucks WHERE driver_id = ?", (driver_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_truck_status(driver_id, new_status):
    """Быстрая смена статуса (Свободен/Занят)"""
    conn = sqlite3.connect('autotrust.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE trucks SET status = ? WHERE driver_id = ?", (new_status, driver_id))
    conn.commit()
    conn.close()


# Запуск базы данных
init_db()

# Временная память телефона для регистрации водителей
user_states = {}
STATE_CHOOSE_CATEGORY = 1
STATE_WAITING_FOR_INFO = 2
STATE_WAITING_FOR_CITY = 3

# Шаблонные категории спецтехники
CATEGORIES = ["🚚 Грузовые машины", "🚜 Погрузчики", "🏗️ Краны и Манипуляторы"]


# ========================================================
# БЛОК 2: ЛОГИКА ТЕЛЕГРАМ-БОТА
# ========================================================

# Команда /start (Приветствие)
@bot.message_handler(commands=['start'])
def start_handler(message):
    welcome_text = (
        f"Здравствуйте, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в сервис Автотраст.\n"
        "Какая техника вам требуется? Выберите нужный раздел на кнопках ниже, "
        "чтобы найти свободный транспорт прямо сейчас."
    )
    
    # Главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_find = types.KeyboardButton("🔍 Найти свободную технику (Каталог)")
    btn_add = types.KeyboardButton("📦 Разместить свой транспорт")
    btn_status = types.KeyboardButton("👤 Мой статус (Занят/Свободен)")
    
    markup.add(btn_find, btn_add, btn_status)
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# КЛИЕНТ: Нажатие кнопки "Найти технику" -> Показываем категории-шаблоны
@bot.message_handler(func=lambda msg: msg.text == "🔍 Найти свободную технику (Каталог)")
def show_search_categories(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for cat in CATEGORIES:
        markup.add(types.KeyboardButton(cat))
    markup.add(types.KeyboardButton("⬅️ В главное меню"))
    
    bot.send_message(message.chat.id, "Какая техника вам требуется?", reply_markup=markup)


# КЛИЕНТ: Выбор конкретной категории из шаблона
@bot.message_handler(func=lambda msg: msg.text in CATEGORIES)
def search_trucks_by_cat(message):
    selected_cat = message.text
    trucks = get_free_trucks_by_category(selected_cat)
    
    if not trucks:
        bot.send_message(
            message.chat.id, 
            f"В категории *{selected_cat}* сейчас нет свободных машин. Попробуйте выбрать другую категорию.",
            parse_mode="Markdown"
        )
        return
        
    response = f"📋 *Свободный транспорт в категории [{selected_cat}]:*\n\n"
    for truck in trucks:
        info, city, driver = truck
        response += f"• *Описание:* {info}\n  *Локация:* {city}\n  *Контакты:* {driver}\n\n"
        
    bot.send_message(message.chat.id, response, parse_mode="Markdown")


# КНОПКА: Возврат в главное меню
@bot.message_handler(func=lambda msg: msg.text == "⬅️ В главное меню")
def back_to_menu(message):
    start_handler(message)


# ВОДИТЕЛЬ: Регистрация транспорта (Пошаговый шаблон)
@bot.message_handler(func=lambda msg: msg.text == "📦 Разместить свой транспорт")
def add_truck_start(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'state': STATE_CHOOSE_CATEGORY}
    
    # Кнопки выбора категории для водителя
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for cat in CATEGORIES:
        markup.add(types.KeyboardButton(cat))
        
    bot.send_message(chat_id, "Шаг 1: Выберите категорию вашего транспорта:", reply_markup=markup)


# Обработка шагов анкеты водителя
@bot.message_handler(func=lambda msg: msg.chat.id in user_states)
def process_driver_steps(message):
    chat_id = message.chat.id
    state = user_states[chat_id]['state']
    
    if state == STATE_CHOOSE_CATEGORY:
        if message.text not in CATEGORIES:
            bot.send_message(chat_id, "Пожалуйста, выберите категорию, используя кнопки на экране.")
            return
            
        user_states[chat_id]['category'] = message.text
        user_states[chat_id]['state'] = STATE_WAITING_FOR_INFO
        
        # Убираем клавиатуру категорий, просим написать параметры
        markup = types.ReplyKeyboardRemove()
        text = (
            "Шаг 2: Напишите подробнее *марку и параметры*.\n"
            "_(Пример: Газель до 3 тонн / Манипулятор 5 тонн, стрела 3 тонны)_"
        )
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif state == STATE_WAITING_FOR_INFO:
        user_states[chat_id]['info'] = message.text
        user_states[chat_id]['state'] = STATE_WAITING_FOR_CITY
        
        bot.send_message(chat_id, "Шаг 3: Укажите *город или область* вашей работы (например: *Костанай*):", parse_mode="Markdown")
        
    elif state == STATE_WAITING_FOR_CITY:
        category = user_states[chat_id]['category']
        truck_info = user_states[chat_id]['info']
        city = message.text
        
        if message.from_user.username:
            driver_name = f"@{message.from_user.username}"
        else:
            driver_name = message.from_user.first_name
            
        # Запись в базу данных
        add_or_update_truck(chat_id, driver_name, category, truck_info, city)
        del user_states[chat_id]
        
        # Возвращаем водителю главное меню управления
        success_text = (
            "✅ *Транспорт успешно добавлен!*\n\n"
            f"Категория: *{category}*\n"
            f"Транспорт: *{truck_info}*\n"
            f"Город: *{city}*\n"
            "Статус: *Свободен*."
        )
        bot.send_message(chat_id, success_text, parse_mode="Markdown")
        start_handler(message)


# УПРАВЛЕНИЕ СТАТУСОМ (Свободен/Занят)
@bot.message_handler(func=lambda msg: msg.text == "👤 Мой статус (Занят/Свободен)")
def status_menu_handler(message):
    chat_id = message.chat.id
    truck = get_driver_truck(chat_id)
    
    if not truck:
        bot.send_message(chat_id, "Вы еще не зарегистрировали свой транспорт. Нажмите «📦 Разместить свой транспорт».")
        return
        
    category, info, city, current_status = truck
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_free = types.InlineKeyboardButton("🟢 Я СВОБОДЕН", callback_data="set_free")
    btn_busy = types.InlineKeyboardButton("🔴 Я ЗАНЯТ", callback_data="set_busy")
    markup.add(btn_free, btn_busy)
    
    status_emoji = "🟢" if current_status == "Свободен" else "🔴"
    
    text = (
        "💼 *Управление вашей техникой:*\n\n"
        f"• Категория: {category}\n"
        f"• Машина: {info}\n"
        f"• Город: {city}\n"
        f"• Сейчас вы: {status_emoji} *{current_status}*\n\n"
        "Переключайте статус кнопками ниже, чтобы клиенты видели актуальную информацию."
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


# Обработка кликов по кнопкам статуса
@bot.callback_query_handler(func=lambda call: call.data in ["set_free", "set_busy"])
def callback_status_update(call):
    chat_id = call.message.chat.id
    new_status = "Свободен" if call.data == "set_free" else "Занят"
    status_emoji = "🟢" if new_status == "Свободен" else "🔴"
    
    update_truck_status(chat_id, new_status)
    bot.answer_callback_query(call.id, text=f"Статус изменен на: {new_status}")
    
    category, info, city, current_status = get_driver_truck(chat_id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_free = types.InlineKeyboardButton("🟢 Я СВОБОДЕН", callback_data="set_free")
    btn_busy = types.InlineKeyboardButton("🔴 Я ЗАНЯТ", callback_data="set_busy")
    markup.add(btn_free, btn_busy)
    
    updated_text = (
        "💼 *Управление вашей техникой:*\n\n"
        f"• Категория: {category}\n"
        f"• Машина: {info}\n"
        f"• Город: {city}\n"
        f"• Сейчас вы: {status_emoji} *{current_status}*\n\n"
        "Статус успешно обновлен!"
    )
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=updated_text, reply_markup=markup, parse_mode="Markdown")


# ========================================================
# ЗАПУСК БОТА
# ========================================================
if __name__ == '__main__':
    print("Бот Автотраст готов к тестам через мобильный онлайн-Python...")
    bot.polling(none_stop=Trueд)
