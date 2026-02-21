import os
import json
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BOOKINGS_FILE = "bookings.json"

# ================== CONFIG DREAM SOURCIL ==================

ADDRESS_TEXT = "📍 Adresse :\n58 avenue Corot, 13013 Marseille"

HALAL_BROW_INFO = (
    "🤍 Halal Brow (Woudhou friendly)\n\n"
    "Restructuration du sourcil sans épilation.\n"
    "Rendu net, naturel et respectueux de vos valeurs.\n\n"
    "Lorsque la prestation est réalisée uniquement par décoloration "
    "du surplus (sans teinture ni browlift), elle est compatible avec "
    "les ablutions."
)

SERVICES_BROWS = [
    {"id": "classic", "name": "Classic Brow", "duration": 30, "price": "15€"},
    {"id": "classic_restruct", "name": "Classic Brow – Restructuration", "duration": 20, "price": "20€"},
    {"id": "henna", "name": "Henna Brow", "duration": 45, "price": "25€"},
    {"id": "henna_halal", "name": "Henna Brow – Sans Épilation (Halal Brow)", "duration": 45, "price": "30€"},
    {"id": "hybrid", "name": "Hybrid Brow", "duration": 45, "price": "30€"},
    {"id": "hybrid_tint", "name": "Hybrid Brow – Teinture hybride", "duration": 45, "price": "35€"},
    {"id": "browlift", "name": "Browlift – Restructuration", "duration": 45, "price": "50€"},
    {"id": "dream_browlift", "name": "Dream Browlift – Forfait complet", "duration": 75, "price": "60€"},
]

SERVICES_LASHES = [
    {"id": "lashlift", "name": "Lash Lift Simple", "duration": 60, "price": "40€"},
]

OPEN_WEEKDAYS = {1, 3, 4, 5}  # mardi, jeudi, vendredi, samedi
START_TIME = time(9, 30)
END_TIME = time(15, 45)
SLOT_STEP_MIN = 15
DAYS_LOOKAHEAD = 35

# ================== UTILS ==================

def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return []
    with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)

def parse_dt(date_str, time_str):
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def slot_available(date_str, time_str, duration):
    start = parse_dt(date_str, time_str)
    end = start + timedelta(minutes=duration)

    day_start = datetime.combine(start.date(), START_TIME)
    day_end = datetime.combine(start.date(), END_TIME)

    if start < day_start or end > day_end + timedelta(minutes=1):
        return False

    for b in load_bookings():
        if b["date"] != date_str:
            continue
        b_start = parse_dt(b["date"], b["time"])
        b_end = b_start + timedelta(minutes=b["duration"])
        if overlaps(start, end, b_start, b_end):
            return False
    return True

# ================== MENUS ==================

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Prendre RDV", callback_data="rdv")],
        [InlineKeyboardButton("💶 Tarifs", callback_data="tarifs")],
        [InlineKeyboardButton("📍 Adresse", callback_data="adresse")],
        [InlineKeyboardButton("🤍 Infos Halal Brow", callback_data="halal")],
    ])

def categories_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💄 Sourcils", callback_data="cat_brows")],
        [InlineKeyboardButton("👁️ Cils", callback_data="cat_lashes")],
        [InlineKeyboardButton("⬅️ Menu", callback_data="menu")],
    ])

def services_menu(services):
    rows = []
    for s in services:
        rows.append([InlineKeyboardButton(
            f"{s['name']} — {s['price']} ({s['duration']} min)",
            callback_data=f"service_{s['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="categories")])
    return InlineKeyboardMarkup(rows)

def days_menu():
    rows = []
    today = datetime.now().date()
    for i in range(DAYS_LOOKAHEAD):
        d = today + timedelta(days=i)
        if d.weekday() in OPEN_WEEKDAYS:
            label = d.strftime("%a %d/%m").replace("Tue","Mar").replace("Thu","Jeu").replace("Fri","Ven").replace("Sat","Sam")
            rows.append([InlineKeyboardButton(label, callback_data=f"day_{d}")])
    rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="services")])
    return InlineKeyboardMarkup(rows)

