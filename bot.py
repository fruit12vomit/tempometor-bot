import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

# States
(
    MAIN_MENU,
    WAIT_A, WAIT_B,
    LAP_MENU,
    LAP_WAIT_DIST,
) = range(5)

def parse_distance(text: str):
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None

def parse_time(text: str):
    parts = text.strip().replace(".", ":").replace(",", ":").split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 2:
            return parts[0] * 3600 + parts[1] * 60
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        pass
    return None

def parse_pace(text: str):
    parts = text.strip().replace(".", ":").replace(",", ":").split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
    except ValueError:
        pass
    return None

def fmt_distance(km: float) -> str:
    return f"{km:.2f}".replace(".", ",") + " км"

def fmt_time(total_seconds: int) -> str:
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    return f"{h}:{m:02d} ч"

def fmt_pace(seconds_per_km: float) -> str:
    m, s = divmod(int(round(seconds_per_km)), 60)
    return f"{m}:{s:02d} /км"

def fmt_kmh(kmh: float) -> str:
    return f"{kmh:.1f}".replace(".", ",") + " км/ч"

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ Время + дистанция → Темп",  callback_data="m_time_dist_pace")],
        [InlineKeyboardButton("📏 Дистанция + темп → Время",  callback_data="m_dist_pace_time")],
        [InlineKeyboardButton("🚀 Км/ч → Темп",               callback_data="m_kmh_pace")],
        [InlineKeyboardButton("🐢 Темп → Км/ч",               callback_data="m_pace_kmh")],
        [InlineKeyboardButton("🔄 Темп на круг",               callback_data="m_lap")],
    ])

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]])

def lap_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("200 м",   callback_data="lap_0.2"),
            InlineKeyboardButton("400 м",   callback_data="lap_0.4"),
            InlineKeyboardButton("800 м",   callback_data="lap_0.8"),
        ],
        [
            InlineKeyboardButton("1 км",    callback_data="lap_1"),
            InlineKeyboardButton("3 км",    callback_data="lap_3"),
            InlineKeyboardButton("5 км",    callback_data="lap_5"),
        ],
        [
            InlineKeyboardButton("10 км",   callback_data="lap_10"),
            InlineKeyboardButton("✏️ Своё", callback_data="lap_custom"),
        ],
        [InlineKeyboardButton("◀️ Назад",   callback_data="back")],
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

