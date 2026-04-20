import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8629042091:AAHeUPC8dXykOxuSdT9zfxodi7U-sWgMZ8E"

(
    MAIN_MENU,
    WAIT_DIST, WAIT_DIST_CUSTOM,
    WAIT_TIME,
    WAIT_PACE,
    WAIT_KMH,
    LAP_DIST, LAP_DIST_CUSTOM,
    WAIT_LAP_PACE,
) = range(9)

def parse_time(text: str):
    parts = text.strip().replace(",", ":").replace(".", ":").split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        pass
    return None

def parse_float(text: str):
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None

def fmt_pace(sec: float) -> str:
    m, s = divmod(int(round(sec)), 60)
    return f"{m}:{s:02d} /км"

def fmt_time(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def fmt_dist(km: float) -> str:
    if km == int(km):
        return f"{int(km)} км"
    return f"{km} км"

def fmt_kmh(kmh: float) -> str:
    return f"{kmh:.1f}".replace(".", ",") + " км/ч"

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ Время + дистанция → Темп",  callback_data="m_tdp")],
        [InlineKeyboardButton("📏 Дистанция + темп → Время",  callback_data="m_dpt")],
        [InlineKeyboardButton("🚀 Км/ч → Темп",               callback_data="m_kp")],
        [InlineKeyboardButton("🐢 Темп → Км/ч",               callback_data="m_pk")],
        [InlineKeyboardButton("🔄 Темп на круг",               callback_data="m_lap")],
    ])

def dist_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 км",    callback_data="d_1"),
            InlineKeyboardButton("3 км",    callback_data="d_3"),
            InlineKeyboardButton("5 км",    callback_data="d_5"),
        ],
        [
            InlineKeyboardButton("10 км",   callback_data="d_10"),
            InlineKeyboardButton("15 км",   callback_data="d_15"),
            InlineKeyboardButton("21,1 км", callback_data="d_21.1"),
        ],
        [
            InlineKeyboardButton("42,2 км", callback_data="d_42.2"),
            InlineKeyboardButton("✍️ Вручную", callback_data="d_custom"),
        ],
        [InlineKeyboardButton("◀️ Назад",   callback_data="back")],
    ])

def lap_dist_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("200 м",   callback_data="ld_0.2"),
            InlineKeyboardButton("400 м",   callback_data="ld_0.4"),
            InlineKeyboardButton("800 м",   callback_data="ld_0.8"),
        ],
        [
            InlineKeyboardButton("1000 м",  callback_data="ld_1"),
            InlineKeyboardButton("✍️ Вручную", callback_data="ld_custom"),
        ],
        [InlineKeyboardButton("◀️ Назад",   callback_data="back")],
    ])

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]])

def again_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Новый расчёт", callback_data="again")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я бот для бегунов, которым лень разбираться в математике 🥸\n\n"
        "Посчитаю км/ч на темп и не только 🏃🏽‍♀️‍➡️ 🤍🏃🏽‍♂️ за тебя\n\n"
        "Сделано с любовью\n"
        "Лиза Требухова @fruit_vomit",
        reply_markup=main_kb()
    )
    return MAIN_MENU

async def to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Выбери калькулятор 👇", reply_markup=main_kb())
    return MAIN_MENU

async def again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.edit_message_text("Выбери калькулятор 👇", reply_markup=main_kb())
    return MAIN_MENU

async def m_tdp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "tdp"
    await q.edit_message_text(
        "⏱ *Время + дистанция → Темп*\n\nШаг 1 из 2 — выбери дистанцию:",
        parse_mode="Markdown", reply_markup=dist_kb()
    )
    return WAIT_DIST

async def m_dpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "dpt"
    await q.edit_message_text(
        "📏 *Дистанция + темп → Время*\n\nШаг 1 из 2 — выбери дистанцию:",
        parse_mode="Markdown", reply_markup=dist_kb()
    )
    return WAIT_DIST

