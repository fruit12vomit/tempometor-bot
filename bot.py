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
    """ЧЧ:ММ:СС → секунды"""
    parts = text.strip().replace(",", ":").replace(".", ":").split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
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
    return f"{h}:{m:02d}:{s:02d}"

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
        "⏱ *Время + дистанция → Темп*\n\nШаг 1 из 2 — введи время в формате *ЧЧ:ММ:СС*\n_Например: 0:25:30 или 1:52:15_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_TIME

async def m_dpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "dpt"
    await q.edit_message_text(
        "📏 *Дистанция + темп → Время*\n\nШаг 1 из 2 — выбери дистанцию:",
        parse_mode="Markdown", reply_markup=dist_kb()
    )
    return WAIT_DIST

async def got_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secs = parse_time(update.message.text)
    if not secs or secs <= 0:
        await update.message.reply_text(
            "❌ Введи время в формате *ЧЧ:ММ:СС*\n_Например: 0:25:30 или 1:52:15_",
            parse_mode="Markdown"
        )
        return WAIT_TIME
    context.user_data["time"] = secs
    await update.message.reply_text(
        f"Время: *{fmt_time(secs)}* ✅\n\nШаг 2 из 2 — выбери дистанцию:",
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
    return await calc_result(update, context, via_query=True)

async def dist_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = parse_float(update.message.text)
    if not dist or dist <= 0:
        await update.message.reply_text("❌ Введи число, например: *8* или *25,5*", parse_mode="Markdown")
        return WAIT_DIST_CUSTOM
    context.user_data["dist"] = dist
    return await calc_result(update, context, via_query=False)

async def calc_result(update, context, via_query=False):
    mode = context.user_data.get("mode")
    dist = context.user_data.get("dist")

    if mode == "tdp":
        secs = context.user_data.get("time")
        pace_s = secs / dist
        kmh = 3600 / pace_s
        text = (
            f"✅ *Результат*\n\n"
            f"⏱ Время: *{fmt_time(secs)}*\n"
            f"🏃 Дистанция: *{fmt_dist(dist)}*\n\n"
            f"📌 Темп: *{fmt_pace(pace_s)}*\n"
            f"📌 Скорость: *{fmt_kmh(kmh)}*"
        )
        if via_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=again_kb())
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=again_kb())
        return MAIN_MENU

    elif mode == "dpt":
        pace_s = context.user_data.get("pace")
        total = int(pace_s * dist)
        kmh = 3600 / pace_s
        text = (
            f"✅ *Результат*\n\n"
            f"🏃 Дистанция: *{fmt_dist(dist)}*\n"
            f"📌 Темп: *{fmt_pace(pace_s)}*\n\n"
            f"⏱ Время финиша: *{fmt_time(total)}*\n"
            f"📌 Скорость: *{fmt_kmh(kmh)}*"
        )
        if via_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=again_kb())
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=again_kb())
        return MAIN_MENU

async def dist_select_dpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await q.edit_message_text(
        f"Дистанция: *{fmt_dist(dist)}* ✅\n\nШаг 2 из 2 — введи темп *ММ:СС*\n_Например: 5:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_PACE

async def got_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_time(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text(
            "❌ Введи темп как *ММ:СС*\n_Например: 5:30_",
            parse_mode="Markdown"
        )
        return WAIT_PACE
    context.user_data["pace"] = pace_s
    dist = context.user_data.get("dist")
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
        "🐢 *Темп → Км/ч*\n\nВведи темп *ММ:СС*\n_Например: 5:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_PACE

async def pk_got_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_time(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text("❌ Введи темп как *ММ:СС*, например: *5:30*", parse_mode="Markdown")
        return WAIT_PACE
    kmh = 3600 / pace_s
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n"
        f"🚀 Скорость: *{fmt_kmh(kmh)}*",
        parse_mode="Markdown", reply_markup=again_kb()
    )
    return MAIN_MENU

async def m_lap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["mode"] = "lap"
    await q.edit_message_text(
        "🔄 *Темп на круг*\n\nШаг 1 из 2 — выбери длину круга:",
        parse_mode="Markdown", reply_markup=lap_dist_kb()
    )
    return LAP_DIST

async def lap_dist_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "back":
        return await to_main(update, context)
    if q.data == "ld_custom":
        await q.edit_message_text(
            "✍️ Введи длину круга в км\n_Например: 0,6 или 2_",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        return LAP_DIST_CUSTOM
    dist = float(q.data.replace("ld_", ""))
    context.user_data["lap_dist"] = dist
    label = f"{int(dist*1000)} м" if dist < 1 else fmt_dist(dist)
    await q.edit_message_text(
        f"Круг: *{label}* ✅\n\nШаг 2 из 2 — введи темп *ММ:СС*\n_Например: 4:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_LAP_PACE

async def lap_dist_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = parse_float(update.message.text)
    if not dist or dist <= 0:
        await update.message.reply_text("❌ Введи число, например: *0,6* или *2*", parse_mode="Markdown")
        return LAP_DIST_CUSTOM
    context.user_data["lap_dist"] = dist
    label = f"{int(dist*1000)} м" if dist < 1 else fmt_dist(dist)
    await update.message.reply_text(
        f"Круг: *{label}* ✅\n\nШаг 2 из 2 — введи темп *ММ:СС*\n_Например: 4:30_",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return WAIT_LAP_PACE

async def lap_got_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace_s = parse_time(update.message.text)
    if not pace_s or pace_s <= 0:
        await update.message.reply_text("❌ Введи темп как *ММ:СС*, например: *4:30*", parse_mode="Markdown")
        return WAIT_LAP_PACE
    dist = context.user_data["lap_dist"]
    lap_t = int(pace_s * dist)
    label = f"{int(dist*1000)} м" if dist < 1 else fmt_dist(dist)
    await update.message.reply_text(
        f"✅ *Результат*\n\n"
        f"🔄 Круг: *{label}*\n"
        f"📌 Темп: *{fmt_pace(pace_s)}*\n\n"
        f"⏱ Время на круг: *{fmt_time(lap_t)}*",
        parse_mode="Markdown", reply_markup=again_kb()
    )
    return MAIN_MENU

async def pace_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode == "dpt":
        return await got_pace(update, context)
    elif mode == "pk":
        return await pk_got_pace(update, context)
    return MAIN_MENU

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(m_tdp,  pattern="^m_tdp$"),
                CallbackQueryHandler(m_dpt,  pattern="^m_dpt$"),
                CallbackQueryHandler(m_kp,   pattern="^m_kp$"),
                CallbackQueryHandler(m_pk,   pattern="^m_pk$"),
                CallbackQueryHandler(m_lap,  pattern="^m_lap$"),
                CallbackQueryHandler(again,  pattern="^again$"),
            ],
            WAIT_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_time),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
            WAIT_DIST: [
                CallbackQueryHandler(dist_select),
            ],
            WAIT_DIST_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, dist_custom),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
            WAIT_PACE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pace_router),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
            WAIT_KMH: [
                CallbackQueryHandler(kmh_select),
                MessageHandler(filters.TEXT & ~filters.COMMAND, kmh_custom),
            ],
            LAP_DIST: [
                CallbackQueryHandler(lap_dist_select),
            ],
            LAP_DIST_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lap_dist_custom),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
            WAIT_LAP_PACE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lap_got_pace),
                CallbackQueryHandler(to_main, pattern="^back$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(to_main, pattern="^back$"),
            CallbackQueryHandler(again, pattern="^again$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