def slots_menu(date_str, duration):
    rows = []
    t = datetime.combine(datetime.now().date(), START_TIME)
    end = datetime.combine(datetime.now().date(), END_TIME)
    while t <= end:
        time_str = t.strftime("%H:%M")
        if slot_available(date_str, time_str, duration):
            rows.append([InlineKeyboardButton(f"✅ {time_str}", callback_data=f"slot_{date_str}_{time_str}")])
        else:
            rows.append([InlineKeyboardButton(f"⛔ {time_str}", callback_data="noop")])
        t += timedelta(minutes=SLOT_STEP_MIN)
    rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="days")])
    return InlineKeyboardMarkup(rows)

# ================== HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Bienvenue chez ✨ Dream Sourcil ✨\n\n"
        "Je t’aide à prendre ton rendez-vous et à retrouver toutes les infos.",
        reply_markup=main_menu()
    )

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu":
        await q.edit_message_text("Menu principal 👇", reply_markup=main_menu())

    elif data == "rdv":
        await q.edit_message_text("Choisis une catégorie 👇", reply_markup=categories_menu())

    elif data == "categories":
        await q.edit_message_text("Choisis une catégorie 👇", reply_markup=categories_menu())

    elif data == "cat_brows":
        context.user_data["services"] = SERVICES_BROWS
        await q.edit_message_text("💄 Choisis ta prestation sourcils 👇", reply_markup=services_menu(SERVICES_BROWS))

    elif data == "cat_lashes":
        context.user_data["services"] = SERVICES_LASHES
        await q.edit_message_text("👁️ Choisis ta prestation cils 👇", reply_markup=services_menu(SERVICES_LASHES))

    elif data.startswith("service_"):
        service_id = data.replace("service_", "")
        service = next(s for s in context.user_data["services"] if s["id"] == service_id)
        context.user_data["service"] = service
        await q.edit_message_text(
            f"✨ {service['name']}\n⏱ {service['duration']} min\n💶 {service['price']}\n\nChoisis une date 👇",
            reply_markup=days_menu()
        )

    elif data.startswith("day_"):
        date_str = data.replace("day_", "")
        context.user_data["date"] = date_str
        service = context.user_data["service"]
        await q.edit_message_text(
            f"📅 {date_str}\nChoisis une heure 👇",
            reply_markup=slots_menu(date_str, service["duration"])
        )

    elif data.startswith("slot_"):
        _, date_str, time_str = data.split("_")
        service = context.user_data["service"]

        if not slot_available(date_str, time_str, service["duration"]):
            await q.edit_message_text("⛔ Créneau indisponible, choisis-en un autre.")
            return

        bookings = load_bookings()
        bookings.append({
            "date": date_str,
            "time": time_str,
            "duration": service["duration"],
            "service": service["name"]
        })
        save_bookings(bookings)

        end_time = (parse_dt(date_str, time_str) + timedelta(minutes=service["duration"])).strftime("%H:%M")

        await q.edit_message_text(
            "✅ RDV confirmé !\n\n"
            f"✨ {service['name']}\n"
            f"📅 {date_str}\n"
            f"🕒 {time_str} → {end_time}\n\n"
            f"{ADDRESS_TEXT}",
            reply_markup=main_menu()
        )

    elif data == "tarifs":
        text = "💶 Tarifs :\n"
        for s in SERVICES_BROWS + SERVICES_LASHES:
            text += f"- {s['name']} : {s['price']} ({s['duration']} min)\n"
        await q.edit_message_text(text, reply_markup=main_menu())

    elif data == "adresse":
        await q.edit_message_text(ADDRESS_TEXT, reply_markup=main_menu())

    elif data == "halal":
        await q.edit_message_text(HALAL_BROW_INFO, reply_markup=main_menu())

def run():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.run_polling()

if __name__ == "__main__":
    run()
