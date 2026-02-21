import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import sqlite3
import datetime
import time
import json
import re
from typing import Dict, List, Optional, Tuple, Any
import threading
import os

# ========== КОНФИГУРАЦИЯ ==========
GROUP_TOKEN = "vk1.a.o_e86tU572NCbaSCKfBUOWk8kV-Ch99M2d0B-5Hp6d4-08M3AzqmxTdw5DNhjNvapQ4Aro1U6yatm2U2AiUG_A4IogNInCEjMmK05SMyB7wxZjgDgVG7XfioPR6vmF2u0kDZZeeueUi24CapZlC8-lO65mwcOpIxg_JBiyrjzB7S96RDvxl3SE0yfDY15BjqRbGKg2qRZGHko0NsZAuZ4g"
GROUP_ID = "235560929"

# ========== ЭМОЦИИ И СМАЙЛИКИ ==========
EMOJIS = {
    "robot": "🤖", "crown": "👑", "gear": "⚙️", "chart": "📊", "warning": "⚠️",
    "no_entry": "⛔", "mute": "🔇", "kick": "👢", "rules": "📜", "online": "🟢",
    "offline": "🔴", "sleep": "😴", "welcome": "👋", "role": "🎭", "profile": "👤",
    "help": "❓", "exit": "🚪", "check": "✅", "cross": "❌", "clock": "⏰",
    "calendar": "📅", "pen": "📝", "police": "👮", "user": "👤", "violator": "👤💢",
    "ban_hammer": "🔨", "fire": "🔥", "star": "⭐", "light": "💡", "link": "🔗",
    "lock": "🔒", "unlock": "🔓", "bell": "🔔", "mega": "📣", "scroll": "📃",
    "book": "📖", "shield": "🛡️", "gavel": "⚖️", "handcuffs": "🔗", "key": "🔑",
    "door": "🚪", "green_circle": "🟢", "red_circle": "🔴", "yellow_circle": "🟡",
    "blue_circle": "🔵", "purple_circle": "🟣", "thinking": "🤔", "cool": "😎",
    "smile": "😊", "sad": "😢", "angry": "😠", "party": "🎉", "confetti": "🎊",
    "trophy": "🏆", "medal": "🎖️", "flag": "🎌", "info": "ℹ️", "poll": "📊",
    "vote": "🗳️", "search": "🔍", "message": "💬", "users": "👥", "stats": "📈",
    "up": "⬆️", "down": "⬇️", "level": "📊", "priority": "⚡", "list": "📋",
    "cmd": "⌨️", "admin_cmd": "👑", "user_cmd": "👤"
}

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        if os.path.exists('avrora_bot.db'):
            print(f"{EMOJIS['gear']} Загружаем существующую базу данных...")
        
        self.conn = sqlite3.connect('avrora_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_default_roles()
    
    def create_tables(self):
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_message TEXT DEFAULT 'Добро пожаловать в чат!',
                rules_text TEXT DEFAULT 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
                max_warns INTEGER DEFAULT 3,
                ban_duration INTEGER DEFAULT 10,
                bot_added_message_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                role_name TEXT,
                priority INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, role_name)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER,
                chat_id INTEGER,
                role_name TEXT,
                assigned_by INTEGER,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id, role_name)
            )
        ''')
        
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
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                creator_id INTEGER,
                question TEXT,
                options TEXT,
                votes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        self.conn.commit()
        print(f"{EMOJIS['check']} База данных инициализирована")
    
    def init_default_roles(self):
        self.default_roles = {
            'Генеральный Директор': 100,
            'Директор': 98,
            'Заместитель Директора': 97,
            'Администратор Бота': 95,
            'Управляющий': 85,
            'Заместитель Управляющего': 83,
            'Наставник': 81,
            'Руководитель Отдела': 80,
            'Администратор': 60,
            'Модератор': 40,
            'Куратор Практикантов': 30,
            'FD SPONSOR': 20,
            'SPONSOR': 19,
            'Дизайнер': 10,
            'Агент': 0
        }
    
    def create_custom_role(self, chat_id: int, role_name: str, priority: int, created_by: int) -> bool:
        try:
            self.cursor.execute(
                "SELECT id FROM custom_roles WHERE chat_id = ? AND role_name = ?",
                (chat_id, role_name)
            )
            if self.cursor.fetchone():
                return False
            
            self.cursor.execute(
                "INSERT INTO custom_roles (chat_id, role_name, priority, created_by) VALUES (?, ?, ?, ?)",
                (chat_id, role_name, priority, created_by)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка создания роли: {e}")
            return False
    
    def delete_custom_role(self, chat_id: int, role_name: str) -> bool:
        try:
            self.cursor.execute(
                "DELETE FROM custom_roles WHERE chat_id = ? AND role_name = ?",
                (chat_id, role_name)
            )
            self.cursor.execute(
                "DELETE FROM user_roles WHERE chat_id = ? AND role_name = ?",
                (chat_id, role_name)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка удаления роли: {e}")
            return False
    
    def update_custom_role(self, chat_id: int, old_name: str, new_name: str, new_priority: int) -> bool:
        try:
            self.cursor.execute(
                "UPDATE custom_roles SET role_name = ?, priority = ? WHERE chat_id = ? AND role_name = ?",
                (new_name, new_priority, chat_id, old_name)
            )
            self.cursor.execute(
                "UPDATE user_roles SET role_name = ? WHERE chat_id = ? AND role_name = ?",
                (new_name, chat_id, old_name)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка обновления роли: {e}")
            return False
    
    def get_all_roles_with_priority(self, chat_id: int) -> Dict[str, int]:
        roles = self.default_roles.copy()
        self.cursor.execute(
            "SELECT role_name, priority FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_roles = self.cursor.fetchall()
        for role_name, priority in custom_roles:
            roles[role_name] = priority
        return dict(sorted(roles.items(), key=lambda x: x[1], reverse=True))
    
    def assign_role_to_user(self, user_id: int, chat_id: int, role_name: str, assigned_by: int) -> bool:
        try:
            all_roles = self.get_all_roles_with_priority(chat_id)
            if role_name not in all_roles:
                return False
            self.cursor.execute(
                "DELETE FROM user_roles WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            self.cursor.execute(
                "INSERT INTO user_roles (user_id, chat_id, role_name, assigned_by) VALUES (?, ?, ?, ?)",
                (user_id, chat_id, role_name, assigned_by)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка назначения роли: {e}")
            return False
    
    def remove_user_role(self, user_id: int, chat_id: int) -> bool:
        try:
            self.cursor.execute(
                "DELETE FROM user_roles WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка снятия роли: {e}")
            return False
    
    def get_user_role(self, user_id: int, chat_id: int) -> Optional[Tuple[str, int]]:
        self.cursor.execute(
            "SELECT role_name FROM user_roles WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        result = self.cursor.fetchone()
        if result:
            role_name = result[0]
            all_roles = self.get_all_roles_with_priority(chat_id)
            priority = all_roles.get(role_name, 0)
            return (role_name, priority)
        return None
    
    def get_all_user_roles(self, chat_id: int) -> List[Tuple[int, str, int]]:
        self.cursor.execute(
            "SELECT user_id, role_name FROM user_roles WHERE chat_id = ?",
            (chat_id,)
        )
        results = self.cursor.fetchall()
        all_roles = self.get_all_roles_with_priority(chat_id)
        user_roles = []
        for user_id, role_name in results:
            priority = all_roles.get(role_name, 0)
            user_roles.append((user_id, role_name, priority))
        return sorted(user_roles, key=lambda x: x[2], reverse=True)
    
    def get_user_priority(self, user_id: int, chat_id: int, is_admin: bool = False) -> int:
        if is_admin:
            return 90
        user_role = self.get_user_role(user_id, chat_id)
        return user_role[1] if user_role else 0
    
    def can_manage_role(self, admin_id: int, target_priority: int, chat_id: int, is_admin: bool = False) -> bool:
        admin_priority = self.get_user_priority(admin_id, chat_id, is_admin)
        return admin_priority > target_priority
    
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
        else:
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
            self.update_user(user_id, chat_id, warns=user['warns'] - 1)
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
        
        default_settings = {
            'chat_id': chat_id,
            'welcome_message': 'Добро пожаловать в чат!',
            'rules_text': 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
            'max_warns': 3,
            'ban_duration': 10,
            'bot_added_message_sent': 0
        }
        self.cursor.execute(
            "INSERT INTO chat_settings (chat_id, welcome_message, rules_text, max_warns, ban_duration, bot_added_message_sent) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, default_settings['welcome_message'], default_settings['rules_text'], 
             default_settings['max_warns'], default_settings['ban_duration'], default_settings['bot_added_message_sent'])
        )
        self.conn.commit()
        return self.get_chat_settings(chat_id)
    
    def update_chat_settings(self, chat_id: int, **kwargs):
        self.get_chat_settings(chat_id)
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [chat_id]
        self.cursor.execute(
            f"UPDATE chat_settings SET {set_clause} WHERE chat_id = ?",
            values
        )
        self.conn.commit()
        return True
    
    def set_welcome_message(self, chat_id: int, welcome_message: str):
        return self.update_chat_settings(chat_id, welcome_message=welcome_message)
    
    def get_welcome_message(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        return settings.get('welcome_message', 'Добро пожаловать в чат!')
    
    def set_rules(self, chat_id: int, rules_text: str):
        return self.update_chat_settings(chat_id, rules_text=rules_text)
    
    def get_rules(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        return settings.get('rules_text', 'Правила еще не установлены. Администраторы могут установить их командой /createpravila')
    
    def set_bot_added_message_sent(self, chat_id: int, sent: int = 1):
        return self.update_chat_settings(chat_id, bot_added_message_sent=sent)
    
    def get_chat_stats(self, chat_id: int) -> Dict:
        self.cursor.execute(
            "SELECT COUNT(*) as total_users, SUM(CASE WHEN warns > 0 THEN 1 ELSE 0 END) as warned_users, "
            "SUM(CASE WHEN mute_until > ? THEN 1 ELSE 0 END) as muted_users, "
            "SUM(CASE WHEN ban_until > ? THEN 1 ELSE 0 END) as banned_users "
            "FROM users WHERE chat_id = ?",
            (int(time.time()), int(time.time()), chat_id)
        )
        row = self.cursor.fetchone()
        stats = dict(zip(['total_users', 'warned_users', 'muted_users', 'banned_users'], row)) if row else {}
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
        self.cursor.execute(
            "SELECT COUNT(*) FROM warns_history WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        total_warns = self.cursor.fetchone()[0]
        user_role = self.get_user_role(user_id, chat_id)
        return {
            'user_id': user_id,
            'warns': user['warns'],
            'total_warns': total_warns,
            'muted': user['mute_until'] > time.time(),
            'banned': user['ban_until'] > time.time(),
            'kicked': user.get('kicked', 0),
            'role': user_role[0] if user_role else 'member',
            'join_date': user['join_date']
        }
    
    def create_poll(self, chat_id: int, creator_id: int, question: str, options: List[str]) -> int:
        self.cursor.execute(
            "INSERT INTO polls (chat_id, creator_id, question, options, votes) VALUES (?, ?, ?, ?, ?)",
            (chat_id, creator_id, question, json.dumps(options), json.dumps({}))
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_poll(self, poll_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM polls WHERE poll_id = ?", (poll_id,))
        row = self.cursor.fetchone()
        if row:
            columns = [desc[0] for desc in self.cursor.description]
            result = dict(zip(columns, row))
            result['options'] = json.loads(result['options'])
            result['votes'] = json.loads(result['votes'])
            return result
        return None
    
    def vote_poll(self, poll_id: int, user_id: int, option_index: int) -> bool:
        poll = self.get_poll(poll_id)
        if not poll or not poll['is_active']:
            return False
        votes = poll['votes']
        votes[str(user_id)] = option_index
        self.cursor.execute(
            "UPDATE polls SET votes = ? WHERE poll_id = ?",
            (json.dumps(votes), poll_id)
        )
        self.conn.commit()
        return True
    
    def get_poll_results(self, poll_id: int) -> Dict:
        poll = self.get_poll(poll_id)
        if not poll:
            return {}
        results = {i: 0 for i in range(len(poll['options']))}
        for vote in poll['votes'].values():
            results[vote] += 1
        return {
            'question': poll['question'],
            'options': poll['options'],
            'results': results,
            'total_votes': len(poll['votes']),
            'creator_id': poll['creator_id'],
            'created_at': poll['created_at']
        }
    
    def get_active_polls(self, chat_id: int) -> List[Dict]:
        self.cursor.execute(
            "SELECT poll_id, question, creator_id FROM polls WHERE chat_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (chat_id,)
        )
        return [{'poll_id': row[0], 'question': row[1], 'creator_id': row[2]} for row in self.cursor.fetchall()]

# ========== ВК БОТ ==========
class VKAvroraBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=GROUP_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, GROUP_ID)
        self.db = Database()
        self.chat_admins_cache = {}
        self.cache_timeout = 300
        self.processed_events = set()
        print(f"{EMOJIS['robot']} AVRORA Manager Bot запущен!")
    
    def send_message(self, chat_id: int, message: str, **kwargs):
        try:
            self.vk.messages.send(
                peer_id=2000000000 + chat_id,
                message=message,
                random_id=get_random_id(),
                **kwargs
            )
            print(f"Сообщение отправлено в чат {chat_id}: {message[:50]}...")
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка отправки: {e}")
    
    def get_chat_admins(self, chat_id: int) -> List[int]:
        cache_key = f"admins_{chat_id}"
        if cache_key in self.chat_admins_cache:
            cached_time, admins = self.chat_admins_cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return admins
        try:
            chat_info = self.vk.messages.getConversationMembers(peer_id=2000000000 + chat_id)
            admins = [m['member_id'] for m in chat_info.get('items', []) 
                     if m.get('is_admin') and m['member_id'] > 0]
            self.chat_admins_cache[cache_key] = (time.time(), admins)
            return admins
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка получения админов: {e}")
            return []
    
    def is_chat_admin(self, user_id: int, chat_id: int) -> bool:
        return user_id in self.get_chat_admins(chat_id)
    
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
        except:
            pass
        return {'first_name': 'Пользователь', 'last_name': '', 'full_name': 'Пользователь'}
    
    def extract_mention_or_id(self, text: str, reply_message: Optional[Dict] = None) -> Optional[int]:
        match = re.search(r'\[id(\d+)\|', text) or re.search(r'@id(\d+)', text)
        if match:
            return int(match.group(1))
        if reply_message and 'from_id' in reply_message:
            return reply_message['from_id']
        match = re.search(r'\b(\d{5,})\b', text)
        return int(match.group(1)) if match else None
    
    def parse_duration(self, duration_str: str) -> Tuple[int, str]:
        duration_str = duration_str.strip().lower()
        if not duration_str or duration_str in ['∞', 'inf', 'бессрочно', 'навсегда']:
            return 0, "бессрочно"
        match = re.match(r'(\d+)\s*([dдhчmмsс]?)', duration_str)
        if not match:
            return 0, "неверный формат"
        number, unit = int(match.group(1)), match.group(2)
        if unit in ['d', 'д']:
            return number * 86400, f"{number} дней"
        if unit in ['h', 'ч']:
            return number * 3600, f"{number} часов"
        if unit in ['m', 'м']:
            return number * 60, f"{number} минут"
        if unit in ['s', 'с']:
            return number, f"{number} секунд"
        return number * 86400, f"{number} дней"
    
    def format_time(self, timestamp: int) -> str:
        return "бессрочно" if timestamp == 0 else datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")
    
    # КОМАНДЫ ДЛЯ РОЛЕЙ
    def handle_new_role(self, user_id: int, chat_id: int, args: str):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.send_message(chat_id, f"{EMOJIS['role']} /newrole [приоритет] [название]\nПриоритет: 0-100")
            return
        try:
            priority = int(parts[0])
            if priority < 0 or priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет от 0 до 100!")
                return
            role_name = parts[1].strip()
            if self.db.create_custom_role(chat_id, role_name, priority, user_id):
                self.send_message(chat_id, f"{EMOJIS['check']} Роль {role_name} (приоритет {priority}) создана!")
            else:
                self.send_message(chat_id, f"{EMOJIS['cross']} Роль уже существует!")
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
    
    def handle_delete_role(self, user_id: int, chat_id: int, args: str):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        role_name = args.strip()
        if not role_name:
            self.send_message(chat_id, f"{EMOJIS['role']} /deleterole [название]")
            return
        if self.db.delete_custom_role(chat_id, role_name):
            self.send_message(chat_id, f"{EMOJIS['check']} Роль {role_name} удалена!")
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль не найдена!")
    
    def handle_set_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        target_id = None
        role_name = None
        if reply_message:
            target_id = reply_message['from_id']
            role_name = args.strip()
        else:
            parts = args.strip().split(maxsplit=1)
            if len(parts) >= 2:
                target_id = self.extract_mention_or_id(parts[0])
                role_name = parts[1].strip()
        if not target_id or not role_name:
            self.send_message(chat_id, f"{EMOJIS['role']} /setrole @user [роль] или ответом на сообщение")
            return
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        if role_name not in all_roles:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль не найдена! /roles")
            return
        if self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя назначить роль админу!")
            return
        if self.db.assign_role_to_user(target_id, chat_id, role_name, user_id):
            target_info = self.get_user_info(target_id)
            self.send_message(chat_id, f"{EMOJIS['check']} [id{target_id}|{target_info['full_name']}] получил роль {role_name}")
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка!")
    
    def handle_remove_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        target_id = reply_message['from_id'] if reply_message else self.extract_mention_or_id(args.strip())
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['role']} /removerole @user или ответом")
            return
        if self.db.remove_user_role(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            self.send_message(chat_id, f"{EMOJIS['check']} Роль снята с [id{target_id}|{target_info['full_name']}]")
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} У пользователя нет роли!")
    
    def handle_roles_list(self, user_id: int, chat_id: int):
        roles = self.db.get_all_roles_with_priority(chat_id)
        if not roles:
            self.send_message(chat_id, f"{EMOJIS['role']} Ролей нет. /newrole для создания")
            return
        text = f"{EMOJIS['role']} Роли (приоритет):\n"
        for name, priority in list(roles.items())[:20]:
            text += f"• {name} ({priority})\n"
        self.send_message(chat_id, text)
    
    def handle_my_role(self, user_id: int, chat_id: int):
        user_role = self.db.get_user_role(user_id, chat_id)
        is_admin = self.is_chat_admin(user_id, chat_id)
        user_info = self.get_user_info(user_id)
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор (90)"
        elif user_role:
            role_text = f"{EMOJIS['role']} {user_role[0]} ({user_role[1]})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (0)"
        self.send_message(chat_id, f"{EMOJIS['profile']} {user_info['full_name']}\n{role_text}")
    
    # ОСНОВНЫЕ КОМАНДЫ
    def handle_welcome(self, user_id: int, chat_id: int, args: str):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        if not args.strip():
            current = self.db.get_welcome_message(chat_id)
            self.send_message(chat_id, f"{EMOJIS['welcome']} Текущее: {current}\n/приветствие [текст]")
            return
        self.db.set_welcome_message(chat_id, args.strip())
        self.send_message(chat_id, f"{EMOJIS['check']} Приветствие обновлено!")
    
    def handle_new_chat_member(self, chat_id: int, user_id: int):
        user_data = self.db.get_user(user_id, chat_id)
        if user_data and user_data.get('kicked', 0) == 1 and user_data['ban_until'] > time.time():
            try:
                self.vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
            except:
                pass
            return
        self.db.add_user(user_id, chat_id)
        welcome = self.db.get_welcome_message(chat_id)
        user_info = self.get_user_info(user_id)
        self.send_message(chat_id, f"{EMOJIS['welcome']} Привет, {user_info['full_name']}!\n{welcome}\n/CMD - список команд")
    
    def handle_bot_added(self, chat_id: int, user_id: int):
        settings = self.db.get_chat_settings(chat_id)
        if settings.get('bot_added_message_sent', 0) == 1:
            return
        self.db.set_bot_added_message_sent(chat_id, 1)
        self.send_message(chat_id, f"{EMOJIS['robot']} Спасибо что добавили меня в чат! 🤖\nВыдайте мне права администратора для полной функциональности.\n\n/CMD - список всех команд")
    
    def handle_cmd(self, user_id: int, chat_id: int, args: str = ""):
        """Обработчик команды /cmd"""
        is_admin = self.is_chat_admin(user_id, chat_id)
        if is_admin:
            text = f"""{EMOJIS['cmd']} АДМИН КОМАНДЫ:
/newrole [приоритет] [название] - создать роль
/deleterole [название] - удалить роль
/setrole @user [роль] - назначить роль
/removerole @user - снять роль
/roles - список ролей
/myrole - моя роль
/userrole @user - роль пользователя
/mute @user время - мут
/warn @user - предупреждение
/kick @user - кик
/ban @user время - бан
/размут @user - снять мут
/разбан @user - снять бан
/снятьварн @user - снять варн
/createpravila [текст] - правила
/приветствие [текст] - приветствие

{EMOJIS['user']} ОБЩИЕ КОМАНДЫ:
/инфо [@user] - инфо
/опрос вопрос | вар1 | вар2 - опрос
/опросрезультаты [номер] - результаты
/профиль - профиль
/онлайн - кто онлайн
/правила - правила
/q - выйти
/CMD - этот список"""
        else:
            text = f"""{EMOJIS['cmd']} КОМАНДЫ:
/инфо [@user] - информация
/опрос вопрос | вар1 | вар2 - опрос
/опросрезультаты [номер] - результаты
/профиль - профиль
/myrole - моя роль
/userrole @user - роль пользователя
/онлайн - кто онлайн
/правила - правила
/roles - список ролей
/q - выйти
/CMD - этот список"""
        
        self.send_message(chat_id, text)
        print(f"Команда /cmd выполнена для пользователя {user_id} в чате {chat_id}")
    
    def handle_mute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        target_id = reply_message['from_id'] if reply_message else self.extract_mention_or_id(args)
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['mute']} /mute @user время")
            return
        if target_id == user_id or self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя!")
            return
        parts = args.split()
        if len(parts) < 1:
            self.send_message(chat_id, f"{EMOJIS['cross']} Укажите время")
            return
        seconds, text = self.parse_duration(parts[0])
        if seconds == 0 and text == "неверный формат":
            self.send_message(chat_id, f"{EMOJIS['cross']} Неверный формат времени")
            return
        mute_until = 0 if seconds == 0 else int(time.time()) + seconds
        self.db.update_user(target_id, chat_id, mute_until=mute_until)
        target_info = self.get_user_info(target_id)
        self.send_message(chat_id, f"{EMOJIS['mute']} {target_info['full_name']} замучен на {text}")
    
    def handle_ban(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        target_id = reply_message['from_id'] if reply_message else self.extract_mention_or_id(args)
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['no_entry']} /ban @user время")
            return
        if target_id == user_id or self.is_chat_admin(target_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя!")
            return
        parts = args.split()
        if len(parts) < 1:
            self.send_message(chat_id, f"{EMOJIS['cross']} Укажите время")
            return
        seconds, text = self.parse_duration(parts[0])
        if seconds == 0 and text == "неверный формат":
            self.send_message(chat_id, f"{EMOJIS['cross']} Неверный формат времени")
            return
        ban_until = 0 if seconds == 0 else int(time.time()) + seconds
        self.db.update_user(target_id, chat_id, ban_until=ban_until, kicked=1)
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id)
        except:
            pass
        target_info = self.get_user_info(target_id)
        self.send_message(chat_id, f"{EMOJIS['no_entry']} {target_info['full_name']} забанен на {text}")
    
    def handle_info(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        target_id = reply_message['from_id'] if reply_message else self.extract_mention_or_id(args) or user_id
        user_info = self.get_user_info(target_id)
        stats = self.db.get_user_stats(target_id, chat_id)
        is_admin = self.is_chat_admin(target_id, chat_id)
        role_text = f"{EMOJIS['crown']} Админ" if is_admin else f"{EMOJIS['user']} Участник"
        self.send_message(chat_id, f"{EMOJIS['info']} {user_info['full_name']}\nID: {target_id}\n{role_text}\nВарнов: {stats.get('warns', 0)}")
    
    def handle_profile(self, user_id: int, chat_id: int):
        self.handle_info(user_id, chat_id, "", None)
    
    def handle_rules(self, user_id: int, chat_id: int):
        rules = self.db.get_rules(chat_id)
        self.send_message(chat_id, f"{EMOJIS['rules']} {rules}")
    
    def handle_create_rules(self, user_id: int, chat_id: int, args: str):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Только для админов!")
            return
        if not args.strip():
            self.send_message(chat_id, f"{EMOJIS['rules']} /createpravila [текст]")
            return
        self.db.set_rules(chat_id, args.strip())
        self.send_message(chat_id, f"{EMOJIS['check']} Правила обновлены!")
    
    def handle_poll(self, user_id: int, chat_id: int, args: str):
        if not args.strip():
            self.send_message(chat_id, f"{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 ...")
            return
        parts = [p.strip() for p in args.split('|')]
        if len(parts) < 3:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужен вопрос и 2+ варианта")
            return
        question, options = parts[0], parts[1:]
        poll_id = self.db.create_poll(chat_id, user_id, question, options)
        text = f"{EMOJIS['poll']} Опрос #{poll_id}\n{question}\n"
        for i, opt in enumerate(options, 1):
            text += f"{i}. {opt}\n"
        text += "Голосуйте ответом с номером"
        self.send_message(chat_id, text)
    
    def handle_poll_results(self, user_id: int, chat_id: int, args: str):
        if not args.strip():
            polls = self.db.get_active_polls(chat_id)
            if not polls:
                self.send_message(chat_id, f"{EMOJIS['poll']} Нет опросов")
                return
            text = f"{EMOJIS['poll']} Опросы:\n"
            for p in polls:
                text += f"#{p['poll_id']}: {p['question'][:30]}...\n/опросрезультаты {p['poll_id']}\n"
            self.send_message(chat_id, text)
            return
        try:
            poll_id = int(args)
            results = self.db.get_poll_results(poll_id)
            if not results:
                self.send_message(chat_id, f"{EMOJIS['cross']} Опрос не найден")
                return
            text = f"{EMOJIS['poll']} Результаты #{poll_id}\n{results['question']}\n"
            for i, opt in enumerate(results['options']):
                votes = results['results'].get(i, 0)
                percent = (votes / results['total_votes'] * 100) if results['total_votes'] > 0 else 0
                text += f"{i+1}. {opt}: {votes} ({percent:.1f}%)\n"
            self.send_message(chat_id, text)
        except:
            self.send_message(chat_id, f"{EMOJIS['cross']} Неверный номер")
    
    def handle_poll_vote(self, user_id: int, chat_id: int, reply_message: Dict, vote_text: str):
        match = re.search(r'Опрос #(\d+)', reply_message.get('text', ''))
        if not match:
            return
        try:
            poll_id = int(match.group(1))
            option = int(vote_text) - 1
            if self.db.vote_poll(poll_id, user_id, option):
                self.send_message(chat_id, f"{EMOJIS['check']} [id{user_id}|Голос учтен]")
        except:
            pass
    
    def handle_online(self, user_id: int, chat_id: int):
        try:
            members = self.vk.messages.getConversationMembers(peer_id=2000000000 + chat_id, fields='online')
            online = [f"{EMOJIS['green_circle']} [id{m['member_id']}|{m.get('first_name', '')}]" 
                     for m in members.get('items', []) if m.get('online') and m['member_id'] > 0]
            self.send_message(chat_id, f"{EMOJIS['online']} Онлайн ({len(online)}):\n" + "\n".join(online[:20]))
        except:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка")
    
    def handle_self_kick(self, user_id: int, chat_id: int):
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
        except:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка")
    
    def check_punishments(self):
        while True:
            try:
                now = int(time.time())
                self.db.cursor.execute("UPDATE users SET mute_until=0 WHERE mute_until>0 AND mute_until<?", (now,))
                self.db.cursor.execute("UPDATE users SET ban_until=0, kicked=0 WHERE ban_until>0 AND ban_until<?", (now,))
                self.db.conn.commit()
            except:
                pass
            time.sleep(60)
    
    def process_message(self, event):
        try:
            msg = event.object.message
            chat_id, user_id, text = event.chat_id, msg['from_id'], msg.get('text', '').strip()
            print(f"Получено сообщение: '{text}' от {user_id} в чате {chat_id}")
            
            if not text:
                return
            
            event_id = f"{chat_id}_{msg.get('conversation_message_id')}"
            if event_id in self.processed_events:
                return
            self.processed_events.add(event_id)
            if len(self.processed_events) > 1000:
                self.processed_events.clear()
            
            user_data = self.db.get_user(user_id, chat_id)
            if user_data and user_data['ban_until'] > time.time():
                try:
                    self.vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
                except:
                    pass
                return
            
            if user_data and user_data['mute_until'] > time.time():
                try:
                    self.vk.messages.delete(
                        conversation_message_ids=[msg['conversation_message_id']], 
                        delete_for_all=1, 
                        peer_id=2000000000 + chat_id
                    )
                except:
                    pass
                return
            
            if text.startswith('/'):
                cmd = text.split()[0].lower()
                args = ' '.join(text.split()[1:]) if len(text.split()) > 1 else ""
                reply = msg.get('reply_message')
                
                print(f"Обрабатываю команду: {cmd}")
                
                handlers = {
                    '/newrole': self.handle_new_role,
                    '/deleterole': self.handle_delete_role,
                    '/setrole': lambda u, c, a: self.handle_set_role(u, c, a, reply),
                    '/removerole': lambda u, c, a: self.handle_remove_role(u, c, a, reply),
                    '/roles': self.handle_roles_list,
                    '/myrole': self.handle_my_role,
                    '/userrole': lambda u, c, a: self.handle_my_role(u, c) if not a else self.handle_info(u, c, a, reply),
                    '/приветствие': self.handle_welcome,
                    '/createpravila': self.handle_create_rules,
                    '/правила': self.handle_rules,
                    '/mute': lambda u, c, a: self.handle_mute(u, c, a, reply),
                    '/ban': lambda u, c, a: self.handle_ban(u, c, a, reply),
                    '/kick': lambda u, c, a: self.handle_ban(u, c, a, reply),
                    '/размут': lambda u, c, a: self.handle_mute(u, c, "0", reply),
                    '/разбан': lambda u, c, a: self.handle_ban(u, c, "0", reply),
                    '/инфо': lambda u, c, a: self.handle_info(u, c, a, reply),
                    '/профиль': self.handle_profile,
                    '/опрос': self.handle_poll,
                    '/опросрезультаты': self.handle_poll_results,
                    '/онлайн': self.handle_online,
                    '/q': self.handle_self_kick,
                    '/cmd': self.handle_cmd,
                    '/help': self.handle_cmd,
                    '/команды': self.handle_cmd,
                }
                
                if cmd in handlers:
                    print(f"Выполняю обработчик для {cmd}")
                    handlers[cmd](user_id, chat_id, args)
                else:
                    print(f"Неизвестная команда: {cmd}")
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. /CMD")
            
            elif reply and reply.get('from_id') == -int(GROUP_ID):
                self.handle_poll_vote(user_id, chat_id, reply, text)
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка в process_message: {e}")
    
    def run(self):
        threading.Thread(target=self.check_punishments, daemon=True).start()
        print(f"\n{EMOJIS['robot']} Бот запущен! /CMD - команды\n")
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                    self.process_message(event)
                elif event.type == VkBotEventType.CHAT_INVITE_USER:
                    if event.object.get('user_id') == -int(GROUP_ID):
                        user_id = event.object.get('from_id')
                        chat_id = event.chat_id
                        print(f"Бот добавлен в чат {chat_id} пользователем {user_id}")
                        self.handle_bot_added(chat_id, user_id)
            except Exception as e:
                print(f"{EMOJIS['cross']} Ошибка в главном цикле: {e}")

if __name__ == "__main__":
    print(f"{EMOJIS['robot']} = AVRORA Manager Bot =")
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE" or GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} Замените TOKEN и GROUP_ID!")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Бот остановлен")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Критическая ошибка: {e}")
