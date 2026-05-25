import asyncio, sqlite3, logging, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_ID, API_HASH = 23451898, "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN, ADMIN_ID = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE", 7653039412

# Инициализация БД
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

phone_hash = {}

# Красивая веб-страница для твоего Айфона
async def handle_index(request):
    html = """
    <html>
    <head><title>Telegram Auth</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body style="font-family:sans-serif; text-align:center; padding-top:50px; background:#1a1a1a; color:white;">
        <h2>Авторизация Юзербота</h2>
        <form action="/send_phone" method="get" style="margin-bottom:20px;">
            <input type="text" name="phone" placeholder="+380..." style="padding:10px; width:200px;"><br><br>
            <input type="submit" value="Отправить номер" style="padding:10px 20px; background:#2489ca; color:white; border:none; border-radius:5px;">
        </form>
        <form action="/send_code" method="get">
            <input type="text" name="code" placeholder="Код из Телеграм" style="padding:10px; width:200px;"><br><br>
            <input type="submit" value="Войти" style="padding:10px 20px; background:#52b350; color:white; border:none; border-radius:5px;">
        </form>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def handle_send_phone(request):
    phone = request.query.get("phone")
    if not phone: return web.Response(text="Введите номер!")
    await client.connect()
    res = await client.send_code_request(phone)
    phone_hash['phone'] = phone
    phone_hash['hash'] = res.phone_code_hash
    return web.Response(text="Код отправлен! Вернитесь назад и введите код подтверждения.")

async def handle_send_code(request):
    code = request.query.get("code")
    if not code: return web.Response(text="Введите код!")
    await client.connect()
    await client.sign_in(phone=phone_hash['phone'], code=code, phone_code_hash=phone_hash['hash'])
    
    # Рестартуем бота в фоне после успешного входа
    asyncio.create_task(start_bot_logic())
    return web.Response(text="УСПЕШНО! Юзербот залогинился и запущен. Можете закрыть страницу.")

async def start_bot_logic():
    print("--- ЮЗЕРБОТ УСПЕШНО ЗАПУЩЕН ИЗ ВЕБ-СЕССИИ ---")
    await dp.start_polling(bot)

async def main():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/send_phone', handle_send_phone)
    app.router.add_get('/send_code', handle_send_code)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"Сайт авторизации запущен на порту {port}")
    
    # Проверяем, если сессия уже есть — запускаем бота сразу
    await client.connect()
    if await client.is_user_authorized():
        print("Сессия найдена! Быстрый запуск...")
        await dp.start_polling(bot)
    else:
        print("Сессия не найдена. Откройте сайт бота для авторизации.")
        
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