async def dist_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "back":
        return await to_main(update, context)
    if q.data == "d_custom":
        await q.edit_message_text(
            "✍️ Введи дистанцию в км\n_Например: 8 или 25,5_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return WAIT_DIST_CUSTOM
    dist = float(q.data.replace("d_", ""))
    context.user_data["dist"] = dist
    mode = context.user_data.get("mode")
    if mode == "tdp":
        await q.edit_message_text(
            f"Дистанция: *{fmt_dist(dist)}* ✅\n\n"
            f"Шаг 2 из 2 — введи время\n"
            f"_Например: 25:30 или 1:52:15_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return WAIT_TIME
    elif mode == "dpt":
        await q.edit_message_text(
            f"Дистанция: *{fmt_dist(dist)}* ✅\n\n"
            f"Шаг 2 из 2 — введи темп *ММ:СС*\n"
            f"_Например: 5:30_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return WAIT_PACE

async def dist_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = parse_float(update.message.text)
    if not dist or dist <= 0:
        await update.message.reply_text("❌ Введи число, например: *8* или *25,5*", parse_mode="Markdown")
        return WAIT_DIST_CUSTOM
    context.user_data["dist"] = dist
    mode = context.user_data.get("mode")
    if mode == "tdp":
        await update.message.reply_text(
            f"Дистанция: *{fmt_dist(dist)}* ✅\n\n"
            f"Шаг 2 из 2 — введи время\n"
            f"_Например: 25:30 или 1:52:15_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return WAIT_TIME
    elif mode == "dpt":
        await update.message.reply_text(
            f"Дистанция: *{fmt_dist(dist)}* ✅\n\n"
            f"Шаг 2 из 2 — введи темп *ММ:СС*\n"
            f"_Например: 5:30_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return WAIT_PACE

async def got_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secs = parse_time(update.message.text)
    if not secs or secs <= 0:
        await update.message.reply_text(
            "❌ Введи время как *ММ:СС* или *ЧЧ:ММ:СС*\n_Например: 25:30 или 1:52:15_",
            parse_mode="Markdown"
        )
        return WAIT_TIME
    dist = context.user_data["dist"]
    pace_s = secs / dist
    kmh = 3600 / pace_s
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🏃 Дистанция: *{fmt_dist(dist)}*\n"
        f"⏱ Время: *{fmt_time(secs)}*\n\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n"
        f"📌 Скорость: *{fmt_kmh(kmh)}*",
        parse_mode="Markdown", reply_markup=again_kb()
    )
    return MAIN_MENU

async def got_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_time(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text(
            "❌ Введи темп как *ММ:СС*\n_Например: 5:30_",
            parse_mode="Markdown"
        )
        return WAIT_PACE
    dist = context.user_data["dist"]
    total = int(pace_s * dist)
    kmh = 3600 / pace_s
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🏃 Дистанция: *{fmt_dist(dist)}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n\n"
        f"⏱ Время финиша: *{fmt_time(total)}*\n"
        f"📌 Скорость: *{fmt_kmh(kmh)}*",
        parse_mode="Markdown", reply_markup=again_kb()
    )
    return MAIN_MENU

async def m_kp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "kp"
    kmh_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("8",  callback_data="k_8"),
            InlineKeyboardButton("9",  callback_data="k_9"),
            InlineKeyboardButton("10", callback_data="k_10"),
        ],
        [
            InlineKeyboardButton("11", callback_data="k_11"),
            InlineKeyboardButton("12", callback_data="k_12"),
            InlineKeyboardButton("13", callback_data="k_13"),
        ],
        [InlineKeyboardButton("✍️ Вручную", callback_data="k_custom")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back")],
    ])
    await q.edit_message_text(
        "🚀 *Км/ч → Темп*\n\nВыбери скорость:",
        parse_mode="Markdown", reply_markup=kmh_kb
    )
    return WAIT_KMH

async def kmh_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "back":
        return await to_main(update, context)
    if q.data == "k_custom":
        await q.edit_message_text(
            "✍️ Введи скорость в км/ч\n_Например: 10,5_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return WAIT_KMH
    kmh = float(q.data.replace("k_", ""))
    pace_s = 3600 / kmh
    await q.edit_message_text(
        f"✅ *Результат*\n\n"
        f"🚀 Скорость: *{fmt_kmh(kmh)}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*",
        parse_mode="Markdown", reply_markup=again_kb()
    )
    return MAIN_MENU

async def kmh_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kmh = parse_float(update.message.text)
    if not kmh or kmh <= 0:
        await update.message.reply_text("❌ Введи число, например: *10,5*", parse_mode="Markdown")
        return WAIT_KMH
    pace_s = 3600 / kmh
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🚀 Скорость: *{fmt_kmh(kmh)}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*",
        parse_mode="Markdown", reply_markup=again_kb()
    )
    return MAIN_MENU

async def m_pk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "pk"
    await q.edit_message_text(
        "🐢 *Темп → Км/ч*\n\nВведи темп *ММ:СС*\​​​​​​​​​​​​​​​​
