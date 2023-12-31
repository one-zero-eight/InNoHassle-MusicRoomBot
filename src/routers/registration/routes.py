import asyncio

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.api import client
from src.constants import rules_message, rules_confirmation_template
from src.menu import menu_kb
from src.routers.registration import router
from src.routers.registration.keyboards import RegistrationCallbackData, phone_request_kb, confirm_email_kb
from src.routers.registration.states import RegistrationStates


@router.callback_query(RegistrationCallbackData.filter(F.key == "register"))
async def user_want_to_register(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    telegram_id = str(callback_query.from_user.id)
    if not await client.is_user_exists(telegram_id):
        await callback_query.bot.send_message(
            chat_id=callback_query.from_user.id,
            text="Enter your email. You will receive a one-time code for registration.",
        )
        await state.set_state(RegistrationStates.email_requested)
    else:
        await callback_query.bot.send_message(
            chat_id=callback_query.from_user.id,
            text="You're already registered.",
            reply_markup=menu_kb,
        )


@router.message(RegistrationStates.email_requested)
async def request_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer(
        text=f"You entered {message.text}. Is it correct email?",
        reply_markup=confirm_email_kb,
    )


@router.callback_query(RegistrationCallbackData.filter(F.key == "change_email"))
async def change_email(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Please enter your email again.")
    await state.set_state(RegistrationStates.email_requested)


@router.callback_query(RegistrationCallbackData.filter(F.key == "correct_email"))
async def send_code(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_data = await state.get_data()
    email = user_data.get("email")
    success, error = await client.start_registration(email)
    if not success:
        await callback.message.answer(error)
    else:
        await callback.message.answer("We sent a one-time code on your email. Please, enter it.")
        await state.set_state(RegistrationStates.code_requested)


@router.message(RegistrationStates.code_requested)
async def request_code(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    email = user_data.get("email")
    telegram_id = str(message.from_user.id)
    code = message.text

    success, error = await client.validate_code(email, code, telegram_id)

    if not success:
        await message.answer(error)
    else:
        await message.answer(
            text="Your code has been accepted. To use the music room, you need to fill out your profile."
        )
        await asyncio.sleep(0.1)
        await message.answer(
            text="Please provide access to your phone number.",
            reply_markup=phone_request_kb,
        )
        await state.set_state(RegistrationStates.phone_number_requested)


@router.message(RegistrationStates.phone_number_requested, F.contact)
async def request_phone_number(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)
    await message.answer("Please, enter your full name.")
    await state.set_state(RegistrationStates.name_requested)


@router.message(RegistrationStates.name_requested)
async def request_name(message: Message, state: FSMContext):
    user_data = await state.get_data()

    success, error = await client.fill_profile(
        telegram_id=message.from_user.id,
        name=message.text,
        alias=message.from_user.username,
        phone_number=user_data.get("phone_number"),
    )

    if not success:
        await message.answer(error)
    else:
        await state.update_data(name=message.text)

        await message.answer("Please, read the rules and confirm that you agree with them.")
        await asyncio.sleep(0.1)
        confirm_kb = types.ReplyKeyboardMarkup(
            keyboard=[
                [
                    types.KeyboardButton(
                        text=rules_confirmation_template.format(name=message.text),
                    )
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(rules_message, reply_markup=confirm_kb)
        await state.set_state(RegistrationStates.rules_confirmation_requested)


@router.message(RegistrationStates.rules_confirmation_requested)
async def confirm_rules(message: Message, state: FSMContext):
    if message.text[:100] == rules_confirmation_template.format(name=(await state.get_data()).get("name"))[:100]:
        await message.answer("You have successfully registered.", reply_markup=menu_kb)
        await state.clear()
    else:
        await message.answer("You haven't confirmed the rules. Please, try again.")
