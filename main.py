import asyncio
import os
import json
from datetime import datetime
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not found")

bot = Bot(token=TOKEN)
dp = Dispatcher()


class RequirementState(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()


DB_FILE = "requirements.json"


def load_requirements():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"functional": [], "non_functional": []}


def save_requirements(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main_menu():
    kb = [
        [KeyboardButton(text="Добавить функциональное требование")],
        [KeyboardButton(text="Добавить нефункциональное требование")],
        [KeyboardButton(text="Показать все требования")],
        [KeyboardButton(text="Статистика"), KeyboardButton(text="Экспорт")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def priority_keyboard():
    kb = [
        [KeyboardButton(text="Высокий"), KeyboardButton(text="Средний")],
        [KeyboardButton(text="Низкий")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)


def cancel_keyboard():
    kb = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для сбора и анализа требований к ПО.\n"
        "Помогу структурировать функциональные и нефункциональные требования.\n\n"
        "Выберите действие из меню 👇",
        reply_markup=main_menu()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        " Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Справка\n"
        "/cancel - Отменить текущую операцию\n\n"
        "Используй кнопки меню для работы!"
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Операция отменена", reply_markup=main_menu())


@dp.message(F.text == "Добавить функциональное требование")
async def add_functional(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RequirementState.waiting_for_title)
    await state.update_data(type="functional")
    await message.answer(
        "📝 Функциональное требование\n\n"
        "Введите название требования (кратко):\n"
        "Например: 'Авторизация пользователя'\n\n"
        "Или нажмите 'Отмена' для выхода",
        reply_markup=cancel_keyboard()
    )


@dp.message(F.text == "Добавить нефункциональное требование")
async def add_non_functional(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RequirementState.waiting_for_title)
    await state.update_data(type="non_functional")
    await message.answer(
        "📝 Нефункциональное требование\n\n"
        "Введите название требования:\n"
        "Например: 'Производительность системы'\n\n"
        "Или нажмите 'Отмена' для выхода",
        reply_markup=cancel_keyboard()
    )


@dp.message(RequirementState.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer(" Операция отменена", reply_markup=main_menu())
        return

    await state.update_data(title=message.text)
    await state.set_state(RequirementState.waiting_for_description)
    await message.answer(
        "📄 Теперь введите описание требования:\n"
        "Опишите, что должно делать требование\n\n"
        "Или нажмите 'Отмена' для выхода",
        reply_markup=cancel_keyboard()
    )


@dp.message(RequirementState.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("❌ Операция отменена", reply_markup=main_menu())
        return

    await state.update_data(description=message.text)
    await state.set_state(RequirementState.waiting_for_priority)
    await message.answer(
        "🎯 Выберите приоритет:",
        reply_markup=priority_keyboard()
    )


@dp.message(RequirementState.waiting_for_priority)
async def process_priority(message: Message, state: FSMContext):
    priority_map = {"Высокий": "high", "Средний": "medium", "Низкий": "low"}
    priority = priority_map.get(message.text, "medium")

    data = await state.get_data()
    requirements = load_requirements()

    new_req = {
        "id": len(requirements["functional"]) + len(requirements["non_functional"]) + 1,
        "title": data["title"],
        "description": data["description"],
        "priority": priority,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "user": message.from_user.first_name
    }

    if data["type"] == "functional":
        requirements["functional"].append(new_req)
    else:
        requirements["non_functional"].append(new_req)

    save_requirements(requirements)
    await state.clear()

    await message.answer(
        f"✅ Требование сохранено!\n\n"
        f"Тип: {'Функциональное' if data['type'] == 'functional' else 'Нефункциональное'}\n"
        f"Название: {data['title']}\n"
        f"Приоритет: {message.text}\n\n"
        "Используй меню для просмотра всех требований.",
        reply_markup=main_menu()
    )


@dp.message(F.text == "Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Операция отменена", reply_markup=main_menu())


@dp.message(F.text == "Показать все требования")
async def show_requirements(message: Message, state: FSMContext):
    await state.clear()
    requirements = load_requirements()

    if not requirements["functional"] and not requirements["non_functional"]:
        await message.answer("📭 Пока нет сохраненных требований", reply_markup=main_menu())
        return

    text = "📋 ВСЕ ТРЕБОВАНИЯ\n\n"

    if requirements["functional"]:
        text += "✅ ФУНКЦИОНАЛЬНЫЕ:\n"
        for req in requirements["functional"]:
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(req["priority"], "")
            text += f"{emoji} #{req['id']} {req['title']}\n"
            desc = req['description'][:100] + "..." if len(req['description']) > 100 else req['description']
            text += f"   {desc}\n"
            text += f"   Дата: {req['date']}\n\n"

    if requirements["non_functional"]:
        text += "🟨 НЕФУНКЦИОНАЛЬНЫЕ:\n"
        for req in requirements["non_functional"]:
            emoji = {"high": "🔴", "medium": "", "low": "🟢"}.get(req["priority"], "")
            text += f"{emoji} #{req['id']} {req['title']}\n"
            desc = req['description'][:100] + "..." if len(req['description']) > 100 else req['description']
            text += f"   {desc}\n"
            text += f"   Дата: {req['date']}\n\n"

    await message.answer(text, reply_markup=main_menu())


@dp.message(F.text == "Статистика")
async def show_stats(message: Message, state: FSMContext):
    await state.clear()
    requirements = load_requirements()
    total = len(requirements["functional"]) + len(requirements["non_functional"])

    if total == 0:
        await message.answer("📭 Нет данных для статистики", reply_markup=main_menu())
        return

    all_reqs = requirements["functional"] + requirements["non_functional"]
    priorities = {"high": 0, "medium": 0, "low": 0}
    for req in all_reqs:
        priorities[req["priority"]] = priorities.get(req["priority"], 0) + 1

    text = (
        "📊 СТАТИСТИКА ТРЕБОВАНИЙ\n\n"
        f"Всего требований: {total}\n"
        f"✅ Функциональные: {len(requirements['functional'])}\n"
        f" Нефункциональные: {len(requirements['non_functional'])}\n\n"
        f"По приоритетам:\n"
        f"🔴 Высокий: {priorities['high']}\n"
        f"🟡 Средний: {priorities['medium']}\n"
        f"🟢 Низкий: {priorities['low']}"
    )

    await message.answer(text, reply_markup=main_menu())


@dp.message(F.text == "Экспорт")
async def export_requirements(message: Message, state: FSMContext):
    await state.clear()
    requirements = load_requirements()

    if not requirements["functional"] and not requirements["non_functional"]:
        await message.answer("📭 Нечего экспортировать", reply_markup=main_menu())
        return

    export_text = "ТРЕБОВАНИЯ К ПРОЕКТУ\n"
    export_text += "=" * 50 + "\n\n"
    export_text += f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"

    export_text += "ФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ:\n"
    export_text += "-" * 50 + "\n"
    for req in requirements["functional"]:
        export_text += f"\nID: {req['id']}\n"
        export_text += f"Название: {req['title']}\n"
        export_text += f"Описание: {req['description']}\n"
        export_text += f"Приоритет: {req['priority']}\n"
        export_text += f"Дата: {req['date']}\n"

    export_text += "\n\nНЕФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ:\n"
    export_text += "-" * 50 + "\n"
    for req in requirements["non_functional"]:
        export_text += f"\nID: {req['id']}\n"
        export_text += f"Название: {req['title']}\n"
        export_text += f"Описание: {req['description']}\n"
        export_text += f"Приоритет: {req['priority']}\n"
        export_text += f"Дата: {req['date']}\n"

    filename = f"requirements_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    filepath = os.path.join(os.getcwd(), filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(export_text)

        document = FSInputFile(filepath)

        await message.answer_document(
            document=document,
            caption=f"📄 Экспорт требований ({len(requirements['functional']) + len(requirements['non_functional'])} шт.)",
            reply_markup=main_menu()
        )

        os.remove(filepath)
        print(f"✅ Файл {filename} успешно отправлен и удален")

    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        await message.answer(f"❌ Ошибка при экспорте: {e}", reply_markup=main_menu())


async def main():
    print("🤖 Бот для сбора требований запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())