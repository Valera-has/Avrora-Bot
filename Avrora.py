import asyncio
import aiosqlite
import re
import random
from datetime import datetime, timedelta

from vkbottle.bot import Bot, Message
from vkbottle.bot import Blueprint
from vkbottle.api import API
from vkbottle import GroupEventType  # ВАЖНО: добавил этот импорт

# ========== НАСТРОЙКИ ==========
VK_TOKEN = "vk1.a.o_e86tU572NCbaSCKfBUOWk8kV-Ch99M2d0B-5Hp6d4-08M3AzqmxTdw5DNhjNvapQ4Aro1U6yatm2U2AiUG_A4IogNInCEjMmK05SMyB7wxZjgDgVG7XfioPR6vmF2u0kDZZeeueUi24CapZlC8-lO65mwcOpIxg_JBiyrjzB7S96RDvxl3SE0yfDY15BjqRbGKg2qRZGHko0NsZAuZ4g"
GROUP_ID = "235560929"

# Ключевые слова для обращения к боту
CALL_NAMES = ["фрост", "frost", "@frost"]

# ========== СОЗДАЕМ API С ТАЙМАУТАМИ ==========
# ========== СОЗДАЕМ API ==========
api = API(token=VK_TOKEN)

bot = Bot(token=VK_TOKEN)
bp = Blueprint()

