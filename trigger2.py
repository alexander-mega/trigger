import asyncio, sqlite3, logging, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_ID, API_HASH = 23451898, "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN, ADMIN_ID = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE", 7653039412
PHONE = "+380680434161"

# База данных
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

# Заглушка для сайта, чтобы Render видел открытый порт и радовался
async def handle_web(request):
    return web.Response(text="Бот активен. Управление происходит через Telegram чат.")

def main_menu(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🎵 Триггеры и Аудио", callback_data="menu_triggers")
    b.button(text="💬 Разрешенные Чаты", callback_data="menu_chats")
    b.adjust(1); return b.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    await m.answer("👋 Панель управления!\n\nНапиши /auth для авторизации юзербота.", reply_markup=main_menu(m.from_user.id))

@dp.message(Command("auth"))
async def cmd_auth(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    await m.answer("⏳ Проверяю авторизацию...")
    await client.connect()
    
    if await client.is_user_authorized():
        await m.answer("✅ Юзербот уже работает!")
        return
        
    res = await client.send_code_request(PHONE)
    user_auth_state["phone_code_hash"] = res.phone_code_hash
    await m.answer("📩 Код отправлен в твой Telegram!\n\n**Пришли мне этот код сюда в чат обычным сообщением.**")

@dp.message()
async def handle_auth_code(m: types.Message):
    if m.from_user.id != ADMIN_ID or "phone_code_hash" not in user_auth_state:
        return

    code = m.text.strip()
    await m.answer(f"⚙️ Вхожу с кодом {code}...")
    
    try:
        await client.connect()
        await client.sign_in(phone=PHONE, code=code, phone_code_hash=user_auth_state["phone_code_hash"])
        await m.answer("🎉 УРА! Юзербот успешно залогинился!")
        user_auth_state.clear()
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}\nПопробуй снова через /auth")

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
    # Моментальный запуск веб-сервера для Рендера
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"Web server started on port {port}")

    # Запуск Телеграм-бота параллельно
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
