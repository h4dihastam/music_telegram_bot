import traceback

async def error_handler(update, context):
    # لاگ کامل استثنا
    logger.exception("خطا در هندلر:")
    tb = ""
    try:
        if getattr(context, "error", None):
            tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        else:
            tb = "No traceback available"
    except Exception:
        tb = "خطا هنگام گرفتن traceback"

    logger.error("Traceback:\n%s", tb)

    # پیام کاربر پسند
    try:
        if update and getattr(update, "effective_message", None):
            await update.effective_message.reply_text(
                "❌ متأسفانه یه خطایی پیش اومد!\nلطفاً دوباره امتحان کن."
            )
    except Exception:
        logger.exception("خطا هنگام ارسال پیام خطا به کاربر")