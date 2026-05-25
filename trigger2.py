import asyncio, sqlite3, logging, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_ID, API_HASH = 23451898, "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN, ADMIN_ID = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE", 7653039412
PHONE = "+380680434161"

conn = sqlite3.connect("bot_data.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS triggers (keyword TEXT PRIMARY KEY, file_id TEXT, delay INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS allowed_chats (chat_id INTEGER PRIMARY KEY)")
c.execute("CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY)")
c.execute("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (ADMIN_ID,))
conn.commit()
conn.close()

bot, dp = Bot(token=BOT_TOKEN), Dispatcher()
client = TelegramClient('session_iphone', API_ID, API_HASH)

user_auth_state = {}

# Словарь для перевода слов в цифры
WORDS_TO_DIGITS = {
    "ноль": "0", "нуль": "0",
    "один": "1", "раз": "1",
    "два": "2",
    "три": "3",
    "четыре": "4",
    "пять": "5",
    "шесть": "6",
    "семь": "7",
    "восемь": "8",
    "девять": "9"
}

async def handle_web(request):
    return web.Response(text="Бот онлайн!")

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    b = InlineKeyboardBuilder()
    b.button(text="🔐 Авторизовать Юзербота", callback_data="start_auth")
    await m.answer("👋 Панель управления!", reply_markup=b.as_markup())

@dp.callback_query(F.data == "start_auth")
async def auth_callback(call: types.CallbackQuery):
    await call.message.answer("⏳ Запрашиваю код у Telegram API...")
    try:
        await client.connect()
        if await client.is_user_authorized():
            await call.message.answer("✅ Юзербот уже успешно авторизован!")
            return
        
        res = await client.send_code_request(PHONE)
        user_auth_state["phone_code_hash"] = res.phone_code_hash
        
        # Добавил сюда твою подсказку с жирным текстом и примером
        await call.message.answer(
            "📩 **КОД УСПЕШНО ОТПРАВЛЕН!**\n\n"
            "⚠️ **ВАЖНО:** Чтобы Telegram не заблокировал код, напиши его **СЛОВАМИ ЧЕРЕЗ ПРОБЕЛ**.\n\n"
            "📌 **ИНСТРУКЦИЯ:** Сделай ОТВЕТ (Reply) на это сообщение и напиши цифры буквами.\n\n"
            "📝 **ПРИМЕР:** Если тебе пришел код `48205`, то ты должен отправить в ответ строго:\n"
            "`четыре восемь два ноль пять`",
            reply_markup=types.ForceReply(selective=True)
        )
    except Exception as e:
        await call.message.answer(f"Ошибка: {e}")

@dp.message(F.reply_to_message)
async def handle_reply_code(m: types.Message):
    if m.from_user.id != ADMIN_ID or "phone_code_hash" not in user_auth_state: return
    
    text_words = m.text.lower().strip().split()
    converted_digits = []
    
    for word in text_words:
        if word in WORDS_TO_DIGITS:
            converted_digits.append(WORDS_TO_DIGITS[word])
        elif word.isdigit():
            converted_digits.append(word)
            
    code = "".join(converted_digits)
    
    if len(code) != 5:
        await m.answer(
            f"❌ **Ошибка распознавания!**\n"
            f"Не удалось собрать 5-значный код. У меня получилось только: `{code}`.\n\n"
            f"Пожалуйста, попробуй еще раз. Пиши строго слова через пробел, например:\n"
            f"`один два три четыре пять`"
        )
        return

    await m.answer(f"⚙️ Код успешно переведен из слов в цифры: `{code}`.\nПробую войти в аккаунт...")
    
    try:
        await client.connect()
        await client.sign_in(phone=PHONE, code=code, phone_code_hash=user_auth_state["phone_code_hash"])
        await m.answer("🎉 **УРА! Юзербот успешно залогинился и запущен!**")
        user_auth_state.clear()
    except Exception as e:
        await m.answer(f"❌ Ошибка входа: {e}\nНажми кнопку авторизации заново.")

@client.on(events.NewMessage(incoming=True))
async def userbot_handler(e):
    if not e.text: return
    chat_id, text_lower = e.chat_id, e.text.lower()
    conn = sqlite3.connect("bot_data.db")
    is_allowed = conn.execute("SELECT 1 FROM allowed_chats WHERE chat_id=?", (chat_id,)).fetchone()
    if not is_allowed: conn.close(); return
    triggers = conn.execute("SELECT keyword, file_id, delay FROM triggers").fetchall(); conn.close()
    for keyword, file_id, delay in triggers:
        if keyword in text_lower:
            if delay > 0: await asyncio.sleep(delay)
            await e.reply(file=file_id); break

async def main():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
