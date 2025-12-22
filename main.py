#!/usr/bin/env python3
import asyncio
import logging
import os
import signal
from telegram.ext import Application

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

TOKEN = os.getenv("BOT_TOKEN")  # load from environment; DO NOT hardcode token

async def _async_start(app: Application):
    # Register handlers here (or import a register function)
    # from bot.handlers import register_handlers
    # register_handlers(app)
    await app.initialize()
    await app.start()
    # start polling without trying to create/close the loop
    await app.updater.start_polling()
    logger.info("Bot started (async mode)")

    stop_event = asyncio.Event()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                # may happen on some platforms
                pass
    except RuntimeError:
        pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        logger.info("Shutting down bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Bot shutdown complete")

async def run_app():
    if not TOKEN:
        logger.error("BOT_TOKEN not set in environment")
        return
    app = Application.builder().token(TOKEN).build()
    # add your handlers before starting, e.g.:
    # from bot.handlers import register_handlers
    # register_handlers(app)

    await _async_start(app)

def main():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Running inside another event loop (hosted environment). Schedule async runner.
        logger.info("Detected running event loop — starting bot in async mode.")
        asyncio.create_task(run_app())
    else:
        # No loop running: run normally (this will create/close the loop)
        logger.info("No running event loop — starting bot with asyncio.run")
        asyncio.run(run_app())

if __name__ == "__main__":
    main()