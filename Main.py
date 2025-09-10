import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Лимиты сообщений
FREE_MESSAGE_LIMIT = 5
SUBSCRIBED_MESSAGE_LIMIT = 30

# Состояния для отправки сообщения
class SendMessage(StatesGroup):
    waiting_for_message = State()
    target_user_id = State()

# --- Клавиатуры ---

def get_subscription_keyboard():
    """Создает клавиатуру для покупки подписки."""
    button = InlineKeyboardButton(text="Купить подписку (демо)", callback_data="subscribe")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard

# --- Обработчики команд ---

@dp.message(CommandStart())
async def send_welcome(message: Message):
    """
    Этот обработчик будет вызван, когда пользователь отправит команду /start.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    db.add_user_if_not_exists(user_id, username)

    # Уникальная ссылка для пользователя
    unique_link = f"https://t.me/{await bot.get_me()}/?start=msg_{user_id}"

    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        f"Это бот для анонимных сообщений.\n\n"
        f"💌 Ваша уникальная ссылка для получения сообщений:\n"
        f"`{unique_link}`\n\n"
        f"Поделитесь ей с друзьями, чтобы они могли отправить вам анонимное сообщение.",
        parse_mode="Markdown"
    )
    await show_stats(message)


@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Показывает статистику по команде /stats"""
    await show_stats(message)


async def show_stats(message: Message):
    """Отображает статистику пользователя."""
    user_id = message.from_user.id
    stats = db.get_user_stats(user_id)
    if stats:
        messages_received, is_subscribed = stats
        limit = SUBSCRIBED_MESSAGE_LIMIT if is_subscribed else FREE_MESSAGE_LIMIT
        status = "✅ Активна" if is_subscribed else "❌ Нет"

        await message.answer(
            f"📊 Ваша статистика:\n\n"
            f"Всего получено сообщений: {messages_received}\n"
            f"Статус подписки: {status}\n"
            f"Лимит сообщений в день: {limit}",
            reply_markup=get_subscription_keyboard() if not is_subscribed else None
        )

# --- Логика отправки анонимных сообщений ---

@dp.message(F.text.startswith('/start msg_'))
async def handle_deep_link(message: Message, state: FSMContext):
    """
    Обрабатывает переход по уникальной ссылке для отправки сообщения.
    """
    try:
        target_user_id = int(message.text.split('_')[1])
        if target_user_id == message.from_user.id:
            await message.answer("Вы не можете отправить сообщение самому себе.")
            return

        target_user_info = db.get_user_info(target_user_id)
        if not target_user_info:
            await message.answer("Пользователь не найден.")
            return

        messages_received, is_subscribed = target_user_info
        limit = SUBSCRIBED_MESSAGE_LIMIT if is_subscribed else FREE_MESSAGE_LIMIT

        if messages_received >= limit:
            await message.answer("К сожалению, у этого пользователя достигнут дневной лимит анонимных сообщений. Попробуйте позже.")
            return

        # Сохраняем ID получателя в состоянии
        await state.update_data(target_user_id=target_user_id)
        await state.set_state(SendMessage.waiting_for_message)

        await message.answer(f"Теперь отправьте анонимное сообщение. Получатель не узнает, кто вы.")

    except (IndexError, ValueError):
        await message.answer("Неверная ссылка. Пожалуйста, используйте правильную ссылку для отправки сообщения.")


@dp.message(SendMessage.waiting_for_message)
async def process_anonymous_message(message: Message, state: FSMContext):
    """
    Принимает анонимное сообщение и пересылает его получателю.
    """
    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    if not target_user_id:
        await message.answer("Произошла ошибка. Попробуйте снова перейти по ссылке.")
        await state.clear()
        return

    try:
        # Увеличиваем счетчик сообщений получателя
        db.increment_message_count(target_user_id)

        # Отправляем сообщение получателю
        await bot.send_message(
            chat_id=target_user_id,
            text=f"💌 Вам пришло новое анонимное сообщение:\n\n"
                 f"<i>{message.text}</i>", # Можно пересылать и другие типы контента
            parse_mode="HTML"
        )
        await message.answer("✅ Ваше анонимное сообщение успешно отправлено!")

    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        await message.answer("Не удалось отправить сообщение. Возможно, получатель заблокировал бота.")
    finally:
        await state.clear()


# --- Обработка подписки (демо) ---

@dp.callback_query(F.data == "subscribe")
async def process_subscription(callback: types.CallbackQuery):
    """
    Обрабатывает нажатие на кнопку "Купить подписку".
    В реальном боте здесь будет логика оплаты.
    """
    user_id = callback.from_user.id
    db.activate_subscription(user_id)

    await callback.message.edit_text(
        "✅ Поздравляем! Ваша подписка успешно активирована.\n"
        f"Ваш дневной лимит сообщений увеличен до {SUBSCRIBED_MESSAGE_LIMIT}."
    )
    await callback.answer()


# --- Основная функция запуска ---

async def main():
    """Главная функция для запуска бота."""
    db.init_db()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
