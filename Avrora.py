import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import sqlite3
import datetime
import time
import json
import re
from typing import Dict, List, Optional, Tuple
import threading
import os

# ========== КОНФИГУРАЦИЯ ==========
GROUP_TOKEN = "vk1.a.o_e86tU572NCbaSCKfBUOWk8kV-Ch99M2d0B-5Hp6d4-08M3AzqmxTdw5DNhjNvapQ4Aro1U6yatm2U2AiUG_A4IogNInCEjMmK05SMyB7wxZjgDgVG7XfioPR6vmF2u0kDZZeeueUi24CapZlC8-lO65mwcOpIxg_JBiyrjzB7S96RDvxl3SE0yfDY15BjqRbGKg2qRZGHko0NsZAuZ4g"
GROUP_ID = "235560929"

# ========== ЭМОЦИИ И СМАЙЛИКИ ==========
EMOJIS = {
    # Основные
    "robot": "🤖",
    "crown": "👑",
    "gear": "⚙️",
    "chart": "📊",
    "warning": "⚠️",
    "no_entry": "⛔",
    "mute": "🔇",
    "kick": "👢",
    "rules": "📜",
    "online": "🟢",
    "offline": "🔴",
    "sleep": "😴",
    "welcome": "👋",
    "role": "🎭",
    "profile": "👤",
    "help": "❓",
    "exit": "🚪",
    
    # Действия
    "check": "✅",
    "cross": "❌",
    "clock": "⏰",
    "calendar": "📅",
    "pen": "📝",
    "police": "👮",
    "user": "👤",
    "violator": "👤💢",
    "ban_hammer": "🔨",
    
    # Дополнительные
    "fire": "🔥",
    "star": "⭐",
    "light": "💡",
    "link": "🔗",
    "lock": "🔒",
    "unlock": "🔓",
    "bell": "🔔",
    "mega": "📣",
    "scroll": "📃",
    "book": "📖",
    "shield": "🛡️",
    "gavel": "⚖️",
    "handcuffs": "🔗",
    "key": "🔑",
    "door": "🚪",
    
    # Статусы
    "green_circle": "🟢",
    "red_circle": "🔴",
    "yellow_circle": "🟡",
    "blue_circle": "🔵",
    "purple_circle": "🟣",
    
    # Разное
    "thinking": "🤔",
    "cool": "😎",
    "smile": "😊",
    "sad": "😢",
    "angry": "😠",
    "party": "🎉",
    "confetti": "🎊",
    "trophy": "🏆",
    "medal": "🎖️",
    "flag": "🎌"
}

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        # Удаляем старую базу для пересоздания
        if os.path.exists('avrora_bot.db'):
            os.remove('avrora_bot.db')
            print(f"{EMOJIS['gear']} Старая база данных удалена, создаем новую...")
        
        self.conn = sqlite3.connect('avrora_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                chat_id INTEGER,
                nickname TEXT,
                role TEXT DEFAULT 'member',
                warns INTEGER DEFAULT 0,
                mute_until INTEGER DEFAULT 0,
                ban_until INTEGER DEFAULT 0,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                kicked INTEGER DEFAULT 0,
                PRIMARY KEY(user_id, chat_id)
            )
        ''')
        
        # Таблица настроек чата
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_message TEXT DEFAULT 'Добро пожаловать в чат!',
                rules_text TEXT DEFAULT '',
                max_warns INTEGER DEFAULT 3,
                ban_duration INTEGER DEFAULT 10
            )
        ''')
        
        # Таблица ролей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                user_id INTEGER,
                chat_id INTEGER,
                role_name TEXT,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        
        # Таблица варнов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                admin_id INTEGER,
                reason TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print(f"{EMOJIS['check']} База данных создана успешно")
    
    def get_user(self, user_id: int, chat_id: int) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        row = self.cursor.fetchone()
        if row:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))
        return None
    
    def add_user(self, user_id: int, chat_id: int, nickname: str = ""):
        if not self.get_user(user_id, chat_id):
            self.cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, chat_id, nickname, kicked) VALUES (?, ?, ?, 0)",
                (user_id, chat_id, nickname)
            )
            self.conn.commit()
        else:
            # Если пользователь уже есть, сбрасываем kicked статус
            self.cursor.execute(
                "UPDATE users SET kicked = 0 WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            self.conn.commit()
    
    def update_user(self, user_id: int, chat_id: int, **kwargs):
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [user_id, chat_id]
        
        self.cursor.execute(
            f"UPDATE users SET {set_clause} WHERE user_id = ? AND chat_id = ?",
            values
        )
        self.conn.commit()
    
    def add_warn(self, user_id: int, chat_id: int, admin_id: int, reason: str = ""):
        self.cursor.execute(
            "INSERT INTO warns_history (user_id, chat_id, admin_id, reason) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, admin_id, reason)
        )
        
        user = self.get_user(user_id, chat_id)
        new_warns = (user['warns'] if user else 0) + 1
        
        self.update_user(user_id, chat_id, warns=new_warns)
        
        # Проверяем на бан
        settings = self.get_chat_settings(chat_id)
        max_warns = settings.get('max_warns', 3) if settings else 3
        
        if new_warns >= max_warns:
            ban_duration = settings.get('ban_duration', 10) if settings else 10
            ban_until = int(time.time()) + (ban_duration * 86400)
            self.update_user(user_id, chat_id, ban_until=ban_until, warns=0, kicked=1)
            return 'ban'
        
        return 'warn'
    
    def remove_warn(self, user_id: int, chat_id: int):
        user = self.get_user(user_id, chat_id)
        if user and user['warns'] > 0:
            new_warns = user['warns'] - 1
            self.update_user(user_id, chat_id, warns=new_warns)
            return True
        return False
    
    def get_chat_settings(self, chat_id: int) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT * FROM chat_settings WHERE chat_id = ?",
            (chat_id,)
        )
        row = self.cursor.fetchone()
        if row:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))
        
        # Создаем настройки по умолчанию
        self.cursor.execute(
            "INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)",
            (chat_id,)
        )
        self.conn.commit()
        return self.get_chat_settings(chat_id)
    
    def update_chat_settings(self, chat_id: int, **kwargs):
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [chat_id]
        
        self.cursor.execute(
            f"UPDATE chat_settings SET {set_clause} WHERE chat_id = ?",
            values
        )
        self.conn.commit()
    
    def set_rules(self, chat_id: int, rules_text: str):
        self.cursor.execute(
            "UPDATE chat_settings SET rules_text = ? WHERE chat_id = ?",
            (rules_text, chat_id)
        )
        self.conn.commit()
    
    def get_rules(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        return settings.get('rules_text', '') if settings else ''
    
    def set_role(self, user_id: int, chat_id: int, role_name: str):
        self.cursor.execute(
            "INSERT OR REPLACE INTO roles (user_id, chat_id, role_name) VALUES (?, ?, ?)",
            (user_id, chat_id, role_name)
        )
        self.conn.commit()
    
    def get_role(self, user_id: int, chat_id: int) -> Optional[str]:
        self.cursor.execute(
            "SELECT role_name FROM roles WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    def get_all_roles(self, chat_id: int) -> List[Tuple]:
        self.cursor.execute(
            "SELECT user_id, role_name FROM roles WHERE chat_id = ?",
            (chat_id,)
        )
        return self.cursor.fetchall()
    
    def get_chat_stats(self, chat_id: int) -> Dict:
        self.cursor.execute(
            "SELECT COUNT(*) as total_users, "
            "SUM(CASE WHEN warns > 0 THEN 1 ELSE 0 END) as warned_users, "
            "SUM(CASE WHEN mute_until > ? THEN 1 ELSE 0 END) as muted_users, "
            "SUM(CASE WHEN ban_until > ? THEN 1 ELSE 0 END) as banned_users "
            "FROM users WHERE chat_id = ?",
            (int(time.time()), int(time.time()), chat_id)
        )
        row = self.cursor.fetchone()
        if row:
            stats = dict(zip(['total_users', 'warned_users', 'muted_users', 'banned_users'], row))
        else:
            stats = {'total_users': 0, 'warned_users': 0, 'muted_users': 0, 'banned_users': 0}
        
        # Количество варнов за сегодня
        today = datetime.date.today().strftime('%Y-%m-%d')
        self.cursor.execute(
            "SELECT COUNT(*) FROM warns_history WHERE chat_id = ? AND date(date) = date(?)",
            (chat_id, today)
        )
        stats['warns_today'] = self.cursor.fetchone()[0]
        
        return stats
    
    def get_user_stats(self, user_id: int, chat_id: int) -> Dict:
        user = self.get_user(user_id, chat_id)
        if not user:
            return {}
        
        # История варнов
        self.cursor.execute(
            "SELECT COUNT(*) FROM warns_history WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        total_warns = self.cursor.fetchone()[0]
        
        return {
            'user_id': user_id,
            'warns': user['warns'],
            'total_warns': total_warns,
            'muted': user['mute_until'] > time.time(),
            'banned': user['ban_until'] > time.time(),
            'kicked': user.get('kicked', 0),
            'role': self.get_role(user_id, chat_id) or user['role'],
            'join_date': user['join_date']
        }

# ========== ВК БОТ ==========
class VKAvroraBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=GROUP_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, GROUP_ID)
        self.db = Database()
        
        # Кэш админов чата
        self.chat_admins_cache = {}
        self.cache_timeout = 300
        
        print(f"{EMOJIS['robot']} AVRORA Manager Bot запущен!")
        print(f"{EMOJIS['crown']} Админы определяются автоматически по правам в чате")
    
    def send_message(self, chat_id: int, message: str, **kwargs):
        try:
            self.vk.messages.send(
                peer_id=2000000000 + chat_id,
                message=message,
                random_id=get_random_id(),
                **kwargs
            )
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка отправки: {e}")
    
    def get_chat_admins(self, chat_id: int) -> List[int]:
        cache_key = f"admins_{chat_id}"
        
        if cache_key in self.chat_admins_cache:
            cached_time, admins = self.chat_admins_cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return admins
        
        try:
            chat_info = self.vk.messages.getConversationMembers(
                peer_id=2000000000 + chat_id
            )
            
            admins = []
            for member in chat_info.get('items', []):
                if 'is_admin' in member and member['is_admin']:
                    user_id = member['member_id']
                    if user_id > 0:
                        admins.append(user_id)
            
            print(f"{EMOJIS['gear']} Найдены админы чата {chat_id}: {admins}")
            
            self.chat_admins_cache[cache_key] = (time.time(), admins)
            
            return admins
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка получения админов чата {chat_id}: {e}")
            return []
    
    def is_chat_admin(self, user_id: int, chat_id: int) -> bool:
        cache_key = f"admins_{chat_id}"
        if cache_key in self.chat_admins_cache:
            cached_time, admins = self.chat_admins_cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return user_id in admins
        
        admins = self.get_chat_admins(chat_id)
        return user_id in admins
    
    def get_user_info(self, user_id: int) -> Dict:
        try:
            users = self.vk.users.get(user_ids=[user_id], fields='first_name,last_name')
            if users:
                user = users[0]
                return {
                    'first_name': user.get('first_name', 'Пользователь'),
                    'last_name': user.get('last_name', ''),
                    'full_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                }
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка получения информации о пользователе {user_id}: {e}")
        
        return {
            'first_name': 'Пользователь',
            'last_name': '',
            'full_name': 'Пользователь'
        }
    
    def extract_mention_or_id(self, text: str, reply_message: Optional[Dict] = None) -> Optional[int]:
        # Проверяем упоминание: [id123456789|Имя]
        match = re.search(r'\[id(\d+)\|', text)
        if match:
            return int(match.group(1))
        
        # Проверяем упоминание: @id123456789
        match = re.search(r'@id(\d+)', text)
        if match:
            return int(match.group(1))
        
        # Если есть ответное сообщение, берем отправителя ответа
        if reply_message and 'from_id' in reply_message:
            return reply_message['from_id']
        
        # Пробуем найти цифровой ID в тексте
        match = re.search(r'\b(\d{5,})\b', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def parse_duration(self, duration_str: str) -> Tuple[int, str]:
        duration_str = duration_str.strip().lower()
        
        if not duration_str:
            return 0, "бессрочно"
        
        if duration_str in ['∞', 'inf', 'бессрочно', 'навсегда', 'forever']:
            return 0, "бессрочно"
        
        match = re.match(r'(\d+)\s*([dдhчmмsс]?)', duration_str)
        if not match:
            return 0, "неверный формат"
        
        number = int(match.group(1))
        unit = match.group(2)
        
        if unit in ['d', 'д']:
            seconds = number * 86400
            text = f"{number} дней"
        elif unit in ['h', 'ч']:
            seconds = number * 3600
            text = f"{number} часов"
        elif unit in ['m', 'м']:
            seconds = number * 60
            text = f"{number} минут"
        elif unit in ['s', 'с']:
            seconds = number
            text = f"{number} секунд"
        else:
            seconds = number * 86400
            text = f"{number} дней"
        
        return seconds, text
    
    def format_time(self, timestamp: int) -> str:
        if timestamp == 0:
            return "бессрочно"
        
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%d.%m.%Y %H:%M")
    
    # ========== КОМАНДЫ ==========
    
    def handle_admin_stats(self, user_id: int, chat_id: int):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        stats = self.db.get_chat_stats(chat_id)
        user_info = self.get_user_info(user_id)
        
        admins = self.get_chat_admins(chat_id)
        admin_list = []
        
        for admin_id in admins:
            if admin_id < 0:
                continue
                
            admin_info = self.get_user_info(admin_id)
            admin_list.append(f"{EMOJIS['police']} [id{admin_id}|{admin_info['full_name']}]")
        
        message = f"""{EMOJIS['robot']} {EMOJIS['chart']} Статистика администратора [id{user_id}|{user_info['full_name']}]

{EMOJIS['chart']} Общая статистика чата:
{EMOJIS['user']} Всего участников: {stats['total_users']}
{EMOJIS['warning']} С предупреждениями: {stats['warned_users']}
{EMOJIS['mute']} В муте: {stats['muted_users']}
{EMOJIS['no_entry']} В бане: {stats['banned_users']}
{EMOJIS['calendar']} Варнов сегодня: {stats['warns_today']}

{EMOJIS['gear']} Настройки чата:
{self.get_chat_settings_info(chat_id)}

{EMOJIS['crown']} Администраторы чата ({len(admin_list)}):
{chr(10).join(admin_list) if admin_list else f"{EMOJIS['cross']} Нет данных"}

{EMOJIS['light']} Используйте /help для списка команд
""".strip()
        self.send_message(chat_id, message)
    
    def get_chat_settings_info(self, chat_id: int) -> str:
        settings = self.db.get_chat_settings(chat_id)
        rules_text = settings.get('rules_text', '')
        has_rules = bool(rules_text.strip())
        
        return f"""{EMOJIS['welcome']} Приветствие: {settings['welcome_message'][:50]}...
{EMOJIS['rules']} Правила: {'✅ Установлены' if has_rules else '❌ Не установлены'}
{EMOJIS['warning']} Макс. варнов: {settings['max_warns']}
{EMOJIS['ban_hammer']} Длительность автобана: {settings['ban_duration']} дней"""
    
    def handle_create_rules(self, user_id: int, chat_id: int, args: str):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        if not args.strip():
            self.send_message(chat_id, f"""{EMOJIS['rules']} Использование: /createpravila [текст правил]

{EMOJIS['light']} Пример:
/createpravila 1. Не спамить
2. Уважать других
3. Не рекламировать""")
            return
        
        self.db.set_rules(chat_id, args.strip())
        
        message = f"""{EMOJIS['check']} {EMOJIS['rules']} Правила чата обновлены!

{EMOJIS['scroll']} Новые правила установлены.
{EMOJIS['light']} Теперь участники могут посмотреть их командой /правила

{EMOJIS['book']} Для просмотра: /правила
{EMOJIS['pen']} Для редактирования: /createpravila [новый текст]
""".strip()
        self.send_message(chat_id, message)
    
    def handle_mute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split()
        if len(parts) < 1 and not reply_message:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование: 
1. /mute @avroramanager время причина
2. /mute время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
30m - 30 минут
2h - 2 часа
1d - 1 день
7d - 7 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/mute @avroramanager 30m спам
/mute 1d флуд (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        # Если есть ответ на сообщение
        if reply_message:
            target_id = reply_message['from_id']
            # Проверяем, не является ли первая часть текста упоминанием
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                # Если есть упоминание, игнорируем reply_message и берем упомянутого пользователя
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            # Если нет ответа, то первая часть должна быть упоминанием
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @avroramanager, ID или ответьте на сообщение.")
            return
        
        if target_id == user_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя замутить самого себя!")
            return
        
        if self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя замутить администратора чата!")
            return
        
        if len(parts) <= duration_idx:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указано время мута.")
            return
        
        duration_seconds, duration_text = self.parse_duration(parts[duration_idx])
        
        reason = ""
        if len(parts) > reason_idx:
            reason = ' '.join(parts[reason_idx:])
        elif len(parts) == reason_idx and duration_idx == 0:
            reason = ' '.join(parts[reason_idx:])
        
        if not reason:
            reason = "Не указана"
        
        if duration_seconds == 0 and duration_text == "бессрочно":
            mute_until = 0
        elif duration_seconds == 0 and duration_text == "неверный формат":
            self.send_message(chat_id, f"{EMOJIS['cross']} Неверный формат времени. Используйте: 30m, 2h, 1d и т.д.")
            return
        else:
            mute_until = int(time.time()) + duration_seconds
        
        self.db.add_user(target_id, chat_id)
        self.db.update_user(target_id, chat_id, mute_until=mute_until)
        
        # Удаляем сообщение, на которое был ответ (если есть)
        if reply_message and 'conversation_message_id' in reply_message:
            try:
                self.vk.messages.delete(
                    conversation_message_ids=[reply_message['conversation_message_id']],
                    delete_for_all=1,
                    peer_id=2000000000 + chat_id
                )
                print(f"{EMOJIS['check']} Удалено сообщение пользователя {target_id}")
            except Exception as e:
                print(f"{EMOJIS['cross']} Не удалось удалить сообщение: {e}")
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        if mute_until == 0:
            time_text = "бессрочно"
        else:
            time_text = f"{duration_text} (до {self.format_time(mute_until)})"
        
        message = f"""{EMOJIS['mute']} Пользователь замучен

{EMOJIS['violator']} Нарушитель: [id{target_id}|{target_info['full_name']}]
{EMOJIS['clock']} Длительность: {time_text}
{EMOJIS['pen']} Причина: {reason}
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['warning']} Нарушитель не сможет писать в чат до окончания мута.
""".strip()
        self.send_message(chat_id, message)
    
    def handle_warn(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=1)
        
        target_id = None
        reason = ""
        
        if parts and (parts[0].startswith('@') or 'id' in parts[0] or (parts and parts[0].isdigit())):
            target_id = self.extract_mention_or_id(parts[0], reply_message)
            if target_id and len(parts) > 1:
                reason = parts[1]
            elif target_id:
                reason = "Не указана"
        
        if not target_id and reply_message:
            target_id = self.extract_mention_or_id('', reply_message)
            reason = args if args.strip() else "Не указана"
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @avroramanager или ответьте на сообщение.")
            return
        
        if target_id == user_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя выдать предупреждение самому себе!")
            return
        
        if self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя выдать предупреждение администратору чата!")
            return
        
        if not reason:
            reason = "Не указана"
        
        self.db.add_user(target_id, chat_id)
        result = self.db.add_warn(target_id, chat_id, user_id, reason)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        user_stats = self.db.get_user_stats(target_id, chat_id)
        
        settings = self.db.get_chat_settings(chat_id)
        max_warns = settings.get('max_warns', 3) if settings else 3
        
        if result == 'ban':
            message = f"""{EMOJIS['no_entry']} Пользователь забанен!

{EMOJIS['violator']} Нарушитель: [id{target_id}|{target_info['full_name']}]
{EMOJIS['pen']} Причина: {reason}
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]
{EMOJIS['warning']} Получено варнов: {max_warns}/{max_warns}

{EMOJIS['ban_hammer']} Результат: Автоматический бан на {settings.get('ban_duration', 10)} дней за превышение лимита предупреждений.
""".strip()
            try:
                self.vk.messages.removeChatUser(
                    chat_id=chat_id,
                    user_id=target_id
                )
            except Exception as e:
                print(f"{EMOJIS['cross']} Ошибка при кике забаненного пользователя: {e}")
        else:
            message = f"""{EMOJIS['warning']} Выдано предупреждение

{EMOJIS['violator']} Нарушитель: [id{target_id}|{target_info['full_name']}]
{EMOJIS['pen']} Причина: {reason}
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]
{EMOJIS['chart']} Варнов: {user_stats['warns']}/{max_warns}

{EMOJIS['light']} Внимание: При достижении {max_warns} предупреждений последует автоматический бан на {settings.get('ban_duration', 10)} дней.
""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_kick(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=1)
        
        target_id = None
        reason = ""
        
        if parts and (parts[0].startswith('@') or 'id' in parts[0] or (parts and parts[0].isdigit())):
            target_id = self.extract_mention_or_id(parts[0], reply_message)
            if target_id and len(parts) > 1:
                reason = parts[1]
            elif target_id:
                reason = "Не указана"
        
        if not target_id and reply_message:
            target_id = self.extract_mention_or_id('', reply_message)
            reason = args if args.strip() else "Не указана"
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @avroramanager или ответьте на сообщение.")
            return
        
        if target_id == user_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя кикнуть самого себя! Используйте /q")
            return
        
        if self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя кикнуть администратора чата!")
            return
        
        if not reason:
            reason = "Не указана"
        
        try:
            self.vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=target_id
            )
            
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['kick']} Пользователь кикнут

{EMOJIS['violator']} Нарушитель: [id{target_id}|{target_info['full_name']}]
{EMOJIS['pen']} Причина: {reason}
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Пользователь может вернуться в чат по приглашению.
""".strip()
            self.send_message(chat_id, message)
            
        except Exception as e:
            error_msg = str(e)
            if "no access" in error_msg or "permission" in error_msg:
                self.send_message(chat_id, f"{EMOJIS['cross']} У меня нет прав на кик пользователей. Сделайте бота администратором чата!")
            else:
                self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка при кике: {error_msg}")
    
    def handle_ban(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split()
        if len(parts) < 1 and not reply_message:
            self.send_message(chat_id, f"""{EMOJIS['no_entry']} Использование:
1. /ban @avroramanager время причина
2. /ban время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
1d - 1 день
7d - 7 дней
30d - 30 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/ban @avroramanager 10d спам
/ban 7d нарушение (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        # Если есть ответ на сообщение
        if reply_message:
            target_id = reply_message['from_id']
            # Проверяем, не является ли первая часть текста упоминанием
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                # Если есть упоминание, игнорируем reply_message и берем упомянутого пользователя
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            # Если нет ответа, то первая часть должна быть упоминанием
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @avroramanager, ID или ответьте на сообщение.")
            return
        
        if target_id == user_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя забанить самого себя!")
            return
        
        if self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя забанить администратора чата!")
            return
        
        if len(parts) <= duration_idx:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указано время бана.")
            return
        
        duration_seconds, duration_text = self.parse_duration(parts[duration_idx])
        
        reason = ""
        if len(parts) > reason_idx:
            reason = ' '.join(parts[reason_idx:])
        elif len(parts) == reason_idx and duration_idx == 0:
            reason = ' '.join(parts[reason_idx:])
        
        if not reason:
            reason = "Не указана"
        
        if duration_seconds == 0 and duration_text == "бессрочно":
            ban_until = 0
        elif duration_seconds == 0 and duration_text == "неверный формат":
            self.send_message(chat_id, f"{EMOJIS['cross']} Неверный формат времени. Используйте: 1d, 7d, 30d и т.д.")
            return
        else:
            ban_until = int(time.time()) + duration_seconds
        
        self.db.add_user(target_id, chat_id)
        self.db.update_user(target_id, chat_id, ban_until=ban_until, kicked=1)
        
        try:
            self.vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=target_id
            )
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка при кике при бане: {e}")
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        if ban_until == 0:
            time_text = "бессрочно"
        else:
            time_text = f"{duration_text} (до {self.format_time(ban_until)})"
        
        message = f"""{EMOJIS['no_entry']} Пользователь забанен!

{EMOJIS['violator']} Нарушитель: [id{target_id}|{target_info['full_name']}]
{EMOJIS['clock']} Длительность: {time_text}
{EMOJIS['pen']} Причина: {reason}
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['warning']} Пользователь будет автоматически кикаться при попытке вернуться в чат.
""".strip()
        self.send_message(chat_id, message)
    
    def handle_welcome(self, user_id: int, chat_id: int, args: str):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        if not args.strip():
            self.send_message(chat_id, f"{EMOJIS['welcome']} Использование: /приветствие [текст]\n\n{EMOJIS['light']} Пример: /приветствие Добро пожаловать в наш чат! Правила: /правила")
            return
        
        self.db.update_chat_settings(chat_id, welcome_message=args.strip())
        
        message = f"""{EMOJIS['check']} {EMOJIS['welcome']} Приветствие обновлено!

{EMOJIS['scroll']} Новое приветствие:
{args.strip()}

{EMOJIS['light']} Теперь это сообщение будет показываться новым участникам.
""".strip()
        self.send_message(chat_id, message)
    
    def handle_self_kick(self, user_id: int, chat_id: int):
        try:
            self.vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )
        except Exception as e:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка при выходе: {str(e)}")
    
    def handle_set_nick(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /snick @avroramanager роль
2. /snick роль (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/snick @avroramanager Босс
/snick Модератор (при ответе на сообщение)""")
            return
        
        target_id = None
        role_name = ""
        
        if parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit():
            target_id = self.extract_mention_or_id(parts[0], reply_message)
            if target_id:
                role_name = parts[1]
        
        if not target_id and reply_message:
            target_id = self.extract_mention_or_id('', reply_message)
            role_name = args
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @avroramanager, ID или ответьте на сообщение.")
            return
        
        if not role_name:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указана роль.")
            return
        
        self.db.set_role(target_id, chat_id, role_name)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['role']} Роль установлена

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['crown']} Роль: {role_name}
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Используйте /niclist для просмотра всех ролей.
""".strip()
        self.send_message(chat_id, message)
    
    def handle_nick_list(self, user_id: int, chat_id: int):
        roles = self.db.get_all_roles(chat_id)
        
        if not roles:
            self.send_message(chat_id, f"{EMOJIS['role']} В этом чате еще нет установленных ролей.\n{EMOJIS['light']} Администраторы могут выдать роли командой /snick [@avroramanager] [роль]")
            return
        
        message = f"{EMOJIS['role']} {EMOJIS['scroll']} Список ролей в чате:\n\n"
        
        for user_id, role_name in roles[:20]:
            user_info = self.get_user_info(user_id)
            message += f"{EMOJIS['star']} [id{user_id}|{user_info['full_name']}] - {role_name}\n"
        
        if len(roles) > 20:
            message += f"\n{EMOJIS['light']} ... и еще {len(roles) - 20} ролей"
        
        self.send_message(chat_id, message.strip())
    
    def handle_rules(self, user_id: int, chat_id: int):
        rules_text = self.db.get_rules(chat_id)
        
        if not rules_text or not rules_text.strip():
            message = f"""{EMOJIS['rules']} Правила чата

{EMOJIS['warning']} Правила еще не установлены.

{EMOJIS['police']} Администраторы могут установить правила командой:
/createpravila [текст правил]

{EMOJIS['light']} Пример:
/createpravila 1. Не спамить
2. Уважать других участников
3. Не размещать рекламу
""".strip()
        else:
            message = f"""{EMOJIS['rules']} Правила чата:

{rules_text}

──────────────
{EMOJIS['gavel']} Система наказаний:
{EMOJIS['warning']} 1-2 предупреждения - предупреждение
{EMOJIS['no_entry']} 3 предупреждения - автоматический бан
{EMOJIS['police']} Администраторы могут выдавать муты и баны

{EMOJIS['light']} По всем вопросам обращайтесь к администраторам.
""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_unmute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование:
1. /размут @avroramanager
2. /размут (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/размут @avroramanager
/размут (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, mute_until=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь размучен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Теперь пользователь может писать в чат.
""".strip()
        self.send_message(chat_id, message)
    
    def handle_unban(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['no_entry']} Использование:
1. /разбан @avroramanager
2. /разбан (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/разбан @avroramanager
/разбан (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, ban_until=0, kicked=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь разбанен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь может вернуться в чат.
""".strip()
        self.send_message(chat_id, message)
    
    def handle_unwarn(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['warning']} Использование:
1. /снятьварн @avroramanager
2. /снятьварн (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/снятьварн @avroramanager
/снятьварн (при ответе на сообщение)""")
            return
        
        if self.db.remove_warn(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} {EMOJIS['warning']} Снято предупреждение

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Одно предупреждение снято.
""".strip()
        else:
            message = f"{EMOJIS['cross']} У пользователя нет активных предупреждений."
        
        self.send_message(chat_id, message)
    
    def handle_help(self, user_id: int, chat_id: int):
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        if is_admin:
            message = f"""{EMOJIS['robot']} Avrora Chat Manager - Помощь

{EMOJIS['crown']} Команды администраторов чата:
{EMOJIS['chart']} /admin - Статистика админа
{EMOJIS['rules']} /createpravila текст - Установить правила чата
{EMOJIS['mute']} /mute [@avroramanager или ответ] время причина - Мут пользователя
{EMOJIS['warning']} /warn [@avroramanager или ответ] причина - Предупреждение
{EMOJIS['kick']} /kick [@avroramanager или ответ] причина - Кик пользователя
{EMOJIS['no_entry']} /ban [@avroramanager или ответ] время причина - Бан пользователя
{EMOJIS['welcome']} /приветствие текст - Установить приветствие
{EMOJIS['role']} /snick [@avroramanager или ответ] роль - Выдать роль
{EMOJIS['unlock']} /размут [@avroramanager или ответ] - Снять мут
{EMOJIS['unlock']} /разбан [@avroramanager или ответ] - Снять бан
{EMOJIS['check']} /снятьварн [@avroramanager или ответ] - Снять предупреждение

{EMOJIS['user']} Команды для всех участников:
{EMOJIS['help']} /help - Эта справка
{EMOJIS['exit']} /q - Выйти из чата
{EMOJIS['role']} /niclist - Список ролей
{EMOJIS['rules']} /правила - Правила чата
{EMOJIS['online']} /онлайн - Кто онлайн
{EMOJIS['profile']} /профиль - Ваша статистика

{EMOJIS['clock']} Примеры времени для /mute и /ban:
{EMOJIS['light']} 30m - 30 минут
{EMOJIS['light']} 2h - 2 часа  
{EMOJIS['light']} 1d - 1 день
{EMOJIS['light']} 7d - 7 дней
{EMOJIS['light']} 30d - 30 дней
{EMOJIS['light']} 0 или пусто - бессрочно

{EMOJIS['light']} Примечание: Администратором считается владелец чата и пользователи с правами администратора в настройках беседы.
""".strip()
        else:
            message = f"""{EMOJIS['robot']} Avrora Chat Manager - Помощь

{EMOJIS['user']} Доступные команды:
{EMOJIS['help']} /help - Эта справка
{EMOJIS['exit']} /q - Выйти из чата
{EMOJIS['role']} /niclist - Список ролей
{EMOJIS['rules']} /правила - Правила чата
{EMOJIS['online']} /онлайн - Кто онлайн
{EMOJIS['profile']} /профиль - Ваша статистика

{EMOJIS['gavel']} Система наказаний:
{EMOJIS['warning']} 3 предупреждения = автоматический бан
{EMOJIS['mute']} Мут ограничивает отправку сообщений
{EMOJIS['no_entry']} Бан исключает из чата на время

{EMOJIS['light']} По всем вопросам обращайтесь к администраторам чата.
""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_profile(self, user_id: int, chat_id: int):
        self.db.add_user(user_id, chat_id)
        stats = self.db.get_user_stats(user_id, chat_id)
        user_info = self.get_user_info(user_id)
        
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        db_role = self.db.get_role(user_id, chat_id)
        if db_role:
            role = f"{EMOJIS['crown']} {db_role}"
        elif is_admin:
            role = f"{EMOJIS['crown']} Администратор"
        else:
            role = f"{EMOJIS['user']} Участник"
        
        status = f"{EMOJIS['green_circle']} Активен"
        if stats.get('muted'):
            status = f"{EMOJIS['mute']} В муте"
        elif stats.get('banned'):
            status = f"{EMOJIS['no_entry']} Забанен"
        
        join_date = stats.get('join_date', 'Неизвестно')
        if join_date and join_date != 'Неизвестно':
            try:
                dt = datetime.datetime.strptime(join_date[:19], "%Y-%m-%d %H:%M:%S")
                join_date = dt.strftime("%d.%m.%Y")
            except:
                pass
        
        message = f"""{EMOJIS['profile']} Ваш профиль

{EMOJIS['user']} Имя: {user_info['full_name']}
{EMOJIS['role']} Роль: {role}
{EMOJIS['warning']} Активные предупреждения: {stats.get('warns', 0)}
{EMOJIS['chart']} Всего получено варнов: {stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{EMOJIS['star']} Статус: {status}

{EMOJIS['light']} Чтобы увидеть все команды, напишите /help
""".strip()
        self.send_message(chat_id, message)
    
    def handle_online(self, user_id: int, chat_id: int):
        try:
            chat_info = self.vk.messages.getConversationMembers(
                peer_id=2000000000 + chat_id,
                fields='online,first_name,last_name'
            )
            
            online_users = []
            
            for member in chat_info.get('items', []):
                if 'member_id' in member and member['member_id'] > 0:
                    if member.get('online') == 1:
                        user_id = member['member_id']
                        first_name = member.get('first_name', 'Пользователь')
                        last_name = member.get('last_name', '')
                        name = f"{first_name} {last_name}".strip()
                        online_users.append(f"{EMOJIS['green_circle']} [id{user_id}|{name}]")
            
            if online_users:
                message = f"{EMOJIS['online']} Сейчас онлайн:\n\n" + "\n".join(online_users[:20])
                if len(online_users) > 20:
                    message += f"\n\n{EMOJIS['light']} ... и еще {len(online_users) - 20} участников"
            else:
                message = f"{EMOJIS['sleep']} Сейчас никого нет онлайн"
            
            self.send_message(chat_id, message)
            
        except Exception as e:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка: {str(e)}")
    
    def handle_new_chat_member(self, chat_id: int, user_id: int):
        user_data = self.db.get_user(user_id, chat_id)
        if user_data and user_data.get('kicked', 0) == 1:
            if user_data['ban_until'] > time.time() or user_data['ban_until'] == 0:
                try:
                    self.vk.messages.removeChatUser(
                        chat_id=chat_id,
                        user_id=user_id
                    )
                    print(f"{EMOJIS['kick']} Забаненный пользователь {user_id} пытался вернуться в чат {chat_id}")
                    return
                except Exception as e:
                    print(f"{EMOJIS['cross']} Ошибка при кике забаненного: {e}")
        
        self.db.add_user(user_id, chat_id)
        
        settings = self.db.get_chat_settings(chat_id)
        welcome_message = settings.get('welcome_message', 'Добро пожаловать в чат!')
        
        user_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['welcome']} Добро пожаловать!

{EMOJIS['party']} Приветствуем нового участника:
[id{user_id}|{user_info['full_name']}]

{EMOJIS['bell']} {welcome_message}

{EMOJIS['rules']} Обязательно ознакомьтесь с /правила
{EMOJIS['help']} Помощь по командам: /help
""".strip()
        self.send_message(chat_id, message)
    
    def check_punishments(self):
        while True:
            try:
                current_time = int(time.time())
                
                self.db.cursor.execute(
                    "SELECT user_id, chat_id FROM users WHERE mute_until > 0 AND mute_until < ?",
                    (current_time,)
                )
                muted_users = self.db.cursor.fetchall()
                for user_id, chat_id in muted_users:
                    self.db.update_user(user_id, chat_id, mute_until=0)
                    print(f"{EMOJIS['check']} Мут истек: пользователь {user_id} в чате {chat_id}")
                
                self.db.cursor.execute(
                    "SELECT user_id, chat_id FROM users WHERE ban_until > 0 AND ban_until < ?",
                    (current_time,)
                )
                banned_users = self.db.cursor.fetchall()
                for user_id, chat_id in banned_users:
                    self.db.update_user(user_id, chat_id, ban_until=0, kicked=0)
                    print(f"{EMOJIS['check']} Бан истек: пользователь {user_id} в чате {chat_id}")
                
                self.db.conn.commit()
                
            except Exception as e:
                print(f"{EMOJIS['cross']} Ошибка проверки наказаний: {e}")
            
            time.sleep(60)
    
    def process_message(self, event):
        try:
            message = event.object.message
            chat_id = event.chat_id
            user_id = message['from_id']
            text = message.get('text', '').strip()
            
            print(f"{EMOJIS['robot']} Сообщение от {user_id} в чате {chat_id}: {text}")
            
            user_data = self.db.get_user(user_id, chat_id)
            
            # Проверка на бан
            if user_data and user_data['ban_until'] > 0:
                if user_data['ban_until'] == 0:
                    ban_active = True
                else:
                    ban_active = user_data['ban_until'] > time.time()
                
                if ban_active:
                    try:
                        self.vk.messages.removeChatUser(
                            chat_id=chat_id,
                            user_id=user_id
                        )
                        print(f"{EMOJIS['kick']} Кикнут забаненный пользователь {user_id} из чата {chat_id}")
                    except Exception as e:
                        print(f"{EMOJIS['cross']} Ошибка при кике забаненного: {e}")
                    return
            
            # Проверка на мут
            if user_data and user_data['mute_until'] > 0:
                if user_data['mute_until'] == 0:
                    mute_active = True
                else:
                    mute_active = user_data['mute_until'] > time.time()
                
                if mute_active:
                    # Пробуем удалить сообщение
                    try:
                        msg_id = message.get('conversation_message_id')
                        if msg_id:
                            self.vk.messages.delete(
                                conversation_message_ids=[msg_id],
                                delete_for_all=1,
                                peer_id=2000000000 + chat_id
                            )
                            print(f"{EMOJIS['mute']} Удалено сообщение от замученного пользователя {user_id}")
                    except Exception as e:
                        print(f"{EMOJIS['cross']} Не удалось удалить сообщение замученного: {e}")
                    return
        
            if text.startswith('/'):
                command_parts = text.split(maxsplit=1)
                command = command_parts[0].lower()
                args = command_parts[1] if len(command_parts) > 1 else ""
                
                reply_message = message.get('reply_message')
                
                if command == '/admin':
                    self.handle_admin_stats(user_id, chat_id)
                
                elif command in ['/createpravila', '/создатьправила', '/правилаустановить']:
                    self.handle_create_rules(user_id, chat_id, args)
                
                elif command == '/mute':
                    self.handle_mute(user_id, chat_id, args, reply_message)
                
                elif command == '/warn':
                    self.handle_warn(user_id, chat_id, args, reply_message)
                
                elif command == '/kick':
                    self.handle_kick(user_id, chat_id, args, reply_message)
                
                elif command == '/ban':
                    self.handle_ban(user_id, chat_id, args, reply_message)
                
                elif command in ['/приветствие', '/привет', '/welcome']:
                    self.handle_welcome(user_id, chat_id, args)
                
                elif command in ['/q', '/quit', '/выйти']:
                    self.handle_self_kick(user_id, chat_id)
                
                elif command in ['/snick', '/setnick', '/роль']:
                    self.handle_set_nick(user_id, chat_id, args, reply_message)
                
                elif command in ['/niclist', '/nicklist', '/роли']:
                    self.handle_nick_list(user_id, chat_id)
                
                elif command in ['/правила', '/rules']:
                    self.handle_rules(user_id, chat_id)
                
                elif command in ['/размут', '/unmute']:
                    self.handle_unmute(user_id, chat_id, args, reply_message)
                
                elif command in ['/разбан', '/unban']:
                    self.handle_unban(user_id, chat_id, args, reply_message)
                
                elif command in ['/снятьварн', '/unwarn', '/снятьпред']:
                    self.handle_unwarn(user_id, chat_id, args, reply_message)
                
                elif command == '/help':
                    self.handle_help(user_id, chat_id)
                
                elif command == '/профиль':
                    self.handle_profile(user_id, chat_id)
                
                elif command == '/онлайн':
                    self.handle_online(user_id, chat_id)
                
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. Используйте /help для списка команд.")
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка обработки сообщения: {e}")
    
    def run(self):
        punishment_thread = threading.Thread(target=self.check_punishments, daemon=True)
        punishment_thread.start()
        
        print(f"{EMOJIS['robot']} Бот запущен и слушает сообщения...")
        print(f"{EMOJIS['crown']} Админы определяются автоматически по правам в каждом чате")
        print(f"{EMOJIS['gear']} База данных: avrora_bot.db")
        
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat:
                        self.process_message(event)
                
                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    pass
                
                elif event.type == VkBotEventType.MESSAGE_ALLOW:
                    if 'chat_id' in event.object:
                        chat_id = event.object['chat_id']
                        user_id = event.object['user_id']
                        self.handle_new_chat_member(chat_id, user_id)
            
            except Exception as e:
                print(f"{EMOJIS['cross']} Ошибка в основном цикле: {e}")

if __name__ == "__main__":
    print(f"""
    {EMOJIS['robot']} ====================================
    🤖 AVRORA Manager Bot
    👑 Управление чатом ВКонтакте
    🚀 Запуск...
    {EMOJIS['robot']} ====================================
    """)
    
    # Проверка прав бота
    print(f"{EMOJIS['light']} Проверяем права бота...")
    print(f"{EMOJIS['light']} Для работы мута боту нужны права:")
    print(f"{EMOJIS['check']} Управление беседой")
    print(f"{EMOJIS['check']} Удаление сообщений (обязательно для мута)")
    print(f"{EMOJIS['check']} Исключение участников")
    print(f"{EMOJIS['light']} Убедитесь, что бот добавлен как администратор в чате!")
    
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_TOKEN на валидный токен группы VK!")
        print(f"""
    {EMOJIS['light']} Как получить токен:
    1. Создайте группу ВК или используйте существующую
    2. Перейдите в Управление -> Работа с API
    3. Создайте ключ с правами:
       {EMOJIS['check']} messages
       {EMOJIS['check']} manage_chat
       {EMOJIS['check']} photos
    4. Скопируйте токен и вставьте в код
        """)
    elif GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_ID на ID вашей группы (только цифры)!")
        print(f"{EMOJIS['light']} ID группы можно найти в ссылке: vk.com/public123456 -> 123456")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Бот остановлен пользователем")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Критическая ошибка: {e}")
