import telebot
import threading
import time
import re
import requests
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv
import telebot

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
# 🗂️ Списки для нагадувань і координат користувачів
reminders = []
user_locations = {}  # chat_id → (lat, lon)

# 📍 Команда /start — інструкція для користувача
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "Привіт! Я бот-нагадувач 📅\n\n"
        "Просто напиши щось типу:\n"
        "👉 завтра день народження мами\n"
        "👉 зустріч 12.09\n"
        "І я нагадаю тобі у цей день + надішлю прогноз погоди!\n\n"
        "Щоб прогноз був точним — напиши своє місто:\n"
        "📝 приклад: \"місто Нью-Йорк\", \"город Нью-Йорк\", \"city New York\"\n"
        "Або просто запитай: \"погода Київ\""
    )

# 📅 Функція для розпізнавання дати з тексту
def extract_date(text):
    text = text.lower()
    today = datetime.now().date()

    if "завтра" in text:
        return today + timedelta(days=1)

    months = {
        'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
        'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
        'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
    }

    match = re.search(r'(\d{1,2})[.\-/](\d{1,2})', text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        try:
            return datetime(datetime.now().year, month, day).date()
        except:
            return None

    match = re.search(r'(\d{1,2})\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)', text)
    if match:
        day = int(match.group(1))
        month = months.get(match.group(2))
        try:
            return datetime(datetime.now().year, month, day).date()
        except:
            return None

    return None

# 🗺️ Отримання координат міста через OpenStreetMap
def get_coordinates_by_city(city_name):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={city_name}"
    try:
        response = requests.get(url, headers={"User-Agent": "weather-bot"})
        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
    except:
        pass
    return None

# 🌤 Отримання прогнозу погоди через Open-Meteo
def get_weather_forecast(date_obj, lat=52.4420, lon=4.8292, hour=12):
    date_str = date_obj.strftime('%Y-%m-%d')
    hour_str = f"{hour:02d}:00"
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&hourly=temperature_2m,"
        f"relative_humidity_2m,wind_speed_10m&timezone=Europe/Amsterdam"
    )
    try:
        response = requests.get(url)
        data = response.json()
        target_time = f"{date_str}T{hour_str}"
        index = data['hourly']['time'].index(target_time)
        temp = data['hourly']['temperature_2m'][index]
        humidity = data['hourly']['relative_humidity_2m'][index]
        wind = data['hourly']['wind_speed_10m'][index]

        if temp >= 20 and humidity < 60:
            comment = "☀ Гарний день! Не забудь окуляри 😎"
        elif humidity > 80 or wind > 10:
            comment = "🌧 Може бути непогода — будь обережний!"
        else:
            comment = "🌤 Звичайна погода, все ок!"

        return f"{temp}°C, вологість {humidity}%, вітер {wind} км/год\n{comment}"
    except:
        return "⚠️ Не вдалося отримати прогноз погоди"

# 💬 Обробка повідомлень користувача
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    # 🏙️ Збереження міста вручну
    if any(text.lower().startswith(prefix) for prefix in ["місто ", "город ", "city "]):
        city_name = re.sub(r"^(місто|город|city)\s+", "", text, flags=re.IGNORECASE).strip()
        coords = get_coordinates_by_city(city_name)
        if coords:
            user_locations[message.chat.id] = coords
            bot.send_message(message.chat.id, f"✅ Місто \"{city_name}\" збережено!")
        else:
            bot.send_message(message.chat.id, f"⚠️ Не вдалося знайти місто \"{city_name}\"")
        return

    # 🌦 Запит погоди вручну
    if text.lower().startswith("погода "):
        city_name = text[7:].strip()
        coords = get_coordinates_by_city(city_name)
        if coords:
            user_locations[message.chat.id] = coords
            forecast = get_weather_forecast(datetime.now().date(), lat=coords[0], lon=coords[1])
            bot.send_message(message.chat.id, f"🌦 Погода в \"{city_name}\":\n{forecast}")
        else:
            bot.send_message(message.chat.id, f"⚠️ Не вдалося знайти місто \"{city_name}\"")
        return

    # 📅 Якщо є дата — зберігаємо нагадування
    date = extract_date(text)
    if date:
        reminders.append((message.chat.id, date, text))
        latlon = user_locations.get(message.chat.id, (52.4420, 4.8292))
        forecast = get_weather_forecast(date, lat=latlon[0], lon=latlon[1])
        bot.send_message(
            message.chat.id,
            f"✅ Нагадування збережено на {date.strftime('%d.%m')}\n"
            f"🌦 Прогноз погоди: {forecast}"
        )
    else:
        bot.send_message(
            message.chat.id,
            "🤔 Я не знайшов дату в повідомленні.\n"
            "Напиши щось типу: \"зустріч 12.09\" або \"завтра день народження мами\"\n"
            "Або вкажи своє місто: \"місто Київ\"\n"
            "Або просто запитай: \"погода Львів\""
        )

# 🔄 Перевірка нагадувань щогодини
def reminder_checker():
    while True:
        today = datetime.now().date()
        for r in reminders[:]:
            chat_id, r_date, text = r
            if r_date == today:
                bot.send_message(chat_id, f"📌 Сьогодні: {text}")
                reminders.remove(r)
        time.sleep(3600)

# 🚀 Запуск бота
threading.Thread(target=reminder_checker).start()
bot.polling()