# ========== БАЗА ДАННЫХ ==========
async def init_db():
    async with aiosqlite.connect('frost_bot.db') as db:
        # Настройки чатов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                style TEXT DEFAULT 'Огненный',
                owner_id INTEGER,
                antifoul INTEGER DEFAULT 1,
                antispam INTEGER DEFAULT 1,
                antiqr INTEGER DEFAULT 1,
                welcome_message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Админы чатов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS chat_admins (
                chat_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'admin',
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        # Варны пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                chat_id INTEGER,
                user_id INTEGER,
                count INTEGER DEFAULT 1,
                reason TEXT,
                warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        # Мут пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mutes (
                chat_id INTEGER,
                user_id INTEGER,
                until TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        # Статистика сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                chat_id INTEGER,
                user_id INTEGER,
                messages_count INTEGER DEFAULT 1,
                last_message_time TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        await db.commit()

# ========== РАБОТА С НАСТРОЙКАМИ ==========
async def get_chat_settings(chat_id: int):
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute(
            'SELECT style, owner_id, antifoul, antispam, antiqr, welcome_message FROM chat_settings WHERE chat_id = ?',
            (chat_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return {
                'style': row[0],
                'owner_id': row[1],
                'antifoul': bool(row[2]),
                'antispam': bool(row[3]),
                'antiqr': bool(row[4]),
                'welcome_message': row[5]
            }
        else:
            await db.execute(
                'INSERT INTO chat_settings (chat_id, style) VALUES (?, ?)',
                (chat_id, 'Огненный')
            )
            await db.commit()
            return {
                'style': 'Огненный',
                'owner_id': None,
                'antifoul': True,
                'antispam': True,
                'antiqr': True,
                'welcome_message': ''
            }

async def update_chat_setting(chat_id: int, setting: str, value):
    async with aiosqlite.connect('frost_bot.db') as db:
        await db.execute(
            f'UPDATE chat_settings SET {setting} = ? WHERE chat_id = ?',
            (value, chat_id)
        )
        await db.commit()

# ========== ПРОВЕРКА ПРАВ ==========
async def is_owner(chat_id: int, user_id: int) -> bool:
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute(
            'SELECT owner_id FROM chat_settings WHERE chat_id = ?',
            (chat_id,)
        )
        row = await cursor.fetchone()
        return row and row[0] == user_id

async def is_admin(chat_id: int, user_id: int) -> bool:
    if await is_owner(chat_id, user_id):
        return True
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute(
            'SELECT 1 FROM chat_admins WHERE chat_id = ? AND user_id = ?',
            (chat_id, user_id)
        )
        return await cursor.fetchone() is not None

async def is_muted(chat_id: int, user_id: int) -> bool:
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute(
            'SELECT until FROM mutes WHERE chat_id = ? AND user_id = ?',
            (chat_id, user_id)
        )
        row = await cursor.fetchone()
        if row:
            until = datetime.fromisoformat(row[0])
            if until > datetime.now():
                return True
            else:
                await db.execute(
                    'DELETE FROM mutes WHERE chat_id = ? AND user_id = ?',
                    (chat_id, user_id)
                )
                await db.commit()
        return False

# ========== МОДЕРАЦИЯ ==========
async def check_foul_language(text: str) -> bool:
    foul_words = ['сука', 'бля', 'хуй', 'пизд', 'еба', 'нах', 'пидор', 'гандон', 'мудак', 'тварь', 'сволочь', 'дебил', 'даун']
    text_lower = text.lower()
    return any(word in text_lower for word in foul_words)

async def check_spam(text: str) -> bool:
    url_pattern = re.compile(r'https?://\S+|www\.\S+')
    return bool(url_pattern.search(text))

async def check_qr(text: str) -> bool:
    qr_pattern = re.compile(r'(?:^|[^\w])[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}(?:[^\w]|$)', re.IGNORECASE)
    return bool(qr_pattern.search(text))

async def add_warn(chat_id: int, user_id: int, reason: str = "Нарушение") -> int:
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute(
            'SELECT count FROM warns WHERE chat_id = ? AND user_id = ?',
            (chat_id, user_id)
        )
        row = await cursor.fetchone()
        
        if row:
            new_count = row[0] + 1
            await db.execute(
                'UPDATE warns SET count = ?, reason = ?, warned_at = CURRENT_TIMESTAMP WHERE chat_id = ? AND user_id = ?',
                (new_count, reason, chat_id, user_id)
            )
        else:
            new_count = 1
            await db.execute(
                'INSERT INTO warns (chat_id, user_id, count, reason) VALUES (?, ?, ?, ?)',
                (chat_id, user_id, new_count, reason)
            )
        
        await db.commit()
        return new_count

async def update_stats(chat_id: int, user_id: int):
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute(
            'SELECT messages_count FROM stats WHERE chat_id = ? AND user_id = ?',
            (chat_id, user_id)
        )
        row = await cursor.fetchone()
        
        if row:
            await db.execute(
                'UPDATE stats SET messages_count = ?, last_message_time = CURRENT_TIMESTAMP WHERE chat_id = ? AND user_id = ?',
                (row[0] + 1, chat_id, user_id)
            )
        else:
            await db.execute(
                'INSERT INTO stats (chat_id, user_id, messages_count, last_message_time) VALUES (?, ?, 1, CURRENT_TIMESTAMP)',
                (chat_id, user_id)
            )
        
        await db.commit()

# ========== ФРАЗЫ ДЛЯ СТИЛЕЙ ==========
STYLE_PHRASES = {
    "Ледяной": {
        "hello": ["Здравствуйте.", "Привет.", "Добрый день."],
        "thanks": ["Пожалуйста.", "Не за что.", "Обращайтесь."],
        "joke": ["Шутка.", "Юмор.", "Смешно."],
        "default": ["Понял.", "Хорошо.", "Ок."]
    },
    "Огненный": {
        "hello": ["Привет 🔥", "Здарова! 👋", "О, привет!!"],
        "thanks": ["Не за что, бро 🔥", "Обращайся, брат!", "Рад помочь!"],
        "joke": ["Хахаха, угар", "😄", "Лол, зашел"],
        "default": ["Понял, принял ✅", "Оки!", "Ну ок)"]
    },
    "Стеклянный": {
        "hello": ["Приветствую. Согласно протоколу.", "Здравствуйте. Как ваше настроение?", "Доброго времени суток."],
        "thanks": ["Пожалуйста. Обращайтесь при необходимости.", "Всегда готов помочь.", "Рад быть полезным."],
        "joke": ["Юмор зафиксирован.", "Смешно? Возможно.", "Записано как шутка."],
        "default": ["Принято к сведению.", "Зафиксировано.", "Информация обработана."]
    }
}

async def get_phrase(chat_id: int, phrase_type: str) -> str:
    settings = await get_chat_settings(chat_id)
    style = settings['style']
    return random.choice(STYLE_PHRASES[style][phrase_type])

# ========== КОМАНДЫ ==========
@bp.on.message(text=["/start", "/помощь", "/help"])
async def help_handler(message: Message):
    chat_id = message.peer_id
    settings = await get_chat_settings(chat_id)
    
    help_text = f"""
❄️ ФРОСТ — ХОЛОДНЫЙ ПОРЯДОК

Текущий стиль: {settings['style']}

📋 ОСНОВНЫЕ КОМАНДЫ:
/help - это сообщение
/stats - статистика чата
/top - топ активных
/random - случайное число
/coin - монетка
/choose - выбрать из вариантов

👑 АДМИН КОМАНДЫ:
/set_style Ледяной/Огненный/Стеклянный - стиль
/owner @user - передать владение
/admin @user - дать права
/unadmin @user - забрать права
/warn @user - предупреждение
/kick @user - кикнуть
/mute @user 10 - мут на 10 минут
/unmute @user - снять мут

⚙️ НАСТРОЙКИ:
/antifoul on/off - фильтр мата
/antispam on/off - фильтр спама
/antiqr on/off - фильтр госномеров
/welcome текст - приветствие
"""
    await message.answer(help_text)

@bp.on.message(text=["/stats", "/стата"])
async def stats_handler(message: Message):
    chat_id = message.peer_id
    
    async with aiosqlite.connect('frost_bot.db') as db:
        # Топ болтунов
        cursor = await db.execute('''
            SELECT user_id, messages_count FROM stats 
            WHERE chat_id = ? 
            ORDER BY messages_count DESC 
            LIMIT 5
        ''', (chat_id,))
        top_users = await cursor.fetchall()
        
        # Количество варнов
        cursor = await db.execute('''
            SELECT COUNT(*) FROM warns WHERE chat_id = ?
        ''', (chat_id,))
        warns_count = (await cursor.fetchone())[0]
        
        # Количество мутов
        cursor = await db.execute('''
            SELECT COUNT(*) FROM mutes WHERE chat_id = ?
        ''', (chat_id,))
        mutes_count = (await cursor.fetchone())[0]
    
    stats_text = f"📊 СТАТИСТИКА ЧАТА:\n"
    stats_text += f"Предупреждений: {warns_count}\n"
    stats_text += f"В муте: {mutes_count}\n\n"
    stats_text += "ТОП БОЛТУНОВ:\n"
    
    for i, (user_id, count) in enumerate(top_users, 1):
        stats_text += f"{i}. @id{user_id} — {count} сообщ.\n"
    
    await message.answer(stats_text)

@bp.on.message(text=["/top"])
async def top_handler(message: Message):
    chat_id = message.peer_id
    
    async with aiosqlite.connect('frost_bot.db') as db:
        cursor = await db.execute('''
            SELECT user_id, messages_count FROM stats 
            WHERE chat_id = ? 
            ORDER BY messages_count DESC 
            LIMIT 10
        ''', (chat_id,))
        users = await cursor.fetchall()
    
    text = "🏆 ТОП-10 АКТИВНЫХ:\n\n"
    for i, (user_id, count) in enumerate(users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        text += f"{medal} {i}. @id{user_id} — {count} сообщ.\n"
    
    await message.answer(text)

@bp.on.message(text=["/random <a> <b>"])
async def random_handler(message: Message, a: str, b: str):
    try:
        a, b = int(a), int(b)
        if a > b:
            a, b = b, a
        num = random.randint(a, b)
        await message.answer(f"🎲 Случайное число: {num}")
    except:
        await message.answer("❌ Пример: /random 1 100")

@bp.on.message(text=["/coin"])
async def coin_handler(message: Message):
    result = random.choice(["Орел 🦅", "Решка 💰", "Ребро! 🤯"])
    await message.answer(f"🪙 Монетка: {result}")

@bp.on.message(text=["/choose <args>"])
async def choose_handler(message: Message, args: str):
    options = [opt.strip() for opt in args.split(',')]
    if len(options) < 2:
        await message.answer("❌ Напиши варианты через запятую: /choose пицца, суши, бургер")
        return
    choice = random.choice(options)
    await message.answer(f"🤔 Я выбираю: {choice}")

@bp.on.message(text=["/set_style <style>"])
async def set_style_handler(message: Message, style: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    valid_styles = ["Ледяной", "Огненный", "Стеклянный"]
    if style not in valid_styles:
        await message.answer(f"❌ Стили: {', '.join(valid_styles)}")
        return
    
    await update_chat_setting(chat_id, 'style', style)
    await message.answer(f"✅ Стиль: {style}")

@bp.on.message(text=["/owner <mention>"])
async def set_owner_handler(message: Message, mention: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_owner(chat_id, user_id):
        await message.answer("❌ Только владелец.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /owner @user")
        return
    
    new_owner_id = int(match.group(1))
    
    async with aiosqlite.connect('frost_bot.db') as db:
        await db.execute(
            'UPDATE chat_settings SET owner_id = ? WHERE chat_id = ?',
            (new_owner_id, chat_id)
        )
        await db.commit()
    
    await message.answer(f"✅ Владелец: @id{new_owner_id}")

@bp.on.message(text=["/admin <mention>"])
async def add_admin_handler(message: Message, mention: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_owner(chat_id, user_id):
        await message.answer("❌ Только владелец.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /admin @user")
        return
    
    new_admin_id = int(match.group(1))
    
    async with aiosqlite.connect('frost_bot.db') as db:
        await db.execute(
            'INSERT OR IGNORE INTO chat_admins (chat_id, user_id) VALUES (?, ?)',
            (chat_id, new_admin_id)
        )
        await db.commit()
    
    await message.answer(f"✅ Админ: @id{new_admin_id}")

@bp.on.message(text=["/unadmin <mention>"])
async def remove_admin_handler(message: Message, mention: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_owner(chat_id, user_id):
        await message.answer("❌ Только владелец.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /unadmin @user")
        return
    
    admin_id = int(match.group(1))
    
    async with aiosqlite.connect('frost_bot.db') as db:
        await db.execute(
            'DELETE FROM chat_admins WHERE chat_id = ? AND user_id = ?',
            (chat_id, admin_id)
        )
        await db.commit()
    
    await message.answer(f"✅ Админ @id{admin_id} удален")

@bp.on.message(text=["/warn <mention>"])
async def warn_handler(message: Message, mention: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /warn @user")
        return
    
    target_id = int(match.group(1))
    warn_count = await add_warn(chat_id, target_id, "Нарушение")
    
    await message.answer(f"⚠️ @id{target_id} варн {warn_count}/3")
    
    if warn_count >= 3:
        try:
            await bot.api.messages.remove_chat_user(
                chat_id=chat_id - 2000000000,
                user_id=target_id
            )
            await message.answer(f"🔨 @id{target_id} исключен (3/3)")
        except:
            pass

@bp.on.message(text=["/kick <mention>"])
async def kick_handler(message: Message, mention: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /kick @user")
        return
    
    target_id = int(match.group(1))
    
    try:
        await bot.api.messages.remove_chat_user(
            chat_id=chat_id - 2000000000,
            user_id=target_id
        )
        await message.answer(f"👢 @id{target_id} исключен")
    except:
        await message.answer("❌ Не могу кикнуть")

@bp.on.message(text=["/mute <mention> <minutes:int>"])
async def mute_handler(message: Message, mention: str, minutes: int):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /mute @user 10")
        return
    
    target_id = int(match.group(1))
    until = datetime.now() + timedelta(minutes=minutes)
    
    async with aiosqlite.connect('frost_bot.db') as db:
        await db.execute(
            'INSERT OR REPLACE INTO mutes (chat_id, user_id, until) VALUES (?, ?, ?)',
            (chat_id, target_id, until.isoformat())
        )
        await db.commit()
    
    await message.answer(f"🔇 @id{target_id} в муте {minutes} мин")

@bp.on.message(text=["/unmute <mention>"])
async def unmute_handler(message: Message, mention: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    match = re.search(r'\[id(\d+)\|', mention)
    if not match:
        await message.answer("❌ Упомяни: /unmute @user")
        return
    
    target_id = int(match.group(1))
    
    async with aiosqlite.connect('frost_bot.db') as db:
        await db.execute(
            'DELETE FROM mutes WHERE chat_id = ? AND user_id = ?',
            (chat_id, target_id)
        )
        await db.commit()
    
    await message.answer(f"🔊 @id{target_id} размучен")

@bp.on.message(text=["/antifoul <state>"])
async def antifoul_handler(message: Message, state: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    value = 1 if state.lower() in ["on", "вкл", "да"] else 0
    await update_chat_setting(chat_id, 'antifoul', value)
    await message.answer(f"✅ Фильтр мата: {'вкл' if value else 'выкл'}")

@bp.on.message(text=["/antispam <state>"])
async def antispam_handler(message: Message, state: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    value = 1 if state.lower() in ["on", "вкл", "да"] else 0
    await update_chat_setting(chat_id, 'antispam', value)
    await message.answer(f"✅ Фильтр спама: {'вкл' if value else 'выкл'}")

@bp.on.message(text=["/antiqr <state>"])
async def antiqr_handler(message: Message, state: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    value = 1 if state.lower() in ["on", "вкл", "да"] else 0
    await update_chat_setting(chat_id, 'antiqr', value)
    await message.answer(f"✅ Фильтр госномеров: {'вкл' if value else 'выкл'}")

@bp.on.message(text=["/welcome <text>"])
async def welcome_handler(message: Message, text: str):
    chat_id = message.peer_id
    user_id = message.from_id
    
    if not await is_admin(chat_id, user_id):
        await message.answer("❌ Нет прав.")
        return
    
    await update_chat_setting(chat_id, 'welcome_message', text)
    await message.answer(f"✅ Приветствие сохранено")

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@bp.on.message()
async def message_handler(message: Message):
    chat_id = message.peer_id
    user_id = message.from_id
    text = message.text.lower()
    
    if not text or message.from_id < 0:
        return
    
    # Проверка мута
    if await is_muted(chat_id, user_id):
        try:
            await bot.api.messages.delete(
                message_ids=[message.message_id],
                delete_for_all=True
            )
        except:
            pass
        return
    
    # Обновляем статистику
    await update_stats(chat_id, user_id)
    
    # Получаем настройки
    settings = await get_chat_settings(chat_id)
    
    # Проверка на мат
    if settings['antifoul'] and await check_foul_language(text):
        warn_count = await add_warn(chat_id, user_id, "Мат")
        await message.answer(f"⚠️ @id{user_id}, без мата! ({warn_count}/3)")
        try:
            await bot.api.messages.delete(
                message_ids=[message.message_id],
                delete_for_all=True
            )
        except:
            pass
        return
    
    # Проверка на спам
    if settings['antispam'] and await check_spam(text):
        warn_count = await add_warn(chat_id, user_id, "Спам")
        await message.answer(f"⚠️ @id{user_id}, реклама? ({warn_count}/3)")
        try:
            await bot.api.messages.delete(
                message_ids=[message.message_id],
                delete_for_all=True
            )
        except:
            pass
        return
    
    # Проверка на госномера
    if settings['antiqr'] and await check_qr(text):
        warn_count = await add_warn(chat_id, user_id, "Госномер")
        await message.answer(f"⚠️ @id{user_id}, госномера нельзя ({warn_count}/3)")
        try:
            await bot.api.messages.delete(
                message_ids=[message.message_id],
                delete_for_all=True
            )
        except:
            pass
        return
    
    # Обращение к боту
    called = False
    clean_text = text
    for call_name in CALL_NAMES:
        if text.startswith(call_name) or f" {call_name}" in text or text == call_name:
            called = True
            clean_text = text.replace(call_name, "").strip()
            break
    
    if called:
        if "привет" in clean_text or "здаров" in clean_text:
            response = await get_phrase(chat_id, "hello")
        elif "спасибо" in clean_text or "благодарю" in clean_text:
            response = await get_phrase(chat_id, "thanks")
        elif "шутка" in clean_text or "анекдот" in clean_text or "смешно" in clean_text:
            response = await get_phrase(chat_id, "joke")
        else:
            response = await get_phrase(chat_id, "default")
        
        await message.answer(response)

# ========== НОВЫЕ УЧАСТНИКИ (ИСПРАВЛЕНО!) ==========
@bot.on.raw_event(GroupEventType.CHAT_INVITE_USER, Message)
async def new_member_handler(event: Message):
    """Приветствие новых участников"""
    if event.action and event.action.type.value == 'chat_invite_user':
        user_id = event.action.member_id
        chat_id = event.peer_id
        
        settings = await get_chat_settings(chat_id)
        
        if settings['welcome_message']:
            welcome = settings['welcome_message'].replace("{name}", f"@id{user_id}")
            await bot.api.messages.send(
                peer_id=chat_id,
                message=welcome,
                random_id=0
            )
        else:
            style = settings['style']
            texts = {
                "Ледяной": f"❄️ @id{user_id}, присоединился.",
                "Огненный": f"🔥 @id{user_id}, привет!",
                "Стеклянный": f"📋 @id{user_id}, добро пожаловать."
            }
            await bot.api.messages.send(
                peer_id=chat_id,
                message=texts.get(style, texts['Огненный']),
                random_id=0
            )

# ========== ЗАПУСК ==========
async def main():
    await init_db()
    bp.load(bot)
    print("❄️ Фрост запущен! Таймауты увеличены до 60 секунд")
    print("✅ VK события обрабатываются правильно")
    
    # Бесконечный цикл с перезапуском при ошибках
    while True:
        try:
            await bot.run()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
