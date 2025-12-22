#!/usr/bin/env python3
import asyncio
import logging
import os
import signal
from telegram.ext import Application

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")  # set this in Render env vars

async def _async_start(app: Application):
    # Register handlers here (if you have a central register function, it should import and run it)
    try:
        from bot.handlers import register_handlers
    except Exception:
        register_handlers = None

    if register_handlers:
        try:
            register_handlers(app)
            logger.info("Handlers registered via bot.handlers.register_handlers")
        except Exception as exc:
            logger.exception("Failed to register handlers: %s", exc)
            raise

    # Temporary debug: detect ellipsis placeholders early
    for groups in app.handlers.values():
        for g in groups:
            if isinstance(g, (list, tuple)):
                for h in g:
                    if h is ...:
                        raise RuntimeError("Found ellipsis (...) in handler registration — remove it")
            else:
                if g is ...:
                    raise RuntimeError("Found ellipsis (...) in handler registration — remove it")

    # Ensure webhook removed before polling (safe; harmless if no webhook)
    try:
        await app.bot.delete_webhook()
    except Exception:
        logger.debug("delete_webhook failed or was unnecessary")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Bot started (async mode)")

    stop_event = asyncio.Event()
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                # Not available on some platforms
                pass
    except RuntimeError:
        # no running loop
        pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        logger.info("Shutting down bot...")
        try:
            await app.updater.stop()
        except Exception:
            logger.debug("updater.stop() failed or unnecessary")
        try:
            await app.stop()
            await app.shutdown()
        except Exception:
            logger.exception("Error during shutdown")
        logger.info("Bot shutdown complete")

async def run_app():
    if not TOKEN:
        logger.error("BOT_TOKEN not set in environment")
        return
    app = Application.builder().token(TOKEN).build()
    await _async_start(app)

def main():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.info("Detected running event loop — scheduling bot in existing loop.")
        asyncio.create_task(run_app())
    else:
        logger.info("No running event loop — starting bot with asyncio.run")
        asyncio.run(run_app())

if __name__ == "__main__":
    main()
