import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram import types
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.exceptions import UnknownIntent
from dotenv import find_dotenv, load_dotenv

from src.constants import instructions_url, how_to_get_url, tg_chat_url, bot_name, bot_description, bot_commands

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(storage=MemoryStorage())


@dp.error(ExceptionTypeFilter(UnknownIntent), F.update.callback_query.as_("callback_query"))
async def unknown_intent_handler(event: ErrorEvent, callback_query: types.CallbackQuery):
    await callback_query.answer("Unknown intent: Please, try to restart the action.")


@dp.message(Command("start"))
async def start(message: types.Message):
    from src.api import client

    telegram_id = str(message.from_user.id)
    res = await client.is_user_exists(telegram_id)
    if res:
        from src.menu import menu_kb

        await message.answer("Welcome! Choose the action you're interested in.", reply_markup=menu_kb)
    else:
        from src.routers.registration.keyboards import registration_kb

        await message.answer("Welcome! To continue, you need to register.", reply_markup=registration_kb)


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Instructions", url=instructions_url),
                types.InlineKeyboardButton(text="Location", url=how_to_get_url),
                types.InlineKeyboardButton(text="Telegram chat", url=tg_chat_url),
            ]
        ]
    )

    await message.answer(
        "If you have any questions, you can ask them in the chat or read the instructions.",
        reply_markup=keyboard,
    )


@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    from src.menu import menu_kb

    await message.answer("Choose the action you're interested in.", reply_markup=menu_kb)


async def main():
    from src.routers import routers

    for router in routers:
        dp.include_router(router)
    setup_dialogs(dp)
    # Set bot name, description and commands
    existing_bot = {
        "name": (await bot.get_my_name()).name,
        "description": (await bot.get_my_description()).description,
        "commands": await bot.get_my_commands(),
    }

    if existing_bot["name"] != bot_name:
        await bot.set_my_name(bot_name)
    if existing_bot["description"] != bot_description:
        await bot.set_my_short_description(bot_description)
    if existing_bot["commands"] != bot_commands:
        await bot.set_my_commands(bot_commands)
    # Drop pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start long-polling
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
