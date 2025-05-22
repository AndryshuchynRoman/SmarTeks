import telebot
import json
import pandas as pd
import os
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

TOKEN = "7608615654:AAF6KDnMrZILIRbosDeV5yxg4YtUT103Uxg"
bot = telebot.TeleBot(TOKEN)

order_data = {}

# Завантаження кур'єрів
def load_couriers():
    global couriers
    try:
        with open("couriers.json", "r", encoding="utf-8") as file:
            couriers = json.load(file)
    except FileNotFoundError:
        couriers = []

load_couriers()

# Список міст та районів
districts = {
    "Львів": ["Франківський", "Сихівський", "Залізничний", "Галицький", "Личаківський", "Шевченківський"],
    "Київ": ["Дарницький", "Шевченківський", "Оболонський"],
    "Одеса": ["Приморський", "Київський", "Суворівський"]
}

@bot.message_handler(commands=['start'])
def start_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    order_button = KeyboardButton("🚚 Замовити кур'єра")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Виберіть дію:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🚚 Замовити кур'єра")
def start_order(message):
    chat_id = message.chat.id
    order_data.pop(chat_id, None)  # Очищення попередніх даних
    order_data[chat_id] = {"step": "from_city", "details": {}, "chat_id": chat_id}

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for city in districts.keys():
        markup.add(KeyboardButton(city))

    bot.send_message(chat_id, "Оберіть місто *звідки* надсилається посилка:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in order_data)
def collect_order_info(message):
    chat_id = message.chat.id
    step = order_data[chat_id]["step"]

    print(f"🔄 Поточний крок: {step}")

    if step == "from_city":
        if message.text in districts:
            order_data[chat_id]["details"]["Місто відправника"] = message.text
            order_data[chat_id]["step"] = "from_district"
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            for district in districts[message.text]:
                markup.add(KeyboardButton(district))
            bot.send_message(chat_id, "Оберіть район *звідки* надсилається посилка:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "❌ Невідоме місто! Оберіть зі списку.")

    elif step == "from_district":
        if message.text in districts[order_data[chat_id]["details"]["Місто відправника"]]:
            order_data[chat_id]["details"]["Район відправника"] = message.text
            order_data[chat_id]["step"] = "from_street"
            bot.send_message(chat_id, "Введіть назву вулиці *звідки* надсилається посилка:", reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(chat_id, "❌ Невідомий район! Оберіть зі списку.")

    elif step == "from_street":
        order_data[chat_id]["details"]["Вулиця відправника"] = message.text
        order_data[chat_id]["step"] = "sender_phone"
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        share_contact_button = KeyboardButton("📞 Поділитися номером", request_contact=True)
        markup.add(share_contact_button)
        bot.send_message(chat_id, "Введіть ваш номер телефону або натисніть кнопку:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_sender_contact(message):
    chat_id = message.chat.id
    if chat_id in order_data and order_data[chat_id]["step"] == "sender_phone":
        order_data[chat_id]["details"]["Телефон відправника"] = message.contact.phone_number
        order_data[chat_id]["step"] = "to_city"
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        for city in districts.keys():
            markup.add(KeyboardButton(city))
        bot.send_message(chat_id, "Оберіть місто *куди* надсилається посилка:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in order_data)
def collect_recipient_info(message):
    chat_id = message.chat.id
    step = order_data[chat_id]["step"]

    if step == "to_city":
        if message.text in districts:
            order_data[chat_id]["details"]["Місто отримувача"] = message.text
            order_data[chat_id]["step"] = "recipient_name"
            bot.send_message(chat_id, "Введіть прізвище та ім’я отримувача:")
        else:
            bot.send_message(chat_id, "❌ Невідоме місто! Оберіть зі списку.")

    elif step == "recipient_name":
        order_data[chat_id]["details"]["Ім'я отримувача"] = message.text
        order_data[chat_id]["step"] = "recipient_street"
        bot.send_message(chat_id, "Введіть назву вулиці отримувача:")

    elif step == "recipient_street":
        order_data[chat_id]["details"]["Вулиця отримувача"] = message.text
        order_data[chat_id]["step"] = "recipient_phone"
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        share_contact_button = KeyboardButton("📞 Поділитися номером", request_contact=True)
        markup.add(share_contact_button)
        bot.send_message(chat_id, "Введіть номер телефону отримувача або натисніть кнопку:", reply_markup=markup)

def finalize_order(chat_id):
    details = order_data[chat_id]["details"]
    bot.send_message(chat_id, f"✅ Ваше замовлення підтверджено!\n📌 Деталі:\n{json.dumps(details, indent=4, ensure_ascii=False)}")

bot.polling(timeout=30, long_polling_timeout=30)