async def m_time_dist_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "time_dist_pace"
    await q.edit_message_text(
        "⏱ *Время + дистанция → Темп*\n\n"
        "Шаг 1 из 2 — введи дистанцию в км\n"
        "_Например: 10 или 21,1_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_A

async def m_time_dist_pace_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = parse_distance(update.message.text)
    if not dist or dist <= 0:
        await update.message.reply_text("❌ Введи число, например: *10* или *21,1*", parse_mode="Markdown")
        return WAIT_A
    context.user_data["val_a"] = dist
    await update.message.reply_text(
        f"Дистанция: *{fmt_distance(dist)}* ✅\n\n"
        "Шаг 2 из 2 — введи время финиша *Ч:ММ* или *ЧЧ:ММ*\n"
        "_Например: 1:02 или 0:45_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_B

async def m_time_dist_pace_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secs = parse_time(update.message.text)
    if not secs or secs <= 0:
        await update.message.reply_text("❌ Введи время как *Ч:ММ*, например: *1:02*", parse_mode="Markdown")
        return WAIT_B
    dist = context.user_data["val_a"]
    pace_s = secs / dist
    kmh = 3600 / pace_s
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🏃 Дистанция: *{fmt_distance(dist)}*\n"
        f"⏱ Время: *{fmt_time(secs)}*\n\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n"
        f"📌 Скорость: *{fmt_kmh(kmh)}*",
        parse_mode="Markdown", reply_markup=main_kb()
    )
    return MAIN_MENU

async def m_dist_pace_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "dist_pace_time"
    await q.edit_message_text(
        "📏 *Дистанция + темп → Время финиша*\n\n"
        "Шаг 1 из 2 — введи дистанцию в км\n"
        "_Например: 42,2_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_A

async def m_dist_pace_time_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = parse_distance(update.message.text)
    if not dist or dist <= 0:
        await update.message.reply_text("❌ Введи число, например: *42,2*", parse_mode="Markdown")
        return WAIT_A
    context.user_data["val_a"] = dist
    await update.message.reply_text(
        f"Дистанция: *{fmt_distance(dist)}* ✅\n\n"
        "Шаг 2 из 2 — введи темп *ММ:СС*\n"
        "_Например: 5:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_B

async def m_dist_pace_time_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_pace(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text("❌ Введи темп как *ММ:СС*, например: *5:30*", parse_mode="Markdown")
        return WAIT_B
    dist = context.user_data["val_a"]
    total = int(pace_s * dist)
    kmh = 3600 / pace_s
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🏃 Дистанция: *{fmt_distance(dist)}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n\n"
        f"⏱ Время финиша: *{fmt_time(total)}*\n"
        f"📌 Скорость: *{fmt_kmh(kmh)}*",
        parse_mode="Markdown", reply_markup=main_kb()
    )
    return MAIN_MENU

async def m_kmh_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "kmh_pace"
    await q.edit_message_text(
        "🚀 *Км/ч → Темп*\n\nВведи скорость в км/ч\n_Например: 10,5_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_A

async def m_kmh_pace_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kmh = parse_distance(update.message.text)
    if not kmh or kmh <= 0:
        await update.message.reply_text("❌ Введи число, например: *10,5*", parse_mode="Markdown")
        return WAIT_A
    pace_s = 3600 / kmh
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🚀 Скорость: *{fmt_kmh(kmh)}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*",
        parse_mode="Markdown", reply_markup=main_kb()
    )
    return MAIN_MENU

async def m_pace_kmh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "pace_kmh"
    await q.edit_message_text(
        "🐢 *Темп → Км/ч*\n\nВведи темп *ММ:СС*\n_Например: 5:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_A

async def m_pace_kmh_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_pace(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text("❌ Введи темп как *ММ:СС*, например: *5:30*", parse_mode="Markdown")
        return WAIT_A
    kmh = 3600 / pace_s
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n"
        f"🚀 Скорость: *{fmt_kmh(kmh)}*",
        parse_mode="Markdown", reply_markup=main_kb()
    )
    return MAIN_MENU

async def m_lap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "lap"
    await q.edit_message_text(
        "🔄 *Темп на круг*\n\nВведи темп *ММ:СС*\n_Например: 5:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_A

async def m_lap_got_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_pace(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text("❌ Введи темп как *ММ:СС*, например: *5:30*", parse_mode="Markdown")
        return WAIT_A
    context.user_data["val_a"] = pace_s
    await update.message.reply_text(
        f"Темп: *{fmt_pace(pace_s)}* ✅\n\nВыбери дистанцию круга 👇",
        parse_mode="Markdown", reply_markup=lap_kb()
    )
    return LAP_MENU

async def m_lap_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "back":
        return await to_main(update, context)
    if q.data == "lap_custom":
        await q.edit_message_text(
            "✏️ Введи своё расстояние в км\n_Например: 0,8 или 2_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return LAP_WAIT_DIST
    dist = float(q.data.replace("lap_", ""))
    pace_s = context.user_data["val_a"]
    lap_t = int(pace_s * dist)
    label = f"{int(dist * 1000)} м" if dist < 1 else fmt_distance(dist)
    await q.edit_message_text(
        f"✅ *Результат*\n\n"
        f"🔄 Круг: *{label}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n\n"
        f"⏱ Время на круг: *{fmt_time(lap_t)}*",
        parse_mode="Markdown", reply_markup=main_kb()
    )
    return MAIN_MENU

async def m_lap_custom_dist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = parse_distance(update.message.text)
    if not dist or dist <= 0:
        await update.message.reply_text("❌ Введи число, например: *0,8*", parse_mode="Markdown")
        return LAP_WAIT_DIST
    pace_s = context.user_data["val_a"]
    lap_t = int(pace_s * dist)
    label = f"{int(dist * 1000)} м" if dist < 1 else fmt_distance(dist)
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🔄 Круг: *{label}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n\n"
        f"⏱ Время на круг: *{fmt_time(lap_t)}*",
        parse_mode="Markdown", reply_markup=main_kb()
    )
    return MAIN_MENU

async def wait_a_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode == "time_dist_pace": return await m_time_dist_pace_b(update, context)
    if mode == "dist_pace_time": return await m_dist_pace_time_b(update, context)
    if mode == "kmh_pace":       return await m_kmh_pace_calc(update, context)
    if mode == "pace_kmh":       return await m_pace_kmh_calc(update, context)
    if mode == "lap":            return await m_lap_got_pace(update, context)
    return MAIN_MENU

async def wait_b_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode == "time_dist_pace": return await m_time_dist_pace_calc(update, context)
    if mode == "dist_pace_time": return await m_dist_pace_time_calc(update, context)
    return MAIN_MENU

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(m_time_dist_pace, pattern="^m_time_dist_pace$"),
                CallbackQueryHandler(m_dist_pace_time, pattern="^m_dist_pace_time$"),
                CallbackQueryHandler(m_kmh_pace,       pattern="^m_kmh_pace$"),
                CallbackQueryHandler(m_pace_kmh,       pattern="^m_pace_kmh$"),
                CallbackQueryHandler(m_lap,            pattern="^m_lap$"),
            ],
            WAIT_A: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wait_a_router),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
            WAIT_B: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wait_b_router),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
            LAP_MENU: [
                CallbackQueryHandler(m_lap_select),
            ],
            LAP_WAIT_DIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, m_lap_custom_dist),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(to_main, pattern="^back$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
