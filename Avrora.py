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
        self.send_message(chat_id, f"{EMOJIS['robot']} Спасибо! Выдайте мне права админа для работы.\n/CMD - команды")
    
    def handle_cmd(self, user_id: int, chat_id: int):
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
/admin - статистика

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
            if not text:
                return
            event_id = f"{chat_id}_{msg.get('conversation_message_id')}"
            if event_id in self.processed_events:
                return
            self.processed_events.add(event_id)
            if len(self.processed_events) > 1000:
                self.processed_events.clear()
            
            user_data = self.db.get_user(user_id, chat_id)
            if user_data and user_data['ban_until'] > 0:
                if user_data['ban_until'] == 0 or user_data['ban_until'] > time.time():
                    try:
                        self.vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
                    except:
                        pass
                    return
            
            if user_data and user_data['mute_until'] > 0:
                if user_data['mute_until'] == 0 or user_data['mute_until'] > time.time():
                    try:
                        self.vk.messages.delete(conversation_message_ids=[msg['conversation_message_id']], 
                                              delete_for_all=1, peer_id=2000000000 + chat_id)
                    except:
                        pass
                    return
            
            if text.startswith('/'):
                cmd = text.split()[0].lower()
                args = ' '.join(text.split()[1:]) if len(text.split()) > 1 else ""
                reply = msg.get('reply_message')
                
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
                    handlers[cmd](user_id, chat_id, args)
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. /CMD")
            
            elif reply and reply.get('from_id') == -int(GROUP_ID):
                self.handle_poll_vote(user_id, chat_id, reply, text)
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка: {e}")
    
    def run(self):
        threading.Thread(target=self.check_punishments, daemon=True).start()
        print(f"\n{EMOJIS['robot']} Бот запущен! /CMD - команды\n")
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                    self.process_message(event)
                elif event.type == VkBotEventType.CHAT_INVITE_USER:
                    if event.object.get('user_id') == -int(GROUP_ID):
                        self.handle_bot_added(event.chat_id, event.object.get('from_id'))
                elif event.type == VkBotEventType.MESSAGE_ALLOW:
                    if 'chat_id' in event.object:
                        self.handle_new_chat_member(event.object['chat_id'], event.object['user_id'])
            except Exception as e:
                print(f"{EMOJIS['cross']} Ошибка цикла: {e}")

if __name__ == "__main__":
    print(f"{EMOJIS['robot']} = AVRORA Manager Bot =")
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE" or GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} Замените TOKEN и GROUP_ID!")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Стоп")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Критическая ошибка: {e}")class Database:
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
        self.send_message(chat_id, f"{EMOJIS['robot']} Спасибо! Выдайте мне права админа для работы.\n/CMD - команды")
    
    def handle_cmd(self, user_id: int, chat_id: int):
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
/admin - статистика

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
            if not text:
                return
            event_id = f"{chat_id}_{msg.get('conversation_message_id')}"
            if event_id in self.processed_events:
                return
            self.processed_events.add(event_id)
            if len(self.processed_events) > 1000:
                self.processed_events.clear()
            
            user_data = self.db.get_user(user_id, chat_id)
            if user_data and user_data['ban_until'] > 0:
                if user_data['ban_until'] == 0 or user_data['ban_until'] > time.time():
                    try:
                        self.vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
                    except:
                        pass
                    return
            
            if user_data and user_data['mute_until'] > 0:
                if user_data['mute_until'] == 0 or user_data['mute_until'] > time.time():
                    try:
                        self.vk.messages.delete(conversation_message_ids=[msg['conversation_message_id']], 
                                              delete_for_all=1, peer_id=2000000000 + chat_id)
                    except:
                        pass
                    return
            
            if text.startswith('/'):
                cmd = text.split()[0].lower()
                args = ' '.join(text.split()[1:]) if len(text.split()) > 1 else ""
                reply = msg.get('reply_message')
                
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
                    handlers[cmd](user_id, chat_id, args)
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. /CMD")
            
            elif reply and reply.get('from_id') == -int(GROUP_ID):
                self.handle_poll_vote(user_id, chat_id, reply, text)
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка: {e}")
    
    def run(self):
        threading.Thread(target=self.check_punishments, daemon=True).start()
        print(f"\n{EMOJIS['robot']} Бот запущен! /CMD - команды\n")
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                    self.process_message(event)
                elif event.type == VkBotEventType.CHAT_INVITE_USER:
                    if event.object.get('user_id') == -int(GROUP_ID):
                        self.handle_bot_added(event.chat_id, event.object.get('from_id'))
                elif event.type == VkBotEventType.MESSAGE_ALLOW:
                    if 'chat_id' in event.object:
                        self.handle_new_chat_member(event.object['chat_id'], event.object['user_id'])
            except Exception as e:
                print(f"{EMOJIS['cross']} Ошибка цикла: {e}")

if __name__ == "__main__":
    print(f"{EMOJIS['robot']} = AVRORA Manager Bot =")
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE" or GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} Замените TOKEN и GROUP_ID!")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Стоп")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Ошибка: {e}")# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        if os.path.exists('avrora_bot.db'):
            print(f"{EMOJIS['gear']} Загружаем существующую базу данных...")
        
        self.conn = sqlite3.connect('avrora_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_default_roles()
    
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
                rules_text TEXT DEFAULT 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
                max_warns INTEGER DEFAULT 3,
                ban_duration INTEGER DEFAULT 10,
                bot_added_message_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица ролей (кастомные роли для чата)
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
        
        # Таблица назначенных ролей пользователям
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
        
        # Таблица опросов
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
        """Инициализация стандартных ролей"""
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
    
    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С РОЛЯМИ ==========
    
    def create_custom_role(self, chat_id: int, role_name: str, priority: int, created_by: int) -> bool:
        """Создание новой кастомной роли в чате"""
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
        """Удаление кастомной роли"""
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
        """Обновление кастомной роли"""
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
        """Получение всех ролей чата (стандартные + кастомные) с приоритетами"""
        roles = self.default_roles.copy()
        
        self.cursor.execute(
            "SELECT role_name, priority FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_roles = self.cursor.fetchall()
        for role_name, priority in custom_roles:
            roles[role_name] = priority
        
        sorted_roles = dict(sorted(roles.items(), key=lambda x: x[1], reverse=True))
        return sorted_roles
    
    def assign_role_to_user(self, user_id: int, chat_id: int, role_name: str, assigned_by: int) -> bool:
        """Назначение роли пользователю"""
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
        """Снятие роли с пользователя"""
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
        """Получение роли пользователя и её приоритета"""
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
        """Получение всех пользователей с ролями в чате"""
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
        
        user_roles.sort(key=lambda x: x[2], reverse=True)
        return user_roles
    
    def get_user_priority(self, user_id: int, chat_id: int, is_admin: bool = False) -> int:
        """Получение приоритета пользователя"""
        if is_admin:
            return 90
        
        user_role = self.get_user_role(user_id, chat_id)
        if user_role:
            return user_role[1]
        
        return 0
    
    def can_manage_role(self, admin_id: int, target_priority: int, chat_id: int, is_admin: bool = False) -> bool:
        """Проверка, может ли администратор управлять ролью с указанным приоритетом"""
        admin_priority = self.get_user_priority(admin_id, chat_id, is_admin)
        return admin_priority > target_priority
    
    # ========== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========
    
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
            settings = dict(zip(columns, row))
            if 'welcome_message' not in settings:
                settings['welcome_message'] = 'Добро пожаловать в чат!'
            if 'rules_text' not in settings:
                settings['rules_text'] = 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
            if 'max_warns' not in settings:
                settings['max_warns'] = 3
            if 'ban_duration' not in settings:
                settings['ban_duration'] = 10
            if 'bot_added_message_sent' not in settings:
                settings['bot_added_message_sent'] = 0
            return settings
        
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
            (chat_id, 
             default_settings['welcome_message'],
             default_settings['rules_text'],
             default_settings['max_warns'],
             default_settings['ban_duration'],
             default_settings['bot_added_message_sent'])
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
    
    def set_rules(self, chat_id: int, rules_text: str):
        return self.update_chat_settings(chat_id, rules_text=rules_text)
    
    def get_rules(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        if settings and 'rules_text' in settings:
            return settings['rules_text']
        return 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
    
    def set_welcome_message(self, chat_id: int, welcome_message: str):
        return self.update_chat_settings(chat_id, welcome_message=welcome_message)
    
    def get_welcome_message(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        if settings and 'welcome_message' in settings:
            return settings['welcome_message']
        return 'Добро пожаловать в чат!'
    
    def set_bot_added_message_sent(self, chat_id: int, sent: int = 1):
        return self.update_chat_settings(chat_id, bot_added_message_sent=sent)
    
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
        role_name = user_role[0] if user_role else 'member'
        
        return {
            'user_id': user_id,
            'warns': user['warns'],
            'total_warns': total_warns,
            'muted': user['mute_until'] > time.time(),
            'banned': user['ban_until'] > time.time(),
            'kicked': user.get('kicked', 0),
            'role': role_name,
            'join_date': user['join_date']
        }
    
    # Методы для опросов
    def create_poll(self, chat_id: int, creator_id: int, question: str, options: List[str]) -> int:
        options_json = json.dumps(options, ensure_ascii=False)
        votes_json = json.dumps({}, ensure_ascii=False)
        
        self.cursor.execute(
            "INSERT INTO polls (chat_id, creator_id, question, options, votes) VALUES (?, ?, ?, ?, ?)",
            (chat_id, creator_id, question, options_json, votes_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_poll(self, poll_id: int) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT * FROM polls WHERE poll_id = ?",
            (poll_id,)
        )
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
        if str(user_id) in votes:
            del votes[str(user_id)]
        
        votes[str(user_id)] = option_index
        votes_json = json.dumps(votes, ensure_ascii=False)
        
        self.cursor.execute(
            "UPDATE polls SET votes = ? WHERE poll_id = ?",
            (votes_json, poll_id)
        )
        self.conn.commit()
        return True
    
    def get_poll_results(self, poll_id: int) -> Dict:
        poll = self.get_poll(poll_id)
        if not poll:
            return {}
        
        votes = poll['votes']
        options = poll['options']
        
        results = {i: 0 for i in range(len(options))}
        for vote in votes.values():
            if vote in results:
                results[vote] += 1
        
        total_votes = sum(results.values())
        
        return {
            'question': poll['question'],
            'options': options,
            'results': results,
            'total_votes': total_votes,
            'creator_id': poll['creator_id'],
            'created_at': poll['created_at']
        }
    
    def get_active_polls(self, chat_id: int) -> List[Dict]:
        self.cursor.execute(
            "SELECT poll_id, question, creator_id FROM polls WHERE chat_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (chat_id,)
        )
        rows = self.cursor.fetchall()
        return [{'poll_id': row[0], 'question': row[1], 'creator_id': row[2]} for row in rows]

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
        print(f"{EMOJIS['crown']} Админы определяются автоматически по правам в чате")
        print(f"{EMOJIS['role']} Новая система ролей с приоритетами активна!")
        print(f"{EMOJIS['cmd']} Команда /CMD - список всех команд")
    
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
        match = re.search(r'\[id(\d+)\|', text)
        if match:
            return int(match.group(1))
        
        match = re.search(r'@id(\d+)', text)
        if match:
            return int(match.group(1))
        
        if reply_message and 'from_id' in reply_message:
            return reply_message['from_id']
        
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
    
    # ========== КОМАНДЫ ДЛЯ РОЛЕЙ ==========
    
    def handle_new_role(self, user_id: int, chat_id: int, args: str):
        """Команда /newrole [приоритет] [название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование: /newrole [приоритет] [название]

{EMOJIS['priority']} Приоритет: 0 (низший) - 100 (высший)

{EMOJIS['light']} Примеры:
/newrole 50 Менеджер
/newrole 25 Помощник
/newrole 75 Старший Модератор""")
            return
        
        try:
            priority = int(parts[0])
            if priority < 0 or priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть от 0 до 100!")
                return
            
            role_name = parts[1].strip()
            if len(role_name) > 50:
                self.send_message(chat_id, f"{EMOJIS['cross']} Название роли слишком длинное (макс. 50 символов)")
                return
            
            if self.db.create_custom_role(chat_id, role_name, priority, user_id):
                admin_info = self.get_user_info(user_id)
                message = f"""{EMOJIS['check']} Роль успешно создана!

{EMOJIS['role']} Название: {role_name}
{EMOJIS['priority']} Приоритет: {priority}
{EMOJIS['police']} Создал: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь вы можете назначать эту роль:
/setrole @user {role_name}

{EMOJIS['list']} Посмотреть все роли: /roles"""
                self.send_message(chat_id, message)
            else:
                self.send_message(chat_id, f"{EMOJIS['cross']} Роль с таким названием уже существует!")
                
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
    
    def handle_delete_role(self, user_id: int, chat_id: int, args: str):
        """Команда /deleterole [название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        role_name = args.strip()
        if not role_name:
            self.send_message(chat_id, f"{EMOJIS['role']} Использование: /deleterole [название]\n\n{EMOJIS['light']} Пример: /deleterole Менеджер")
            return
        
        if self.db.delete_custom_role(chat_id, role_name):
            admin_info = self.get_user_info(user_id)
            message = f"""{EMOJIS['check']} Роль удалена!

{EMOJIS['role']} Название: {role_name}
{EMOJIS['police']} Удалил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['warning']} Все пользователи лишились этой роли."""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{role_name}' не найдена!")
    
    def handle_update_role(self, user_id: int, chat_id: int, args: str):
        """Команда /updaterole [старое название] [новый приоритет] [новое название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=2)
        if len(parts) < 3:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование: /updaterole [старое название] [новый приоритет] [новое название]

{EMOJIS['light']} Пример: /updaterole Менеджер 55 Старший Менеджер""")
            return
        
        old_name = parts[0].strip()
        
        try:
            new_priority = int(parts[1])
            if new_priority < 0 or new_priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть от 0 до 100!")
                return
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
            return
        
        new_name = parts[2].strip()
        
        if self.db.update_custom_role(chat_id, old_name, new_name, new_priority):
            admin_info = self.get_user_info(user_id)
            message = f"""{EMOJIS['check']} Роль обновлена!

{EMOJIS['role']} Было: {old_name}
{EMOJIS['role']} Стало: {new_name}
{EMOJIS['priority']} Новый приоритет: {new_priority}
{EMOJIS['police']} Обновил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['list']} Посмотреть все роли: /roles"""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{old_name}' не найдена!")
    
    def handle_set_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /setrole [@user] [роль] - назначение роли пользователю"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
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
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /setrole @user [роль]
2. /setrole [роль] (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/setrole @durov Администратор
/setrole Модератор (ответ на сообщение)""")
            return
        
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        if role_name not in all_roles:
            available_roles = "\n".join([f"  • {name} (приоритет {priority})" for name, priority in list(all_roles.items())[:10]])
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{role_name}' не найдена!\n\n{EMOJIS['list']} Доступные роли:\n{available_roles}\n\n{EMOJIS['light']} Полный список: /roles")
            return
        
        target_priority = all_roles[role_name]
        is_admin_target = self.is_chat_admin(target_id, chat_id)
        
        if not self.db.can_manage_role(user_id, target_priority, chat_id, self.is_chat_admin(user_id, chat_id)):
            self.send_message(chat_id, f"{EMOJIS['cross']} Вы не можете назначить эту роль! Ваш приоритет должен быть выше.")
            return
        
        if is_admin_target:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя назначить роль администратору чата!")
            return
        
        if self.db.assign_role_to_user(target_id, chat_id, role_name, user_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} Роль назначена!

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['role']} Роль: {role_name}
{EMOJIS['priority']} Приоритет: {target_priority}
{EMOJIS['police']} Назначил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Посмотреть все роли: /roles"""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не удалось назначить роль!")
    
    def handle_remove_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /removerole [@user] - снятие роли с пользователя"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = None
        
        if reply_message:
            target_id = reply_message['from_id']
        else:
            target_id = self.extract_mention_or_id(args.strip())
        
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /removerole @user
2. /removerole (при ответе на сообщение)

{EMOJIS['light']} Пример: /removerole @durov""")
            return
        
        user_role = self.db.get_user_role(target_id, chat_id)
        if not user_role:
            self.send_message(chat_id, f"{EMOJIS['cross']} У пользователя нет роли!")
            return
        
        role_name, priority = user_role
        is_admin_target = self.is_chat_admin(target_id, chat_id)
        
        if not self.db.can_manage_role(user_id, priority, chat_id, self.is_chat_admin(user_id, chat_id)):
            self.send_message(chat_id, f"{EMOJIS['cross']} Вы не можете снять эту роль! Ваш приоритет должен быть выше.")
            return
        
        if is_admin_target:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя снять роль с администратора чата!")
            return
        
        if self.db.remove_user_role(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} Роль снята!

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['role']} Была роль: {role_name}
{EMOJIS['police']} Снял: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь без роли."""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не удалось снять роль!")
    
    def handle_roles_list(self, user_id: int, chat_id: int):
        """Команда /roles - список всех доступных ролей"""
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        
        if not all_roles:
            self.send_message(chat_id, f"{EMOJIS['role']} В этом чате пока нет ролей.\n{EMOJIS['light']} Администраторы могут создать роли командой /newrole")
            return
        
        custom_roles = []
        default_roles = []
        
        self.db.cursor.execute(
            "SELECT role_name FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_names = [row[0] for row in self.db.cursor.fetchall()]
        
        for name, priority in all_roles.items():
            if name in custom_names:
                custom_roles.append((name, priority))
            else:
                default_roles.append((name, priority))
        
        message = f"{EMOJIS['role']} {EMOJIS['list']} Все доступные роли (в скобках приоритет):\n\n"
        
        if custom_roles:
            message += f"{EMOJIS['star']} Кастомные роли:\n"
            for name, priority in custom_roles:
                message += f"  • {name} ({priority})\n"
            message += "\n"
        
        if default_roles:
            message += f"{EMOJIS['crown']} Стандартные роли:\n"
            for name, priority in default_roles[:10]:
                message += f"  • {name} ({priority})\n"
            
            if len(default_roles) > 10:
                message += f"  {EMOJIS['light']} ... и еще {len(default_roles) - 10} ролей\n"
        
        message += f"\n{EMOJIS['light']} Назначить роль: /setrole @user [название]\n{EMOJIS['light']} Посмотреть свою роль: /myrole"
        
        self.send_message(chat_id, message.strip())
    
    def handle_my_role(self, user_id: int, chat_id: int):
        """Команда /myrole - показать свою роль"""
        user_role = self.db.get_user_role(user_id, chat_id)
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        user_info = self.get_user_info(user_id)
        
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        elif user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        message = f"""{EMOJIS['profile']} Ваша роль

{EMOJIS['user']} Пользователь: [id{user_id}|{user_info['full_name']}]
{role_text}

{EMOJIS['list']} Посмотреть все роли: /roles"""
        
        self.send_message(chat_id, message)
    
    def handle_user_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /userrole [@user] - показать роль пользователя"""
        target_id = None
        
        if reply_message:
            target_id = reply_message['from_id']
        else:
            target_id = self.extract_mention_or_id(args.strip())
        
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /userrole @user
2. /userrole (при ответе на сообщение)

{EMOJIS['light']} Пример: /userrole @durov""")
            return
        
        user_info = self.get_user_info(target_id)
        user_role = self.db.get_user_role(target_id, chat_id)
        is_admin = self.is_chat_admin(target_id, chat_id)
        
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        elif user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        message = f"""{EMOJIS['profile']} Роль пользователя

{EMOJIS['user']} Пользователь: [id{target_id}|{user_info['full_name']}]
{role_text}

{EMOJIS['list']} Посмотреть все роли: /roles"""
        
        self.send_message(chat_id, message)
    
    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    def handle_create_rules(self, user_id: int, chat_id: int, args: str):
        """Команда /createpravila - установка правил"""
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
        
        if self.db.set_rules(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['rules']} Правила чата обновлены!

{EMOJIS['scroll']} Новые правила установлены.
{EMOJIS['light']} Теперь участники могут посмотреть их командой /правила

{EMOJIS['book']} Для просмотра: /правила
{EMOJIS['pen']} Для редактирования: /createpravila [новый текст]"""
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении правил. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_welcome(self, user_id: int, chat_id: int, args: str):
        """Команда /приветствие - установка приветствия (ИСПРАВЛЕНО)"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        if not args.strip():
            current_welcome = self.db.get_welcome_message(chat_id)
            self.send_message(chat_id, f"""{EMOJIS['welcome']} Текущее приветствие: 
{current_welcome}

{EMOJIS['light']} Использование: /приветствие [текст]
Пример: /приветствие Добро пожаловать в наш чат! Правила: /правила""")
            return
        
        if self.db.set_welcome_message(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['welcome']} Приветствие обновлено!

{EMOJIS['scroll']} Новое приветствие:
{args.strip()}

{EMOJIS['light']} Теперь это сообщение будет показываться новым участникам при входе в чат."""
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении приветствия. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_rules(self, user_id: int, chat_id: int):
        """Команда /правила - просмотр правил"""
        rules_text = self.db.get_rules(chat_id)
        
        if not rules_text or rules_text == 'Правила еще не установлены. Администраторы могут установить их командой /createpravila':
            message = f"""{EMOJIS['rules']} Правила чата

{EMOJIS['warning']} Правила еще не установлены.

{EMOJIS['police']} Администраторы могут установить правила командой:
/createpravila [текст правил]

{EMOJIS['light']} Пример:
/createpravila 1. Не спамить
2. Уважать других участников
3. Не размещать рекламу"""
        else:
            message = f"""{EMOJIS['rules']} Правила чата:

{rules_text}

──────────────
{EMOJIS['gavel']} Система наказаний:
{EMOJIS['warning']} 1-2 предупреждения - предупреждение
{EMOJIS['no_entry']} 3 предупреждения - автоматический бан
{EMOJIS['police']} Администраторы могут выдавать муты и баны

{EMOJIS['light']} По всем вопросам обращайтесь к администраторам."""
        
        self.send_message(chat_id, message)
    
    def handle_new_chat_member(self, chat_id: int, user_id: int):
        """Обработчик новых участников (ИСПРАВЛЕНО)"""
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
                    return
        
        self.db.add_user(user_id, chat_id)
        
        welcome_message = self.db.get_welcome_message(chat_id)
        user_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['welcome']} Добро пожаловать в чат!

{EMOJIS['party']} Приветствуем нового участника:
[id{user_id}|{user_info['full_name']}]

{EMOJIS['bell']} {welcome_message}

{EMOJIS['rules']} Обязательно ознакомьтесь с /правила
{EMOJIS['cmd']} Список всех команд: /CMD
{EMOJIS['info']} Ваша статистика: /профиль"""
        
        self.send_message(chat_id, message)
    
    def handle_bot_added(self, chat_id: int, user_id: int):
        """Обработчик добавления бота в чат"""
        settings = self.db.get_chat_settings(chat_id)
        
        if settings.get('bot_added_message_sent', 0) == 1:
            return
        
        self.db.set_bot_added_message_sent(chat_id, 1)
        
        message = f"""{EMOJIS['robot']} {EMOJIS['party']} Спасибо что добавили меня в чат!

{EMOJIS['warning']} {EMOJIS['mega']} ВАЖНО: Для полноценной работы мне необходимы права администратора!

{EMOJIS['gear']} Что нужно сделать:
1. Откройте настройки беседы
2. Перейдите в раздел \"Участники\"
3. Найдите меня в списке (Avrora Manager)
4. Назначьте администратором с правами:
   {EMOJIS['check']} Управление беседой
   {EMOJIS['check']} Удаление сообщений
   {EMOJIS['check']} Исключение участников

{EMOJIS['crown']} Только после этого будут работать команды:
{EMOJIS['mute']} /mute - ограничение на отправку сообщений
{EMOJIS['kick']} /kick - исключение из чата
{EMOJIS['no_entry']} /ban - бан пользователя
{EMOJIS['warning']} /warn - предупреждения

{EMOJIS['cmd']} Все команды: /CMD
{EMOJIS['rules']} Установка правил: /createpravila [текст]
{EMOJIS['welcome']} Приветствие: /приветствие [текст]

{EMOJIS['light']} Если права уже выданы - игнорируйте это сообщение."""
        
        self.send_message(chat_id, message)
    
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

{EMOJIS['crown']} Администраторы чата ({len(admin_list)}):
{chr(10).join(admin_list) if admin_list else f"{EMOJIS['cross']} Нет данных"}

{EMOJIS['cmd']} Используйте /CMD для списка команд"""
        
        self.send_message(chat_id, message)
    
    def handle_mute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split()
        if len(parts) < 1 and not reply_message:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование: 
1. /mute @user время причина
2. /mute время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
30m - 30 минут
2h - 2 часа
1d - 1 день
7d - 7 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/mute @durov 30m спам
/mute 1d флуд (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user, ID или ответьте на сообщение.")
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

{EMOJIS['warning']} Нарушитель не сможет писать в чат до окончания мута."""
        
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
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user или ответьте на сообщение.")
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

{EMOJIS['ban_hammer']} Результат: Автоматический бан на {settings.get('ban_duration', 10)} дней за превышение лимита предупреждений."""
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

{EMOJIS['light']} Внимание: При достижении {max_warns} предупреждений последует автоматический бан на {settings.get('ban_duration', 10)} дней."""
        
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
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user или ответьте на сообщение.")
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

{EMOJIS['light']} Пользователь может вернуться в чат по приглашению."""
            
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
1. /ban @user время причина
2. /ban время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
1d - 1 день
7d - 7 дней
30d - 30 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/ban @durov 10d спам
/ban 7d нарушение (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user, ID или ответьте на сообщение.")
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

{EMOJIS['warning']} Пользователь будет автоматически кикаться при попытке вернуться в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_self_kick(self, user_id: int, chat_id: int):
        try:
            self.vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )
        except Exception as e:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка при выходе: {str(e)}")
    
    def handle_unmute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование:
1. /размут @user
2. /размут (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/размут @durov
/размут (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, mute_until=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь размучен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Теперь пользователь может писать в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_unban(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['no_entry']} Использование:
1. /разбан @user
2. /разбан (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/разбан @durov
/разбан (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, ban_until=0, kicked=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь разбанен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь может вернуться в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_unwarn(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['warning']} Использование:
1. /снятьварн @user
2. /снятьварн (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/снятьварн @durov
/снятьварн (при ответе на сообщение)""")
            return
        
        if self.db.remove_warn(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} {EMOJIS['warning']} Снято предупреждение

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Одно предупреждение снято."""
        else:
            message = f"{EMOJIS['cross']} У пользователя нет активных предупреждений."
        
        self.send_message(chat_id, message)
    
    # ========== КОМАНДЫ ДЛЯ ВСЕХ ==========
    
    def handle_cmd(self, user_id: int, chat_id: int):
        """Команда /CMD - список всех команд"""
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        if is_admin:
            message = f"""{EMOJIS['cmd']} {EMOJIS['admin_cmd']} ПОЛНЫЙ СПИСОК КОМАНД

{EMOJIS['crown']} АДМИНИСТРАТОРСКИЕ КОМАНДЫ:

{EMOJIS['role']} • УПРАВЛЕНИЕ РОЛЯМИ:
/newrole [приоритет] [название] - создать роль
/deleterole [название] - удалить роль
/updaterole [старое] [приоритет] [новое] - обновить роль
/setrole @user [роль] - назначить роль
/removerole @user - снять роль
/roles - все доступные роли
/userrole @user - роль пользователя

{EMOJIS['gavel']} • НАКАЗАНИЯ:
/mute @user время причина - мут
/warn @user причина - предупреждение
/kick @user причина - кик
/ban @user время причина - бан
/размут @user - снять мут
/разбан @user - снять бан
/снятьварн @user - снять варн

{EMOJIS['gear']} • НАСТРОЙКИ:
/createpravila [текст] - установить правила
/приветствие [текст] - установить приветствие
/admin - статистика админа

{EMOJIS['user']} ОБЩИЕ КОМАНДЫ:

{EMOJIS['info']} /инфо [@user] - инфо о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 - создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - результаты
{EMOJIS['profile']} /профиль - ваш профиль
{EMOJIS['myrole']} /myrole - ваша роль
{EMOJIS['online']} /онлайн - кто онлайн
{EMOJIS['rules']} /правила - правила чата
{EMOJIS['exit']} /q - выйти из чата
{EMOJIS['cmd']} /CMD - этот список

{EMOJIS['clock']} Форматы времени: 30m, 2h, 1d, 7d, 0 - бессрочно

{EMOJIS['warning']} Для работы мута/бана/кика бот должен быть админом чата!"""
        else:
            message = f"""{EMOJIS['cmd']} {EMOJIS['user_cmd']} ДОСТУПНЫЕ КОМАНДЫ

{EMOJIS['info']} /инфо [@user] - информация о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 - создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - результаты опроса
{EMOJIS['profile']} /профиль - ваш профиль
{EMOJIS['myrole']} /myrole - ваша роль
{EMOJIS['online']} /онлайн - кто онлайн
{EMOJIS['rules']} /правила - правила чата
{EMOJIS['roles']} /roles - список всех ролей
{EMOJIS['userrole']} /userrole @user - роль пользователя
{EMOJIS['exit']} /q - выйти из чата
{EMOJIS['cmd']} /CMD - этот список

{EMOJIS['gavel']} СИСТЕМА НАКАЗАНИЙ:
{EMOJIS['warning']} 3 предупреждения = автоматический бан

{EMOJIS['light']} По вопросам обращайтесь к администраторам чата."""
        
        self.send_message(chat_id, message)
    
    def handle_info(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /инфо - информация о пользователе"""
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            target_id = user_id
        
        user_info = self.get_user_info(target_id)
        self.db.add_user(target_id, chat_id)
        user_data = self.db.get_user(target_id, chat_id)
        user_stats = self.db.get_user_stats(target_id, chat_id)
        
        is_admin = self.is_chat_admin(target_id, chat_id)
        user_role = self.db.get_user_role(target_id, chat_id)
        
        if user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        status = []
        if user_stats.get('muted'):
            status.append(f"{EMOJIS['mute']} В муте")
        if user_stats.get('banned'):
            status.append(f"{EMOJIS['no_entry']} Забанен")
        if user_stats.get('kicked'):
            status.append(f"{EMOJIS['kick']} Кикнут")
        if not status:
            status.append(f"{EMOJIS['green_circle']} Активен")
        
        join_date = user_stats.get('join_date', 'Неизвестно')
        if join_date and join_date != 'Неизвестно':
            try:
                dt = datetime.datetime.strptime(join_date[:19], "%Y-%m-%d %H:%M:%S")
                join_date = dt.strftime("%d.%m.%Y в %H:%M")
            except:
                pass
        
        self.db.cursor.execute(
            "SELECT reason, date, admin_id FROM warns_history WHERE user_id = ? AND chat_id = ? ORDER BY date DESC LIMIT 3",
            (target_id, chat_id)
        )
        recent_warns = self.db.cursor.fetchall()
        
        warns_history = ""
        if recent_warns:
            warns_history = f"\n{EMOJIS['warning']} Последние предупреждения:\n"
            for reason, warn_date, admin_id in recent_warns:
                admin_info = self.get_user_info(admin_id)
                dt = datetime.datetime.strptime(warn_date[:19], "%Y-%m-%d %H:%M:%S")
                formatted_date = dt.strftime("%d.%m.%Y")
                warns_history += f"  • {reason} ({formatted_date}, от [id{admin_id}|{admin_info['first_name']}])\n"
        
        message = f"""{EMOJIS['info']} Информация о пользователе

{EMOJIS['user']} ОСНОВНАЯ ИНФОРМАЦИЯ:
{EMOJIS['light']} Имя: {user_info['full_name']}
{EMOJIS['light']} ID: {target_id}
{role_text}
{EMOJIS['star']} Статус: {', '.join(status)}

{EMOJIS['chart']} СТАТИСТИКА:
{EMOJIS['warning']} Активные предупреждения: {user_stats.get('warns', 0)}
{EMOJIS['chart']} Всего предупреждений: {user_stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{warns_history}

{EMOJIS['cmd']} Полный список команд: /CMD"""
        
        self.send_message(chat_id, message)
    
    def handle_poll(self, user_id: int, chat_id: int, args: str):
        """Команда /опрос - создание опроса"""
        if not args.strip():
            self.send_message(chat_id, f"""{EMOJIS['poll']} Использование: /опрос [вопрос] | [вариант1] | [вариант2] | ...
            
{EMOJIS['light']} Примеры:
/опрос Какой день лучше для встречи? | Понедельник | Вторник | Среда
/опрос Любимый цвет? | Красный | Синий | Зеленый | Желтый

{EMOJIS['vote']} Голосовать: ответьте на сообщение с номером варианта (1, 2, 3...)
{EMOJIS['chart']} Результаты: /опросрезультаты""")
            return
        
        parts = args.split('|')
        if len(parts) < 3:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно указать вопрос и минимум 2 варианта ответа, разделенные |")
            return
        
        question = parts[0].strip()
        options = [opt.strip() for opt in parts[1:] if opt.strip()]
        
        if len(options) < 2:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно минимум 2 варианта ответа")
            return
        
        if len(options) > 10:
            self.send_message(chat_id, f"{EMOJIS['cross']} Максимум 10 вариантов ответа")
            return
        
        poll_id = self.db.create_poll(chat_id, user_id, question, options)
        user_info = self.get_user_info(user_id)
        
        options_text = ""
        for i, option in enumerate(options, 1):
            options_text += f"{i}. {option}\n"
        
        message = f"""{EMOJIS['poll']} Новый опрос #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['vote']} Варианты ответов:
{options_text}
{EMOJIS['user']} Создал: [id{user_id}|{user_info['full_name']}]

{EMOJIS['light']} Голосование: ответьте на это сообщение с номером варианта (1, 2, 3...)

{EMOJIS['chart']} Результаты: /опросрезультаты {poll_id}"""
        
        self.send_message(chat_id, message)
    
    def handle_poll_results(self, user_id: int, chat_id: int, args: str):
        """Команда /опросрезультаты - результаты опроса"""
        if not args.strip():
            active_polls = self.db.get_active_polls(chat_id)
            
            if not active_polls:
                self.send_message(chat_id, f"{EMOJIS['poll']} В этом чате нет активных опросов.\n{EMOJIS['light']} Создайте опрос: /опрос вопрос | вариант1 | вариант2")
                return
            
            message = f"{EMOJIS['poll']} Активные опросы:\n\n"
            for poll in active_polls[:5]:
                creator_info = self.get_user_info(poll['creator_id'])
                message += f"{EMOJIS['vote']} Опрос #{poll['poll_id']}: {poll['question'][:50]}...\n"
                message += f"   Создал: [id{poll['creator_id']}|{creator_info['first_name']}]\n"
                message += f"   /опросрезультаты {poll['poll_id']}\n\n"
            
            if len(active_polls) > 5:
                message += f"{EMOJIS['light']} ... и еще {len(active_polls) - 5} опросов"
            
            self.send_message(chat_id, message.strip())
            return
        
        try:
            poll_id = int(args.strip())
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Укажите номер опроса. Например: /опросрезультаты 1")
            return
        
        results = self.db.get_poll_results(poll_id)
        if not results:
            self.send_message(chat_id, f"{EMOJIS['cross']} Опрос #{poll_id} не найден")
            return
        
        question = results['question']
        options = results['options']
        vote_results = results['results']
        total_votes = results['total_votes']
        creator_info = self.get_user_info(results['creator_id'])
        
        results_text = ""
        for i, option in enumerate(options):
            votes = vote_results.get(i, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            bars = int(percentage / 10)
            progress_bar = "█" * bars + "░" * (10 - bars)
            
            results_text += f"{i+1}. {option}\n"
            results_text += f"   {progress_bar} {votes} голосов ({percentage:.1f}%)\n\n"
        
        message = f"""{EMOJIS['poll']} Результаты опроса #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['chart']} Результаты:
{results_text}
{EMOJIS['vote']} Всего голосов: {total_votes}
{EMOJIS['user']} Создал: [id{results['creator_id']}|{creator_info['full_name']}]

{EMOJIS['clock']} Создан: {results['created_at'][:19]}"""
        
        self.send_message(chat_id, message)
    
    def handle_poll_vote(self, user_id: int, chat_id: int, reply_message: Dict, vote_text: str):
        """Обработка голосования в опросе"""
        poll_match = re.search(r'Опрос #(\d+)', reply_message.get('text', ''))
        if not poll_match:
            return
        
        poll_id = int(poll_match.group(1))
        
        try:
            option_num = int(vote_text.strip())
            option_index = option_num - 1
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Пожалуйста], укажите номер варианта (1, 2, 3...)")
            return
        
        poll = self.db.get_poll(poll_id)
        if not poll or not poll['is_active']:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Этот опрос уже завершен]")
            return
        
        if option_index < 0 or option_index >= len(poll['options']):
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Неправильный номер варианта. Доступно: 1-{len(poll['options'])}]")
            return
        
        if self.db.vote_poll(poll_id, user_id, option_index):
            user_info = self.get_user_info(user_id)
            option_text = poll['options'][option_index]
            
            results = self.db.get_poll_results(poll_id)
            votes_for_option = results['results'].get(option_index, 0)
            total_votes = results['total_votes']
            percentage = (votes_for_option / total_votes * 100) if total_votes > 0 else 0
            
            message = f"""{EMOJIS['check']} [id{user_id}|{user_info['first_name']}], ваш голос учтен!

{EMOJIS['vote']} Вы выбрали: {option_text}
{EMOJIS['chart']} За этот вариант: {votes_for_option} голосов ({percentage:.1f}%)
{EMOJIS['light']} Всего голосов: {total_votes}

{EMOJIS['poll']} Результаты: /опросрезультаты {poll_id}"""
            
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Не удалось зарегистрировать ваш голос]")
    
    def handle_profile(self, user_id: int, chat_id: int):
        """Команда /профиль - профиль пользователя"""
        self.db.add_user(user_id, chat_id)
        stats = self.db.get_user_stats(user_id, chat_id)
        user_info = self.get_user_info(user_id)
        
        is_admin = self.is_chat_admin(user_id, chat_id)
        user_role = self.db.get_user_role(user_id, chat_id)
        
        if user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
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
{role_text}
{EMOJIS['warning']} Активные предупреждения: {stats.get('warns', 0)}
{EMOJIS['chart']} Всего получено варнов: {stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{EMOJIS['star']} Статус: {status}

{EMOJIS['info']} Подробная информация: /инфо
{EMOJIS['cmd']} Все команды: /CMD"""
        
        self.send_message(chat_id, message)
    
    def handle_online(self, user_id: int, chat_id: int):
        """Команда /онлайн - кто онлайн"""
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
    
    def check_punishments(self):
        """Проверка истечения наказаний"""
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
        """Обработка входящих сообщений"""
        try:
            message = event.object.message
            chat_id = event.chat_id
            user_id = message['from_id']
            text = message.get('text', '').strip()
            
            event_id = f"{chat_id}_{message.get('conversation_message_id', '')}"
            if event_id in self.processed_events:
                return
            self.processed_events.add(event_id)
            if len(self.processed_events) > 1000:
                self.processed_events.clear()
            
            print(f"{EMOJIS['robot']} Сообщение от {user_id} в чате {chat_id}: {text}")
            
            user_data = self.db.get_user(user_id, chat_id)
            
            if user_data and user_data['ban_until'] > 0:
                ban_active = True if user_data['ban_until'] == 0 else user_data['ban_until'] > time.time()
                
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
            
            if user_data and user_data['mute_until'] > 0:
                mute_active = True if user_data['mute_until'] == 0 else user_data['mute_until'] > time.time()
                
                if mute_active:
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
                
                if command == '/newrole':
                    self.handle_new_role(user_id, chat_id, args)
                elif command == '/deleterole':
                    self.handle_delete_role(user_id, chat_id, args)
                elif command == '/updaterole':
                    self.handle_update_role(user_id, chat_id, args)
                elif command == '/setrole':
                    self.handle_set_role(user_id, chat_id, args, reply_message)
                elif command == '/removerole':
                    self.handle_remove_role(user_id, chat_id, args, reply_message)
                elif command == '/roles':
                    self.handle_roles_list(user_id, chat_id)
                elif command == '/myrole':
                    self.handle_my_role(user_id, chat_id)
                elif command == '/userrole':
                    self.handle_user_role(user_id, chat_id, args, reply_message)
                elif command == '/admin':
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
                elif command in ['/правила', '/rules']:
                    self.handle_rules(user_id, chat_id)
                elif command in ['/размут', '/unmute']:
                    self.handle_unmute(user_id, chat_id, args, reply_message)
                elif command in ['/разбан', '/unban']:
                    self.handle_unban(user_id, chat_id, args, reply_message)
                elif command in ['/снятьварн', '/unwarn', '/снятьпред']:
                    self.handle_unwarn(user_id, chat_id, args, reply_message)
                elif command in ['/инфо', '/info']:
                    self.handle_info(user_id, chat_id, args, reply_message)
                elif command in ['/опрос', '/poll', '/голосование']:
                    self.handle_poll(user_id, chat_id, args)
                elif command in ['/опросрезультаты', '/pollresults', '/результаты']:
                    self.handle_poll_results(user_id, chat_id, args)
                elif command in ['/cmd', '/CMD', '/команды', '/help']:
                    self.handle_cmd(user_id, chat_id)
                elif command in ['/профиль', '/profile']:
                    self.handle_profile(user_id, chat_id)
                elif command in ['/онлайн', '/online']:
                    self.handle_online(user_id, chat_id)
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. Используйте /CMD для списка команд.")
            
            elif reply_message and reply_message.get('from_id') == -int(GROUP_ID):
                reply_text = reply_message.get('text', '')
                if 'Опрос #' in reply_text and text.strip().isdigit():
                    self.handle_poll_vote(user_id, chat_id, reply_message, text)
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка обработки сообщения: {e}")
    
    def run(self):
        """Запуск бота"""
        punishment_thread = threading.Thread(target=self.check_punishments, daemon=True)
        punishment_thread.start()
        
        print(f"\n{EMOJIS['robot']} Бот запущен и слушает сообщения...")
        print(f"{EMOJIS['crown']} Админы определяются автоматически")
        print(f"{EMOJIS['role']} Система ролей с приоритетами активна")
        print(f"{EMOJIS['welcome']} Приветствие работает (исправлено)")
        print(f"{EMOJIS['cmd']} Команда /CMD - полный список команд")
        print(f"{EMOJIS['gear']} База данных: avrora_bot.db\n")
        
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat:
                        self.process_message(event)
                
                elif event.type == VkBotEventType.CHAT_INVITE_USER:
                    if event.object.get('user_id') == -int(GROUP_ID):
                        chat_id = event.chat_id
                        inviter_id = event.object.get('from_id')
                        self.handle_bot_added(chat_id, inviter_id)
                
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
    {EMOJIS['role']} Система ролей с приоритетами
    {EMOJIS['cmd']} Полный список команд: /CMD
    {EMOJIS['robot']} ====================================
    """)
    
    print(f"{EMOJIS['light']} Проверяем права бота...")
    
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_TOKEN на валидный токен группы VK!")
    elif GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_ID на ID вашей группы (только цифры)!")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Бот остановлен пользователем")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Критическая ошибка: {e}")# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        if os.path.exists('avrora_bot.db'):
            print(f"{EMOJIS['gear']} Загружаем существующую базу данных...")
        
        self.conn = sqlite3.connect('avrora_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_default_roles()
    
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
                rules_text TEXT DEFAULT 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
                max_warns INTEGER DEFAULT 3,
                ban_duration INTEGER DEFAULT 10,
                bot_added_message_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица ролей (кастомные роли для чата)
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
        
        # Таблица назначенных ролей пользователям
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
        
        # Таблица опросов
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
        """Инициализация стандартных ролей"""
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
    
    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С РОЛЯМИ ==========
    
    def create_custom_role(self, chat_id: int, role_name: str, priority: int, created_by: int) -> bool:
        """Создание новой кастомной роли в чате"""
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
        """Удаление кастомной роли"""
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
        """Обновление кастомной роли"""
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
        """Получение всех ролей чата (стандартные + кастомные) с приоритетами"""
        roles = self.default_roles.copy()
        
        self.cursor.execute(
            "SELECT role_name, priority FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_roles = self.cursor.fetchall()
        for role_name, priority in custom_roles:
            roles[role_name] = priority
        
        sorted_roles = dict(sorted(roles.items(), key=lambda x: x[1], reverse=True))
        return sorted_roles
    
    def assign_role_to_user(self, user_id: int, chat_id: int, role_name: str, assigned_by: int) -> bool:
        """Назначение роли пользователю"""
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
        """Снятие роли с пользователя"""
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
        """Получение роли пользователя и её приоритета"""
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
        """Получение всех пользователей с ролями в чате"""
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
        
        user_roles.sort(key=lambda x: x[2], reverse=True)
        return user_roles
    
    def get_user_priority(self, user_id: int, chat_id: int, is_admin: bool = False) -> int:
        """Получение приоритета пользователя"""
        if is_admin:
            return 90
        
        user_role = self.get_user_role(user_id, chat_id)
        if user_role:
            return user_role[1]
        
        return 0
    
    def can_manage_role(self, admin_id: int, target_priority: int, chat_id: int, is_admin: bool = False) -> bool:
        """Проверка, может ли администратор управлять ролью с указанным приоритетом"""
        admin_priority = self.get_user_priority(admin_id, chat_id, is_admin)
        return admin_priority > target_priority
    
    # ========== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========
    
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
            settings = dict(zip(columns, row))
            if 'welcome_message' not in settings:
                settings['welcome_message'] = 'Добро пожаловать в чат!'
            if 'rules_text' not in settings:
                settings['rules_text'] = 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
            if 'max_warns' not in settings:
                settings['max_warns'] = 3
            if 'ban_duration' not in settings:
                settings['ban_duration'] = 10
            if 'bot_added_message_sent' not in settings:
                settings['bot_added_message_sent'] = 0
            return settings
        
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
            (chat_id, 
             default_settings['welcome_message'],
             default_settings['rules_text'],
             default_settings['max_warns'],
             default_settings['ban_duration'],
             default_settings['bot_added_message_sent'])
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
    
    def set_rules(self, chat_id: int, rules_text: str):
        return self.update_chat_settings(chat_id, rules_text=rules_text)
    
    def get_rules(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        if settings and 'rules_text' in settings:
            return settings['rules_text']
        return 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
    
    def set_welcome_message(self, chat_id: int, welcome_message: str):
        return self.update_chat_settings(chat_id, welcome_message=welcome_message)
    
    def get_welcome_message(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        if settings and 'welcome_message' in settings:
            return settings['welcome_message']
        return 'Добро пожаловать в чат!'
    
    def set_bot_added_message_sent(self, chat_id: int, sent: int = 1):
        return self.update_chat_settings(chat_id, bot_added_message_sent=sent)
    
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
        role_name = user_role[0] if user_role else 'member'
        
        return {
            'user_id': user_id,
            'warns': user['warns'],
            'total_warns': total_warns,
            'muted': user['mute_until'] > time.time(),
            'banned': user['ban_until'] > time.time(),
            'kicked': user.get('kicked', 0),
            'role': role_name,
            'join_date': user['join_date']
        }
    
    # Методы для опросов
    def create_poll(self, chat_id: int, creator_id: int, question: str, options: List[str]) -> int:
        options_json = json.dumps(options, ensure_ascii=False)
        votes_json = json.dumps({}, ensure_ascii=False)
        
        self.cursor.execute(
            "INSERT INTO polls (chat_id, creator_id, question, options, votes) VALUES (?, ?, ?, ?, ?)",
            (chat_id, creator_id, question, options_json, votes_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_poll(self, poll_id: int) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT * FROM polls WHERE poll_id = ?",
            (poll_id,)
        )
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
        if str(user_id) in votes:
            del votes[str(user_id)]
        
        votes[str(user_id)] = option_index
        votes_json = json.dumps(votes, ensure_ascii=False)
        
        self.cursor.execute(
            "UPDATE polls SET votes = ? WHERE poll_id = ?",
            (votes_json, poll_id)
        )
        self.conn.commit()
        return True
    
    def get_poll_results(self, poll_id: int) -> Dict:
        poll = self.get_poll(poll_id)
        if not poll:
            return {}
        
        votes = poll['votes']
        options = poll['options']
        
        results = {i: 0 for i in range(len(options))}
        for vote in votes.values():
            if vote in results:
                results[vote] += 1
        
        total_votes = sum(results.values())
        
        return {
            'question': poll['question'],
            'options': options,
            'results': results,
            'total_votes': total_votes,
            'creator_id': poll['creator_id'],
            'created_at': poll['created_at']
        }
    
    def get_active_polls(self, chat_id: int) -> List[Dict]:
        self.cursor.execute(
            "SELECT poll_id, question, creator_id FROM polls WHERE chat_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (chat_id,)
        )
        rows = self.cursor.fetchall()
        return [{'poll_id': row[0], 'question': row[1], 'creator_id': row[2]} for row in rows]

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
        print(f"{EMOJIS['crown']} Админы определяются автоматически по правам в чате")
        print(f"{EMOJIS['role']} Новая система ролей с приоритетами активна!")
        print(f"{EMOJIS['cmd']} Команда /CMD - список всех команд")
    
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
        match = re.search(r'\[id(\d+)\|', text)
        if match:
            return int(match.group(1))
        
        match = re.search(r'@id(\d+)', text)
        if match:
            return int(match.group(1))
        
        if reply_message and 'from_id' in reply_message:
            return reply_message['from_id']
        
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
    
    # ========== КОМАНДЫ ДЛЯ РОЛЕЙ ==========
    
    def handle_new_role(self, user_id: int, chat_id: int, args: str):
        """Команда /newrole [приоритет] [название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование: /newrole [приоритет] [название]

{EMOJIS['priority']} Приоритет: 0 (низший) - 100 (высший)

{EMOJIS['light']} Примеры:
/newrole 50 Менеджер
/newrole 25 Помощник
/newrole 75 Старший Модератор""")
            return
        
        try:
            priority = int(parts[0])
            if priority < 0 or priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть от 0 до 100!")
                return
            
            role_name = parts[1].strip()
            if len(role_name) > 50:
                self.send_message(chat_id, f"{EMOJIS['cross']} Название роли слишком длинное (макс. 50 символов)")
                return
            
            if self.db.create_custom_role(chat_id, role_name, priority, user_id):
                admin_info = self.get_user_info(user_id)
                message = f"""{EMOJIS['check']} Роль успешно создана!

{EMOJIS['role']} Название: {role_name}
{EMOJIS['priority']} Приоритет: {priority}
{EMOJIS['police']} Создал: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь вы можете назначать эту роль:
/setrole @user {role_name}

{EMOJIS['list']} Посмотреть все роли: /roles"""
                self.send_message(chat_id, message)
            else:
                self.send_message(chat_id, f"{EMOJIS['cross']} Роль с таким названием уже существует!")
                
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
    
    def handle_delete_role(self, user_id: int, chat_id: int, args: str):
        """Команда /deleterole [название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        role_name = args.strip()
        if not role_name:
            self.send_message(chat_id, f"{EMOJIS['role']} Использование: /deleterole [название]\n\n{EMOJIS['light']} Пример: /deleterole Менеджер")
            return
        
        if self.db.delete_custom_role(chat_id, role_name):
            admin_info = self.get_user_info(user_id)
            message = f"""{EMOJIS['check']} Роль удалена!

{EMOJIS['role']} Название: {role_name}
{EMOJIS['police']} Удалил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['warning']} Все пользователи лишились этой роли."""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{role_name}' не найдена!")
    
    def handle_update_role(self, user_id: int, chat_id: int, args: str):
        """Команда /updaterole [старое название] [новый приоритет] [новое название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=2)
        if len(parts) < 3:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование: /updaterole [старое название] [новый приоритет] [новое название]

{EMOJIS['light']} Пример: /updaterole Менеджер 55 Старший Менеджер""")
            return
        
        old_name = parts[0].strip()
        
        try:
            new_priority = int(parts[1])
            if new_priority < 0 or new_priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть от 0 до 100!")
                return
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
            return
        
        new_name = parts[2].strip()
        
        if self.db.update_custom_role(chat_id, old_name, new_name, new_priority):
            admin_info = self.get_user_info(user_id)
            message = f"""{EMOJIS['check']} Роль обновлена!

{EMOJIS['role']} Было: {old_name}
{EMOJIS['role']} Стало: {new_name}
{EMOJIS['priority']} Новый приоритет: {new_priority}
{EMOJIS['police']} Обновил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['list']} Посмотреть все роли: /roles"""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{old_name}' не найдена!")
    
    def handle_set_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /setrole [@user] [роль] - назначение роли пользователю"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
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
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /setrole @user [роль]
2. /setrole [роль] (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/setrole @durov Администратор
/setrole Модератор (ответ на сообщение)""")
            return
        
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        if role_name not in all_roles:
            available_roles = "\n".join([f"  • {name} (приоритет {priority})" for name, priority in list(all_roles.items())[:10]])
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{role_name}' не найдена!\n\n{EMOJIS['list']} Доступные роли:\n{available_roles}\n\n{EMOJIS['light']} Полный список: /roles")
            return
        
        target_priority = all_roles[role_name]
        is_admin_target = self.is_chat_admin(target_id, chat_id)
        
        if not self.db.can_manage_role(user_id, target_priority, chat_id, self.is_chat_admin(user_id, chat_id)):
            self.send_message(chat_id, f"{EMOJIS['cross']} Вы не можете назначить эту роль! Ваш приоритет должен быть выше.")
            return
        
        if is_admin_target:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя назначить роль администратору чата!")
            return
        
        if self.db.assign_role_to_user(target_id, chat_id, role_name, user_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} Роль назначена!

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['role']} Роль: {role_name}
{EMOJIS['priority']} Приоритет: {target_priority}
{EMOJIS['police']} Назначил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Посмотреть все роли: /roles"""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не удалось назначить роль!")
    
    def handle_remove_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /removerole [@user] - снятие роли с пользователя"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = None
        
        if reply_message:
            target_id = reply_message['from_id']
        else:
            target_id = self.extract_mention_or_id(args.strip())
        
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /removerole @user
2. /removerole (при ответе на сообщение)

{EMOJIS['light']} Пример: /removerole @durov""")
            return
        
        user_role = self.db.get_user_role(target_id, chat_id)
        if not user_role:
            self.send_message(chat_id, f"{EMOJIS['cross']} У пользователя нет роли!")
            return
        
        role_name, priority = user_role
        is_admin_target = self.is_chat_admin(target_id, chat_id)
        
        if not self.db.can_manage_role(user_id, priority, chat_id, self.is_chat_admin(user_id, chat_id)):
            self.send_message(chat_id, f"{EMOJIS['cross']} Вы не можете снять эту роль! Ваш приоритет должен быть выше.")
            return
        
        if is_admin_target:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя снять роль с администратора чата!")
            return
        
        if self.db.remove_user_role(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} Роль снята!

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['role']} Была роль: {role_name}
{EMOJIS['police']} Снял: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь без роли."""
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не удалось снять роль!")
    
    def handle_roles_list(self, user_id: int, chat_id: int):
        """Команда /roles - список всех доступных ролей"""
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        
        if not all_roles:
            self.send_message(chat_id, f"{EMOJIS['role']} В этом чате пока нет ролей.\n{EMOJIS['light']} Администраторы могут создать роли командой /newrole")
            return
        
        custom_roles = []
        default_roles = []
        
        self.db.cursor.execute(
            "SELECT role_name FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_names = [row[0] for row in self.db.cursor.fetchall()]
        
        for name, priority in all_roles.items():
            if name in custom_names:
                custom_roles.append((name, priority))
            else:
                default_roles.append((name, priority))
        
        message = f"{EMOJIS['role']} {EMOJIS['list']} Все доступные роли (в скобках приоритет):\n\n"
        
        if custom_roles:
            message += f"{EMOJIS['star']} Кастомные роли:\n"
            for name, priority in custom_roles:
                message += f"  • {name} ({priority})\n"
            message += "\n"
        
        if default_roles:
            message += f"{EMOJIS['crown']} Стандартные роли:\n"
            for name, priority in default_roles[:10]:
                message += f"  • {name} ({priority})\n"
            
            if len(default_roles) > 10:
                message += f"  {EMOJIS['light']} ... и еще {len(default_roles) - 10} ролей\n"
        
        message += f"\n{EMOJIS['light']} Назначить роль: /setrole @user [название]\n{EMOJIS['light']} Посмотреть свою роль: /myrole"
        
        self.send_message(chat_id, message.strip())
    
    def handle_my_role(self, user_id: int, chat_id: int):
        """Команда /myrole - показать свою роль"""
        user_role = self.db.get_user_role(user_id, chat_id)
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        user_info = self.get_user_info(user_id)
        
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        elif user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        message = f"""{EMOJIS['profile']} Ваша роль

{EMOJIS['user']} Пользователь: [id{user_id}|{user_info['full_name']}]
{role_text}

{EMOJIS['list']} Посмотреть все роли: /roles"""
        
        self.send_message(chat_id, message)
    
    def handle_user_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /userrole [@user] - показать роль пользователя"""
        target_id = None
        
        if reply_message:
            target_id = reply_message['from_id']
        else:
            target_id = self.extract_mention_or_id(args.strip())
        
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /userrole @user
2. /userrole (при ответе на сообщение)

{EMOJIS['light']} Пример: /userrole @durov""")
            return
        
        user_info = self.get_user_info(target_id)
        user_role = self.db.get_user_role(target_id, chat_id)
        is_admin = self.is_chat_admin(target_id, chat_id)
        
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        elif user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        message = f"""{EMOJIS['profile']} Роль пользователя

{EMOJIS['user']} Пользователь: [id{target_id}|{user_info['full_name']}]
{role_text}

{EMOJIS['list']} Посмотреть все роли: /roles"""
        
        self.send_message(chat_id, message)
    
    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    def handle_create_rules(self, user_id: int, chat_id: int, args: str):
        """Команда /createpravila - установка правил"""
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
        
        if self.db.set_rules(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['rules']} Правила чата обновлены!

{EMOJIS['scroll']} Новые правила установлены.
{EMOJIS['light']} Теперь участники могут посмотреть их командой /правила

{EMOJIS['book']} Для просмотра: /правила
{EMOJIS['pen']} Для редактирования: /createpravila [новый текст]"""
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении правил. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_welcome(self, user_id: int, chat_id: int, args: str):
        """Команда /приветствие - установка приветствия (ИСПРАВЛЕНО)"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        if not args.strip():
            current_welcome = self.db.get_welcome_message(chat_id)
            self.send_message(chat_id, f"""{EMOJIS['welcome']} Текущее приветствие: 
{current_welcome}

{EMOJIS['light']} Использование: /приветствие [текст]
Пример: /приветствие Добро пожаловать в наш чат! Правила: /правила""")
            return
        
        if self.db.set_welcome_message(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['welcome']} Приветствие обновлено!

{EMOJIS['scroll']} Новое приветствие:
{args.strip()}

{EMOJIS['light']} Теперь это сообщение будет показываться новым участникам при входе в чат."""
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении приветствия. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_rules(self, user_id: int, chat_id: int):
        """Команда /правила - просмотр правил"""
        rules_text = self.db.get_rules(chat_id)
        
        if not rules_text or rules_text == 'Правила еще не установлены. Администраторы могут установить их командой /createpravila':
            message = f"""{EMOJIS['rules']} Правила чата

{EMOJIS['warning']} Правила еще не установлены.

{EMOJIS['police']} Администраторы могут установить правила командой:
/createpravila [текст правил]

{EMOJIS['light']} Пример:
/createpravila 1. Не спамить
2. Уважать других участников
3. Не размещать рекламу"""
        else:
            message = f"""{EMOJIS['rules']} Правила чата:

{rules_text}

──────────────
{EMOJIS['gavel']} Система наказаний:
{EMOJIS['warning']} 1-2 предупреждения - предупреждение
{EMOJIS['no_entry']} 3 предупреждения - автоматический бан
{EMOJIS['police']} Администраторы могут выдавать муты и баны

{EMOJIS['light']} По всем вопросам обращайтесь к администраторам."""
        
        self.send_message(chat_id, message)
    
    def handle_new_chat_member(self, chat_id: int, user_id: int):
        """Обработчик новых участников (ИСПРАВЛЕНО)"""
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
                    return
        
        self.db.add_user(user_id, chat_id)
        
        welcome_message = self.db.get_welcome_message(chat_id)
        user_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['welcome']} Добро пожаловать в чат!

{EMOJIS['party']} Приветствуем нового участника:
[id{user_id}|{user_info['full_name']}]

{EMOJIS['bell']} {welcome_message}

{EMOJIS['rules']} Обязательно ознакомьтесь с /правила
{EMOJIS['cmd']} Список всех команд: /CMD
{EMOJIS['info']} Ваша статистика: /профиль"""
        
        self.send_message(chat_id, message)
    
    def handle_bot_added(self, chat_id: int, user_id: int):
        """Обработчик добавления бота в чат"""
        settings = self.db.get_chat_settings(chat_id)
        
        if settings.get('bot_added_message_sent', 0) == 1:
            return
        
        self.db.set_bot_added_message_sent(chat_id, 1)
        
        message = f"""{EMOJIS['robot']} {EMOJIS['party']} Спасибо что добавили меня в чат!

{EMOJIS['warning']} {EMOJIS['mega']} ВАЖНО: Для полноценной работы мне необходимы права администратора!

{EMOJIS['gear']} Что нужно сделать:
1. Откройте настройки беседы
2. Перейдите в раздел \"Участники\"
3. Найдите меня в списке (Avrora Manager)
4. Назначьте администратором с правами:
   {EMOJIS['check']} Управление беседой
   {EMOJIS['check']} Удаление сообщений
   {EMOJIS['check']} Исключение участников

{EMOJIS['crown']} Только после этого будут работать команды:
{EMOJIS['mute']} /mute - ограничение на отправку сообщений
{EMOJIS['kick']} /kick - исключение из чата
{EMOJIS['no_entry']} /ban - бан пользователя
{EMOJIS['warning']} /warn - предупреждения

{EMOJIS['cmd']} Все команды: /CMD
{EMOJIS['rules']} Установка правил: /createpravila [текст]
{EMOJIS['welcome']} Приветствие: /приветствие [текст]

{EMOJIS['light']} Если права уже выданы - игнорируйте это сообщение."""
        
        self.send_message(chat_id, message)
    
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

{EMOJIS['crown']} Администраторы чата ({len(admin_list)}):
{chr(10).join(admin_list) if admin_list else f"{EMOJIS['cross']} Нет данных"}

{EMOJIS['cmd']} Используйте /CMD для списка команд"""
        
        self.send_message(chat_id, message)
    
    def handle_mute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split()
        if len(parts) < 1 and not reply_message:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование: 
1. /mute @user время причина
2. /mute время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
30m - 30 минут
2h - 2 часа
1d - 1 день
7d - 7 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/mute @durov 30m спам
/mute 1d флуд (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user, ID или ответьте на сообщение.")
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

{EMOJIS['warning']} Нарушитель не сможет писать в чат до окончания мута."""
        
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
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user или ответьте на сообщение.")
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

{EMOJIS['ban_hammer']} Результат: Автоматический бан на {settings.get('ban_duration', 10)} дней за превышение лимита предупреждений."""
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

{EMOJIS['light']} Внимание: При достижении {max_warns} предупреждений последует автоматический бан на {settings.get('ban_duration', 10)} дней."""
        
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
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user или ответьте на сообщение.")
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

{EMOJIS['light']} Пользователь может вернуться в чат по приглашению."""
            
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
1. /ban @user время причина
2. /ban время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
1d - 1 день
7d - 7 дней
30d - 30 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/ban @durov 10d спам
/ban 7d нарушение (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user, ID или ответьте на сообщение.")
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

{EMOJIS['warning']} Пользователь будет автоматически кикаться при попытке вернуться в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_self_kick(self, user_id: int, chat_id: int):
        try:
            self.vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )
        except Exception as e:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка при выходе: {str(e)}")
    
    def handle_unmute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование:
1. /размут @user
2. /размут (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/размут @durov
/размут (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, mute_until=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь размучен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Теперь пользователь может писать в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_unban(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['no_entry']} Использование:
1. /разбан @user
2. /разбан (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/разбан @durov
/разбан (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, ban_until=0, kicked=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь разбанен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь может вернуться в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_unwarn(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['warning']} Использование:
1. /снятьварн @user
2. /снятьварн (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/снятьварн @durov
/снятьварн (при ответе на сообщение)""")
            return
        
        if self.db.remove_warn(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} {EMOJIS['warning']} Снято предупреждение

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Одно предупреждение снято."""
        else:
            message = f"{EMOJIS['cross']} У пользователя нет активных предупреждений."
        
        self.send_message(chat_id, message)
    
    # ========== КОМАНДЫ ДЛЯ ВСЕХ ==========
    
    def handle_cmd(self, user_id: int, chat_id: int):
        """Команда /CMD - список всех команд"""
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        if is_admin:
            message = f"""{EMOJIS['cmd']} {EMOJIS['admin_cmd']} ПОЛНЫЙ СПИСОК КОМАНД

{EMOJIS['crown']} АДМИНИСТРАТОРСКИЕ КОМАНДЫ:

{EMOJIS['role']} • УПРАВЛЕНИЕ РОЛЯМИ:
/newrole [приоритет] [название] - создать роль
/deleterole [название] - удалить роль
/updaterole [старое] [приоритет] [новое] - обновить роль
/setrole @user [роль] - назначить роль
/removerole @user - снять роль
/roles - все доступные роли
/userrole @user - роль пользователя

{EMOJIS['gavel']} • НАКАЗАНИЯ:
/mute @user время причина - мут
/warn @user причина - предупреждение
/kick @user причина - кик
/ban @user время причина - бан
/размут @user - снять мут
/разбан @user - снять бан
/снятьварн @user - снять варн

{EMOJIS['gear']} • НАСТРОЙКИ:
/createpravila [текст] - установить правила
/приветствие [текст] - установить приветствие
/admin - статистика админа

{EMOJIS['user']} ОБЩИЕ КОМАНДЫ:

{EMOJIS['info']} /инфо [@user] - инфо о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 - создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - результаты
{EMOJIS['profile']} /профиль - ваш профиль
{EMOJIS['myrole']} /myrole - ваша роль
{EMOJIS['online']} /онлайн - кто онлайн
{EMOJIS['rules']} /правила - правила чата
{EMOJIS['exit']} /q - выйти из чата
{EMOJIS['cmd']} /CMD - этот список

{EMOJIS['clock']} Форматы времени: 30m, 2h, 1d, 7d, 0 - бессрочно

{EMOJIS['warning']} Для работы мута/бана/кика бот должен быть админом чата!"""
        else:
            message = f"""{EMOJIS['cmd']} {EMOJIS['user_cmd']} ДОСТУПНЫЕ КОМАНДЫ

{EMOJIS['info']} /инфо [@user] - информация о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 - создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - результаты опроса
{EMOJIS['profile']} /профиль - ваш профиль
{EMOJIS['myrole']} /myrole - ваша роль
{EMOJIS['online']} /онлайн - кто онлайн
{EMOJIS['rules']} /правила - правила чата
{EMOJIS['roles']} /roles - список всех ролей
{EMOJIS['userrole']} /userrole @user - роль пользователя
{EMOJIS['exit']} /q - выйти из чата
{EMOJIS['cmd']} /CMD - этот список

{EMOJIS['gavel']} СИСТЕМА НАКАЗАНИЙ:
{EMOJIS['warning']} 3 предупреждения = автоматический бан

{EMOJIS['light']} По вопросам обращайтесь к администраторам чата."""
        
        self.send_message(chat_id, message)
    
    def handle_info(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /инфо - информация о пользователе"""
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            target_id = user_id
        
        user_info = self.get_user_info(target_id)
        self.db.add_user(target_id, chat_id)
        user_data = self.db.get_user(target_id, chat_id)
        user_stats = self.db.get_user_stats(target_id, chat_id)
        
        is_admin = self.is_chat_admin(target_id, chat_id)
        user_role = self.db.get_user_role(target_id, chat_id)
        
        if user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        status = []
        if user_stats.get('muted'):
            status.append(f"{EMOJIS['mute']} В муте")
        if user_stats.get('banned'):
            status.append(f"{EMOJIS['no_entry']} Забанен")
        if user_stats.get('kicked'):
            status.append(f"{EMOJIS['kick']} Кикнут")
        if not status:
            status.append(f"{EMOJIS['green_circle']} Активен")
        
        join_date = user_stats.get('join_date', 'Неизвестно')
        if join_date and join_date != 'Неизвестно':
            try:
                dt = datetime.datetime.strptime(join_date[:19], "%Y-%m-%d %H:%M:%S")
                join_date = dt.strftime("%d.%m.%Y в %H:%M")
            except:
                pass
        
        self.db.cursor.execute(
            "SELECT reason, date, admin_id FROM warns_history WHERE user_id = ? AND chat_id = ? ORDER BY date DESC LIMIT 3",
            (target_id, chat_id)
        )
        recent_warns = self.db.cursor.fetchall()
        
        warns_history = ""
        if recent_warns:
            warns_history = f"\n{EMOJIS['warning']} Последние предупреждения:\n"
            for reason, warn_date, admin_id in recent_warns:
                admin_info = self.get_user_info(admin_id)
                dt = datetime.datetime.strptime(warn_date[:19], "%Y-%m-%d %H:%M:%S")
                formatted_date = dt.strftime("%d.%m.%Y")
                warns_history += f"  • {reason} ({formatted_date}, от [id{admin_id}|{admin_info['first_name']}])\n"
        
        message = f"""{EMOJIS['info']} Информация о пользователе

{EMOJIS['user']} ОСНОВНАЯ ИНФОРМАЦИЯ:
{EMOJIS['light']} Имя: {user_info['full_name']}
{EMOJIS['light']} ID: {target_id}
{role_text}
{EMOJIS['star']} Статус: {', '.join(status)}

{EMOJIS['chart']} СТАТИСТИКА:
{EMOJIS['warning']} Активные предупреждения: {user_stats.get('warns', 0)}
{EMOJIS['chart']} Всего предупреждений: {user_stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{warns_history}

{EMOJIS['cmd']} Полный список команд: /CMD"""
        
        self.send_message(chat_id, message)
    
    def handle_poll(self, user_id: int, chat_id: int, args: str):
        """Команда /опрос - создание опроса"""
        if not args.strip():
            self.send_message(chat_id, f"""{EMOJIS['poll']} Использование: /опрос [вопрос] | [вариант1] | [вариант2] | ...
            
{EMOJIS['light']} Примеры:
/опрос Какой день лучше для встречи? | Понедельник | Вторник | Среда
/опрос Любимый цвет? | Красный | Синий | Зеленый | Желтый

{EMOJIS['vote']} Голосовать: ответьте на сообщение с номером варианта (1, 2, 3...)
{EMOJIS['chart']} Результаты: /опросрезультаты""")
            return
        
        parts = args.split('|')
        if len(parts) < 3:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно указать вопрос и минимум 2 варианта ответа, разделенные |")
            return
        
        question = parts[0].strip()
        options = [opt.strip() for opt in parts[1:] if opt.strip()]
        
        if len(options) < 2:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно минимум 2 варианта ответа")
            return
        
        if len(options) > 10:
            self.send_message(chat_id, f"{EMOJIS['cross']} Максимум 10 вариантов ответа")
            return
        
        poll_id = self.db.create_poll(chat_id, user_id, question, options)
        user_info = self.get_user_info(user_id)
        
        options_text = ""
        for i, option in enumerate(options, 1):
            options_text += f"{i}. {option}\n"
        
        message = f"""{EMOJIS['poll']} Новый опрос #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['vote']} Варианты ответов:
{options_text}
{EMOJIS['user']} Создал: [id{user_id}|{user_info['full_name']}]

{EMOJIS['light']} Голосование: ответьте на это сообщение с номером варианта (1, 2, 3...)

{EMOJIS['chart']} Результаты: /опросрезультаты {poll_id}"""
        
        self.send_message(chat_id, message)
    
    def handle_poll_results(self, user_id: int, chat_id: int, args: str):
        """Команда /опросрезультаты - результаты опроса"""
        if not args.strip():
            active_polls = self.db.get_active_polls(chat_id)
            
            if not active_polls:
                self.send_message(chat_id, f"{EMOJIS['poll']} В этом чате нет активных опросов.\n{EMOJIS['light']} Создайте опрос: /опрос вопрос | вариант1 | вариант2")
                return
            
            message = f"{EMOJIS['poll']} Активные опросы:\n\n"
            for poll in active_polls[:5]:
                creator_info = self.get_user_info(poll['creator_id'])
                message += f"{EMOJIS['vote']} Опрос #{poll['poll_id']}: {poll['question'][:50]}...\n"
                message += f"   Создал: [id{poll['creator_id']}|{creator_info['first_name']}]\n"
                message += f"   /опросрезультаты {poll['poll_id']}\n\n"
            
            if len(active_polls) > 5:
                message += f"{EMOJIS['light']} ... и еще {len(active_polls) - 5} опросов"
            
            self.send_message(chat_id, message.strip())
            return
        
        try:
            poll_id = int(args.strip())
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Укажите номер опроса. Например: /опросрезультаты 1")
            return
        
        results = self.db.get_poll_results(poll_id)
        if not results:
            self.send_message(chat_id, f"{EMOJIS['cross']} Опрос #{poll_id} не найден")
            return
        
        question = results['question']
        options = results['options']
        vote_results = results['results']
        total_votes = results['total_votes']
        creator_info = self.get_user_info(results['creator_id'])
        
        results_text = ""
        for i, option in enumerate(options):
            votes = vote_results.get(i, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            bars = int(percentage / 10)
            progress_bar = "█" * bars + "░" * (10 - bars)
            
            results_text += f"{i+1}. {option}\n"
            results_text += f"   {progress_bar} {votes} голосов ({percentage:.1f}%)\n\n"
        
        message = f"""{EMOJIS['poll']} Результаты опроса #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['chart']} Результаты:
{results_text}
{EMOJIS['vote']} Всего голосов: {total_votes}
{EMOJIS['user']} Создал: [id{results['creator_id']}|{creator_info['full_name']}]

{EMOJIS['clock']} Создан: {results['created_at'][:19]}"""
        
        self.send_message(chat_id, message)
    
    def handle_poll_vote(self, user_id: int, chat_id: int, reply_message: Dict, vote_text: str):
        """Обработка голосования в опросе"""
        poll_match = re.search(r'Опрос #(\d+)', reply_message.get('text', ''))
        if not poll_match:
            return
        
        poll_id = int(poll_match.group(1))
        
        try:
            option_num = int(vote_text.strip())
            option_index = option_num - 1
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Пожалуйста], укажите номер варианта (1, 2, 3...)")
            return
        
        poll = self.db.get_poll(poll_id)
        if not poll or not poll['is_active']:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Этот опрос уже завершен]")
            return
        
        if option_index < 0 or option_index >= len(poll['options']):
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Неправильный номер варианта. Доступно: 1-{len(poll['options'])}]")
            return
        
        if self.db.vote_poll(poll_id, user_id, option_index):
            user_info = self.get_user_info(user_id)
            option_text = poll['options'][option_index]
            
            results = self.db.get_poll_results(poll_id)
            votes_for_option = results['results'].get(option_index, 0)
            total_votes = results['total_votes']
            percentage = (votes_for_option / total_votes * 100) if total_votes > 0 else 0
            
            message = f"""{EMOJIS['check']} [id{user_id}|{user_info['first_name']}], ваш голос учтен!

{EMOJIS['vote']} Вы выбрали: {option_text}
{EMOJIS['chart']} За этот вариант: {votes_for_option} голосов ({percentage:.1f}%)
{EMOJIS['light']} Всего голосов: {total_votes}

{EMOJIS['poll']} Результаты: /опросрезультаты {poll_id}"""
            
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Не удалось зарегистрировать ваш голос]")
    
    def handle_profile(self, user_id: int, chat_id: int):
        """Команда /профиль - профиль пользователя"""
        self.db.add_user(user_id, chat_id)
        stats = self.db.get_user_stats(user_id, chat_id)
        user_info = self.get_user_info(user_id)
        
        is_admin = self.is_chat_admin(user_id, chat_id)
        user_role = self.db.get_user_role(user_id, chat_id)
        
        if user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
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
{role_text}
{EMOJIS['warning']} Активные предупреждения: {stats.get('warns', 0)}
{EMOJIS['chart']} Всего получено варнов: {stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{EMOJIS['star']} Статус: {status}

{EMOJIS['info']} Подробная информация: /инфо
{EMOJIS['cmd']} Все команды: /CMD"""
        
        self.send_message(chat_id, message)
    
    def handle_online(self, user_id: int, chat_id: int):
        """Команда /онлайн - кто онлайн"""
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
    
    def check_punishments(self):
        """Проверка истечения наказаний"""
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
        """Обработка входящих сообщений"""
        try:
            message = event.object.message
            chat_id = event.chat_id
            user_id = message['from_id']
            text = message.get('text', '').strip()
            
            event_id = f"{chat_id}_{message.get('conversation_message_id', '')}"
            if event_id in self.processed_events:
                return
            self.processed_events.add(event_id)
            if len(self.processed_events) > 1000:
                self.processed_events.clear()
            
            print(f"{EMOJIS['robot']} Сообщение от {user_id} в чате {chat_id}: {text}")
            
            user_data = self.db.get_user(user_id, chat_id)
            
            if user_data and user_data['ban_until'] > 0:
                ban_active = True if user_data['ban_until'] == 0 else user_data['ban_until'] > time.time()
                
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
            
            if user_data and user_data['mute_until'] > 0:
                mute_active = True if user_data['mute_until'] == 0 else user_data['mute_until'] > time.time()
                
                if mute_active:
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
                
                if command == '/newrole':
                    self.handle_new_role(user_id, chat_id, args)
                elif command == '/deleterole':
                    self.handle_delete_role(user_id, chat_id, args)
                elif command == '/updaterole':
                    self.handle_update_role(user_id, chat_id, args)
                elif command == '/setrole':
                    self.handle_set_role(user_id, chat_id, args, reply_message)
                elif command == '/removerole':
                    self.handle_remove_role(user_id, chat_id, args, reply_message)
                elif command == '/roles':
                    self.handle_roles_list(user_id, chat_id)
                elif command == '/myrole':
                    self.handle_my_role(user_id, chat_id)
                elif command == '/userrole':
                    self.handle_user_role(user_id, chat_id, args, reply_message)
                elif command == '/admin':
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
                elif command in ['/правила', '/rules']:
                    self.handle_rules(user_id, chat_id)
                elif command in ['/размут', '/unmute']:
                    self.handle_unmute(user_id, chat_id, args, reply_message)
                elif command in ['/разбан', '/unban']:
                    self.handle_unban(user_id, chat_id, args, reply_message)
                elif command in ['/снятьварн', '/unwarn', '/снятьпред']:
                    self.handle_unwarn(user_id, chat_id, args, reply_message)
                elif command in ['/инфо', '/info']:
                    self.handle_info(user_id, chat_id, args, reply_message)
                elif command in ['/опрос', '/poll', '/голосование']:
                    self.handle_poll(user_id, chat_id, args)
                elif command in ['/опросрезультаты', '/pollresults', '/результаты']:
                    self.handle_poll_results(user_id, chat_id, args)
                elif command in ['/cmd', '/CMD', '/команды', '/help']:
                    self.handle_cmd(user_id, chat_id)
                elif command in ['/профиль', '/profile']:
                    self.handle_profile(user_id, chat_id)
                elif command in ['/онлайн', '/online']:
                    self.handle_online(user_id, chat_id)
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. Используйте /CMD для списка команд.")
            
            elif reply_message and reply_message.get('from_id') == -int(GROUP_ID):
                reply_text = reply_message.get('text', '')
                if 'Опрос #' in reply_text and text.strip().isdigit():
                    self.handle_poll_vote(user_id, chat_id, reply_message, text)
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка обработки сообщения: {e}")
    
    def run(self):
        """Запуск бота"""
        punishment_thread = threading.Thread(target=self.check_punishments, daemon=True)
        punishment_thread.start()
        
        print(f"\n{EMOJIS['robot']} Бот запущен и слушает сообщения...")
        print(f"{EMOJIS['crown']} Админы определяются автоматически")
        print(f"{EMOJIS['role']} Система ролей с приоритетами активна")
        print(f"{EMOJIS['welcome']} Приветствие работает (исправлено)")
        print(f"{EMOJIS['cmd']} Команда /CMD - полный список команд")
        print(f"{EMOJIS['gear']} База данных: avrora_bot.db\n")
        
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat:
                        self.process_message(event)
                
                elif event.type == VkBotEventType.CHAT_INVITE_USER:
                    if event.object.get('user_id') == -int(GROUP_ID):
                        chat_id = event.chat_id
                        inviter_id = event.object.get('from_id')
                        self.handle_bot_added(chat_id, inviter_id)
                
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
    {EMOJIS['role']} Система ролей с приоритетами
    {EMOJIS['cmd']} Полный список команд: /CMD
    {EMOJIS['robot']} ====================================
    """)
    
    print(f"{EMOJIS['light']} Проверяем права бота...")
    
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_TOKEN на валидный токен группы VK!")
    elif GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_ID на ID вашей группы (только цифры)!")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Бот остановлен пользователем")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Критическая ошибка: {e}")# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        if os.path.exists('avrora_bot.db'):
            print(f"{EMOJIS['gear']} Загружаем существующую базу данных...")
        
        self.conn = sqlite3.connect('avrora_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_default_roles()
    
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
                rules_text TEXT DEFAULT 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
                max_warns INTEGER DEFAULT 3,
                ban_duration INTEGER DEFAULT 10,
                bot_added_message_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица ролей (кастомные роли для чата)
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
        
        # Таблица назначенных ролей пользователям
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
        
        # Таблица опросов
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
        """Инициализация стандартных ролей"""
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
    
    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С РОЛЯМИ ==========
    
    def create_custom_role(self, chat_id: int, role_name: str, priority: int, created_by: int) -> bool:
        """Создание новой кастомной роли в чате"""
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
        """Удаление кастомной роли"""
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
        """Обновление кастомной роли"""
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
        """Получение всех ролей чата (стандартные + кастомные) с приоритетами"""
        roles = self.default_roles.copy()
        
        self.cursor.execute(
            "SELECT role_name, priority FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_roles = self.cursor.fetchall()
        for role_name, priority in custom_roles:
            roles[role_name] = priority
        
        sorted_roles = dict(sorted(roles.items(), key=lambda x: x[1], reverse=True))
        return sorted_roles
    
    def assign_role_to_user(self, user_id: int, chat_id: int, role_name: str, assigned_by: int) -> bool:
        """Назначение роли пользователю"""
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
        """Снятие роли с пользователя"""
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
        """Получение роли пользователя и её приоритета"""
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
        """Получение всех пользователей с ролями в чате"""
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
        
        user_roles.sort(key=lambda x: x[2], reverse=True)
        return user_roles
    
    def get_user_priority(self, user_id: int, chat_id: int, is_admin: bool = False) -> int:
        """Получение приоритета пользователя"""
        if is_admin:
            return 90
        
        user_role = self.get_user_role(user_id, chat_id)
        if user_role:
            return user_role[1]
        
        return 0
    
    def can_manage_role(self, admin_id: int, target_priority: int, chat_id: int, is_admin: bool = False) -> bool:
        """Проверка, может ли администратор управлять ролью с указанным приоритетом"""
        admin_priority = self.get_user_priority(admin_id, chat_id, is_admin)
        return admin_priority > target_priority
    
    # ========== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========
    
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
            settings = dict(zip(columns, row))
            if 'welcome_message' not in settings:
                settings['welcome_message'] = 'Добро пожаловать в чат!'
            if 'rules_text' not in settings:
                settings['rules_text'] = 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
            if 'max_warns' not in settings:
                settings['max_warns'] = 3
            if 'ban_duration' not in settings:
                settings['ban_duration'] = 10
            if 'bot_added_message_sent' not in settings:
                settings['bot_added_message_sent'] = 0
            return settings
        
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
            (chat_id, 
             default_settings['welcome_message'],
             default_settings['rules_text'],
             default_settings['max_warns'],
             default_settings['ban_duration'],
             default_settings['bot_added_message_sent'])
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
    
    def set_rules(self, chat_id: int, rules_text: str):
        return self.update_chat_settings(chat_id, rules_text=rules_text)
    
    def get_rules(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        if settings and 'rules_text' in settings:
            return settings['rules_text']
        return 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
    
    def set_welcome_message(self, chat_id: int, welcome_message: str):
        return self.update_chat_settings(chat_id, welcome_message=welcome_message)
    
    def get_welcome_message(self, chat_id: int) -> str:
        settings = self.get_chat_settings(chat_id)
        if settings and 'welcome_message' in settings:
            return settings['welcome_message']
        return 'Добро пожаловать в чат!'
    
    def set_bot_added_message_sent(self, chat_id: int, sent: int = 1):
        return self.update_chat_settings(chat_id, bot_added_message_sent=sent)
    
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
        role_name = user_role[0] if user_role else 'member'
        
        return {
            'user_id': user_id,
            'warns': user['warns'],
            'total_warns': total_warns,
            'muted': user['mute_until'] > time.time(),
            'banned': user['ban_until'] > time.time(),
            'kicked': user.get('kicked', 0),
            'role': role_name,
            'join_date': user['join_date']
        }
    
    # Методы для опросов
    def create_poll(self, chat_id: int, creator_id: int, question: str, options: List[str]) -> int:
        options_json = json.dumps(options, ensure_ascii=False)
        votes_json = json.dumps({}, ensure_ascii=False)
        
        self.cursor.execute(
            "INSERT INTO polls (chat_id, creator_id, question, options, votes) VALUES (?, ?, ?, ?, ?)",
            (chat_id, creator_id, question, options_json, votes_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_poll(self, poll_id: int) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT * FROM polls WHERE poll_id = ?",
            (poll_id,)
        )
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
        if str(user_id) in votes:
            del votes[str(user_id)]
        
        votes[str(user_id)] = option_index
        votes_json = json.dumps(votes, ensure_ascii=False)
        
        self.cursor.execute(
            "UPDATE polls SET votes = ? WHERE poll_id = ?",
            (votes_json, poll_id)
        )
        self.conn.commit()
        return True
    
    def get_poll_results(self, poll_id: int) -> Dict:
        poll = self.get_poll(poll_id)
        if not poll:
            return {}
        
        votes = poll['votes']
        options = poll['options']
        
        results = {i: 0 for i in range(len(options))}
        for vote in votes.values():
            if vote in results:
                results[vote] += 1
        
        total_votes = sum(results.values())
        
        return {
            'question': poll['question'],
            'options': options,
            'results': results,
            'total_votes': total_votes,
            'creator_id': poll['creator_id'],
            'created_at': poll['created_at']
        }
    
    def get_active_polls(self, chat_id: int) -> List[Dict]:
        self.cursor.execute(
            "SELECT poll_id, question, creator_id FROM polls WHERE chat_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (chat_id,)
        )
        rows = self.cursor.fetchall()
        return [{'poll_id': row[0], 'question': row[1], 'creator_id': row[2]} for row in rows]

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
        print(f"{EMOJIS['crown']} Админы определяются автоматически по правам в чате")
        print(f"{EMOJIS['role']} Новая система ролей с приоритетами активна!")
        print(f"{EMOJIS['cmd']} Команда /CMD - список всех команд")
    
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
        match = re.search(r'\[id(\d+)\|', text)
        if match:
            return int(match.group(1))
        
        match = re.search(r'@id(\d+)', text)
        if match:
            return int(match.group(1))
        
        if reply_message and 'from_id' in reply_message:
            return reply_message['from_id']
        
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
    
    # ========== КОМАНДЫ ДЛЯ РОЛЕЙ ==========
    
    def handle_new_role(self, user_id: int, chat_id: int, args: str):
        """Команда /newrole [приоритет] [название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование: /newrole [приоритет] [название]

{EMOJIS['priority']} Приоритет: 0 (низший) - 100 (высший)

{EMOJIS['light']} Примеры:
/newrole 50 Менеджер
/newrole 25 Помощник
/newrole 75 Старший Модератор""")
            return
        
        try:
            priority = int(parts[0])
            if priority < 0 or priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть от 0 до 100!")
                return
            
            role_name = parts[1].strip()
            if len(role_name) > 50:
                self.send_message(chat_id, f"{EMOJIS['cross']} Название роли слишком длинное (макс. 50 символов)")
                return
            
            if self.db.create_custom_role(chat_id, role_name, priority, user_id):
                admin_info = self.get_user_info(user_id)
                message = f"""{EMOJIS['check']} Роль успешно создана!

{EMOJIS['role']} Название: {role_name}
{EMOJIS['priority']} Приоритет: {priority}
{EMOJIS['police']} Создал: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь вы можете назначать эту роль:
/setrole @user {role_name}

{EMOJIS['list']} Посмотреть все роли: /roles""".strip()
                self.send_message(chat_id, message)
            else:
                self.send_message(chat_id, f"{EMOJIS['cross']} Роль с таким названием уже существует!")
                
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
    
    def handle_delete_role(self, user_id: int, chat_id: int, args: str):
        """Команда /deleterole [название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        role_name = args.strip()
        if not role_name:
            self.send_message(chat_id, f"{EMOJIS['role']} Использование: /deleterole [название]\n\n{EMOJIS['light']} Пример: /deleterole Менеджер")
            return
        
        if self.db.delete_custom_role(chat_id, role_name):
            admin_info = self.get_user_info(user_id)
            message = f"""{EMOJIS['check']} Роль удалена!

{EMOJIS['role']} Название: {role_name}
{EMOJIS['police']} Удалил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['warning']} Все пользователи лишились этой роли.""".strip()
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{role_name}' не найдена!")
    
    def handle_update_role(self, user_id: int, chat_id: int, args: str):
        """Команда /updaterole [старое название] [новый приоритет] [новое название]"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        # Пытаемся распарсить: сначала ищем 3 части
        parts = args.strip().split(maxsplit=2)
        if len(parts) < 3:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование: /updaterole [старое название] [новый приоритет] [новое название]

{EMOJIS['light']} Пример: /updaterole Менеджер 55 Старший Менеджер""")
            return
        
        old_name = parts[0].strip()
        
        try:
            new_priority = int(parts[1])
            if new_priority < 0 or new_priority > 100:
                self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть от 0 до 100!")
                return
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Приоритет должен быть числом!")
            return
        
        new_name = parts[2].strip()
        
        if self.db.update_custom_role(chat_id, old_name, new_name, new_priority):
            admin_info = self.get_user_info(user_id)
            message = f"""{EMOJIS['check']} Роль обновлена!

{EMOJIS['role']} Было: {old_name}
{EMOJIS['role']} Стало: {new_name}
{EMOJIS['priority']} Новый приоритет: {new_priority}
{EMOJIS['police']} Обновил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['list']} Посмотреть все роли: /roles""".strip()
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{old_name}' не найдена!")
    
    def handle_set_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /setrole [@user] [роль] - назначение роли пользователю"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        # Пытаемся определить цель и роль
        target_id = None
        role_name = None
        
        if reply_message:
            # Если есть ответ на сообщение, цель - автор того сообщения
            target_id = reply_message['from_id']
            role_name = args.strip()
        else:
            # Иначе ищем упоминание в тексте
            parts = args.strip().split(maxsplit=1)
            if len(parts) >= 2:
                target_id = self.extract_mention_or_id(parts[0])
                role_name = parts[1].strip()
        
        if not target_id or not role_name:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /setrole @user [роль]
2. /setrole [роль] (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/setrole @durov Администратор
/setrole Модератор (ответ на сообщение)""")
            return
        
        # Проверяем права: админ может назначать только роли с приоритетом ниже своего
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        if role_name not in all_roles:
            # Проверяем, может это стандартная роль?
            available_roles = "\n".join([f"  • {name} (приоритет {priority})" for name, priority in list(all_roles.items())[:10]])
            self.send_message(chat_id, f"{EMOJIS['cross']} Роль '{role_name}' не найдена!\n\n{EMOJIS['list']} Доступные роли:\n{available_roles}\n\n{EMOJIS['light']} Полный список: /roles")
            return
        
        target_priority = all_roles[role_name]
        is_admin_target = self.is_chat_admin(target_id, chat_id)
        
        if not self.db.can_manage_role(user_id, target_priority, chat_id, self.is_chat_admin(user_id, chat_id)):
            self.send_message(chat_id, f"{EMOJIS['cross']} Вы не можете назначить эту роль! Ваш приоритет должен быть выше.")
            return
        
        if is_admin_target:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя назначить роль администратору чата!")
            return
        
        if self.db.assign_role_to_user(target_id, chat_id, role_name, user_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} Роль назначена!

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['role']} Роль: {role_name}
{EMOJIS['priority']} Приоритет: {target_priority}
{EMOJIS['police']} Назначил: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Посмотреть все роли: /roles""".strip()
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не удалось назначить роль!")
    
    def handle_remove_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /removerole [@user] - снятие роли с пользователя"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = None
        
        if reply_message:
            target_id = reply_message['from_id']
        else:
            target_id = self.extract_mention_or_id(args.strip())
        
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /removerole @user
2. /removerole (при ответе на сообщение)

{EMOJIS['light']} Пример: /removerole @durov""")
            return
        
        user_role = self.db.get_user_role(target_id, chat_id)
        if not user_role:
            self.send_message(chat_id, f"{EMOJIS['cross']} У пользователя нет роли!")
            return
        
        role_name, priority = user_role
        is_admin_target = self.is_chat_admin(target_id, chat_id)
        
        if not self.db.can_manage_role(user_id, priority, chat_id, self.is_chat_admin(user_id, chat_id)):
            self.send_message(chat_id, f"{EMOJIS['cross']} Вы не можете снять эту роль! Ваш приоритет должен быть выше.")
            return
        
        if is_admin_target:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нельзя снять роль с администратора чата!")
            return
        
        if self.db.remove_user_role(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} Роль снята!

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['role']} Была роль: {role_name}
{EMOJIS['police']} Снял: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь без роли.""".strip()
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не удалось снять роль!")
    
    def handle_roles_list(self, user_id: int, chat_id: int):
        """Команда /roles - список всех доступных ролей"""
        all_roles = self.db.get_all_roles_with_priority(chat_id)
        
        if not all_roles:
            self.send_message(chat_id, f"{EMOJIS['role']} В этом чате пока нет ролей.\n{EMOJIS['light']} Администраторы могут создать роли командой /newrole")
            return
        
        # Разделяем на стандартные и кастомные
        custom_roles = []
        default_roles = []
        
        self.db.cursor.execute(
            "SELECT role_name FROM custom_roles WHERE chat_id = ?",
            (chat_id,)
        )
        custom_names = [row[0] for row in self.db.cursor.fetchall()]
        
        for name, priority in all_roles.items():
            if name in custom_names:
                custom_roles.append((name, priority))
            else:
                default_roles.append((name, priority))
        
        message = f"{EMOJIS['role']} {EMOJIS['list']} Все доступные роли (в скобках приоритет):\n\n"
        
        if custom_roles:
            message += f"{EMOJIS['star']} Кастомные роли:\n"
            for name, priority in custom_roles:
                message += f"  • {name} ({priority})\n"
            message += "\n"
        
        if default_roles:
            message += f"{EMOJIS['crown']} Стандартные роли:\n"
            for name, priority in default_roles[:10]:
                message += f"  • {name} ({priority})\n"
            
            if len(default_roles) > 10:
                message += f"  {EMOJIS['light']} ... и еще {len(default_roles) - 10} ролей\n"
        
        message += f"\n{EMOJIS['light']} Назначить роль: /setrole @user [название]\n{EMOJIS['light']} Посмотреть свою роль: /myrole"
        
        self.send_message(chat_id, message.strip())
    
    def handle_my_role(self, user_id: int, chat_id: int):
        """Команда /myrole - показать свою роль"""
        user_role = self.db.get_user_role(user_id, chat_id)
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        user_info = self.get_user_info(user_id)
        
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        elif user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        message = f"""{EMOJIS['profile']} Ваша роль

{EMOJIS['user']} Пользователь: [id{user_id}|{user_info['full_name']}]
{role_text}

{EMOJIS['list']} Посмотреть все роли: /roles""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_user_role(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /userrole [@user] - показать роль пользователя"""
        target_id = None
        
        if reply_message:
            target_id = reply_message['from_id']
        else:
            target_id = self.extract_mention_or_id(args.strip())
        
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['role']} Использование:
1. /userrole @user
2. /userrole (при ответе на сообщение)

{EMOJIS['light']} Пример: /userrole @durov""")
            return
        
        user_info = self.get_user_info(target_id)
        user_role = self.db.get_user_role(target_id, chat_id)
        is_admin = self.is_chat_admin(target_id, chat_id)
        
        if is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        elif user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        message = f"""{EMOJIS['profile']} Роль пользователя

{EMOJIS['user']} Пользователь: [id{target_id}|{user_info['full_name']}]
{role_text}

{EMOJIS['list']} Посмотреть все роли: /roles""".strip()
        
        self.send_message(chat_id, message)
    
    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    def handle_create_rules(self, user_id: int, chat_id: int, args: str):
        """Команда /createpravila - установка правил"""
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
        
        if self.db.set_rules(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['rules']} Правила чата обновлены!

{EMOJIS['scroll']} Новые правила установлены.
{EMOJIS['light']} Теперь участники могут посмотреть их командой /правила

{EMOJIS['book']} Для просмотра: /правила
{EMOJIS['pen']} Для редактирования: /createpravila [новый текст]"""
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении правил. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_welcome(self, user_id: int, chat_id: int, args: str):
        """Команда /приветствие - установка приветствия (ИСПРАВЛЕНО)"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        if not args.strip():
            current_welcome = self.db.get_welcome_message(chat_id)
            self.send_message(chat_id, f"""{EMOJIS['welcome']} Текущее приветствие: 
{current_welcome}

{EMOJIS['light']} Использование: /приветствие [текст]
Пример: /приветствие Добро пожаловать в наш чат! Правила: /правила""")
            return
        
        # Сохраняем приветствие в базу данных
        if self.db.set_welcome_message(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['welcome']} Приветствие обновлено!

{EMOJIS['scroll']} Новое приветствие:
{args.strip()}

{EMOJIS['light']} Теперь это сообщение будет показываться новым участникам при входе в чат."""
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении приветствия. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_rules(self, user_id: int, chat_id: int):
        """Команда /правила - просмотр правил"""
        rules_text = self.db.get_rules(chat_id)
        
        if not rules_text or rules_text == 'Правила еще не установлены. Администраторы могут установить их командой /createpravila':
            message = f"""{EMOJIS['rules']} Правила чата

{EMOJIS['warning']} Правила еще не установлены.

{EMOJIS['police']} Администраторы могут установить правила командой:
/createpravila [текст правил]

{EMOJIS['light']} Пример:
/createpravila 1. Не спамить
2. Уважать других участников
3. Не размещать рекламу"""
        else:
            message = f"""{EMOJIS['rules']} Правила чата:

{rules_text}

──────────────
{EMOJIS['gavel']} Система наказаний:
{EMOJIS['warning']} 1-2 предупреждения - предупреждение
{EMOJIS['no_entry']} 3 предупреждения - автоматический бан
{EMOJIS['police']} Администраторы могут выдавать муты и баны

{EMOJIS['light']} По всем вопросам обращайтесь к администраторам."""
        
        self.send_message(chat_id, message)
    
    def handle_new_chat_member(self, chat_id: int, user_id: int):
        """Обработчик новых участников (ИСПРАВЛЕНО)"""
        # Проверяем, не забанен ли пользователь
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
                    return
        
        # Добавляем пользователя в базу
        self.db.add_user(user_id, chat_id)
        
        # ПОЛУЧАЕМ ПРИВЕТСТВИЕ ИЗ БАЗЫ ДАННЫХ
        welcome_message = self.db.get_welcome_message(chat_id)
        user_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['welcome']} Добро пожаловать в чат!

{EMOJIS['party']} Приветствуем нового участника:
[id{user_id}|{user_info['full_name']}]

{EMOJIS['bell']} {welcome_message}

{EMOJIS['rules']} Обязательно ознакомьтесь с /правила
{EMOJIS['cmd']} Список всех команд: /CMD
{EMOJIS['info']} Ваша статистика: /профиль"""
        
        self.send_message(chat_id, message)
    
    def handle_bot_added(self, chat_id: int, user_id: int):
        """Обработчик добавления бота в чат"""
        settings = self.db.get_chat_settings(chat_id)
        
        # Проверяем, отправляли ли уже сообщение
        if settings.get('bot_added_message_sent', 0) == 1:
            return
        
        # Отмечаем, что сообщение отправлено
        self.db.set_bot_added_message_sent(chat_id, 1)
        
        message = f"""{EMOJIS['robot']} {EMOJIS['party']} Спасибо что добавили меня в чат!

{EMOJIS['warning']} {EMOJIS['mega']} ВАЖНО: Для полноценной работы мне необходимы права администратора!

{EMOJIS['gear']} Что нужно сделать:
1. Откройте настройки беседы
2. Перейдите в раздел \"Участники\"
3. Найдите меня в списке (Avrora Manager)
4. Назначьте администратором с правами:
   {EMOJIS['check']} Управление беседой
   {EMOJIS['check']} Удаление сообщений
   {EMOJIS['check']} Исключение участников

{EMOJIS['crown']} Только после этого будут работать команды:
{EMOJIS['mute']} /mute - ограничение на отправку сообщений
{EMOJIS['kick']} /kick - исключение из чата
{EMOJIS['no_entry']} /ban - бан пользователя
{EMOJIS['warning']} /warn - предупреждения

{EMOJIS['cmd']} Все команды: /CMD
{EMOJIS['rules']} Установка правил: /createpravila [текст]
{EMOJIS['welcome']} Приветствие: /приветствие [текст]

{EMOJIS['light']} Если права уже выданы - игнорируйте это сообщение."""
        
        self.send_message(chat_id, message)
    
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

{EMOJIS['crown']} Администраторы чата ({len(admin_list)}):
{chr(10).join(admin_list) if admin_list else f"{EMOJIS['cross']} Нет данных"}

{EMOJIS['cmd']} Используйте /CMD для списка команд"""
        
        self.send_message(chat_id, message)
    
    def handle_mute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        parts = args.strip().split()
        if len(parts) < 1 and not reply_message:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование: 
1. /mute @user время причина
2. /mute время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
30m - 30 минут
2h - 2 часа
1d - 1 день
7d - 7 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/mute @durov 30m спам
/mute 1d флуд (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user, ID или ответьте на сообщение.")
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

{EMOJIS['warning']} Нарушитель не сможет писать в чат до окончания мута."""
        
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
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user или ответьте на сообщение.")
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

{EMOJIS['ban_hammer']} Результат: Автоматический бан на {settings.get('ban_duration', 10)} дней за превышение лимита предупреждений."""
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

{EMOJIS['light']} Внимание: При достижении {max_warns} предупреждений последует автоматический бан на {settings.get('ban_duration', 10)} дней."""
        
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
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user или ответьте на сообщение.")
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

{EMOJIS['light']} Пользователь может вернуться в чат по приглашению."""
            
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
1. /ban @user время причина
2. /ban время причина (при ответе на сообщение)

{EMOJIS['clock']} Примеры времени:
1d - 1 день
7d - 7 дней
30d - 30 дней
0 или пусто - бессрочно

{EMOJIS['light']} Примеры:
/ban @durov 10d спам
/ban 7d нарушение (при ответе на сообщение)""")
            return
        
        target_id = None
        duration_idx = 0
        reason_idx = 1
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
            if parts:
                target_id = self.extract_mention_or_id(parts[0], reply_message)
                if target_id:
                    duration_idx = 1
                    reason_idx = 2
        
        if not target_id:
            self.send_message(chat_id, f"{EMOJIS['cross']} Не указан пользователь. Используйте @user, ID или ответьте на сообщение.")
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

{EMOJIS['warning']} Пользователь будет автоматически кикаться при попытке вернуться в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_self_kick(self, user_id: int, chat_id: int):
        try:
            self.vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )
        except Exception as e:
            self.send_message(chat_id, f"{EMOJIS['cross']} Ошибка при выходе: {str(e)}")
    
    def handle_unmute(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['mute']} Использование:
1. /размут @user
2. /размут (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/размут @durov
/размут (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, mute_until=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь размучен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Теперь пользователь может писать в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_unban(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['no_entry']} Использование:
1. /разбан @user
2. /разбан (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/разбан @durov
/разбан (при ответе на сообщение)""")
            return
        
        self.db.update_user(target_id, chat_id, ban_until=0, kicked=0)
        
        target_info = self.get_user_info(target_id)
        admin_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['check']} {EMOJIS['unlock']} Пользователь разбанен

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['light']} Теперь пользователь может вернуться в чат."""
        
        self.send_message(chat_id, message)
    
    def handle_unwarn(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            self.send_message(chat_id, f"""{EMOJIS['warning']} Использование:
1. /снятьварн @user
2. /снятьварн (при ответе на сообщение)

{EMOJIS['light']} Примеры:
/снятьварн @durov
/снятьварн (при ответе на сообщение)""")
            return
        
        if self.db.remove_warn(target_id, chat_id):
            target_info = self.get_user_info(target_id)
            admin_info = self.get_user_info(user_id)
            
            message = f"""{EMOJIS['check']} {EMOJIS['warning']} Снято предупреждение

{EMOJIS['user']} Пользователь: [id{target_id}|{target_info['full_name']}]
{EMOJIS['police']} Администратор: [id{user_id}|{admin_info['full_name']}]

{EMOJIS['check']} Одно предупреждение снято."""
        else:
            message = f"{EMOJIS['cross']} У пользователя нет активных предупреждений."
        
        self.send_message(chat_id, message)
    
    # ========== КОМАНДЫ ДЛЯ ВСЕХ ==========
    
    def handle_cmd(self, user_id: int, chat_id: int):
        """Команда /CMD - список всех команд"""
        is_admin = self.is_chat_admin(user_id, chat_id)
        
        if is_admin:
            message = f"""{EMOJIS['cmd']} {EMOJIS['admin_cmd']} ПОЛНЫЙ СПИСОК КОМАНД

{EMOJIS['crown']} АДМИНИСТРАТОРСКИЕ КОМАНДЫ:

{EMOJIS['role']} • УПРАВЛЕНИЕ РОЛЯМИ:
/newrole [приоритет] [название] - создать роль
/deleterole [название] - удалить роль
/updaterole [старое] [приоритет] [новое] - обновить роль
/setrole @user [роль] - назначить роль
/removerole @user - снять роль
/roles - все доступные роли
/userrole @user - роль пользователя

{EMOJIS['gavel']} • НАКАЗАНИЯ:
/mute @user время причина - мут
/warn @user причина - предупреждение
/kick @user причина - кик
/ban @user время причина - бан
/размут @user - снять мут
/разбан @user - снять бан
/снятьварн @user - снять варн

{EMOJIS['gear']} • НАСТРОЙКИ:
/createpravila [текст] - установить правила
/приветствие [текст] - установить приветствие
/admin - статистика админа

{EMOJIS['user']} ОБЩИЕ КОМАНДЫ:

{EMOJIS['info']} /инфо [@user] - инфо о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 - создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - результаты
{EMOJIS['profile']} /профиль - ваш профиль
{EMOJIS['myrole']} /myrole - ваша роль
{EMOJIS['online']} /онлайн - кто онлайн
{EMOJIS['rules']} /правила - правила чата
{EMOJIS['exit']} /q - выйти из чата
{EMOJIS['cmd']} /CMD - этот список

{EMOJIS['clock']} Форматы времени: 30m, 2h, 1d, 7d, 0 - бессрочно

{EMOJIS['warning']} Для работы мута/бана/кика бот должен быть админом чата!"""
        else:
            message = f"""{EMOJIS['cmd']} {EMOJIS['user_cmd']} ДОСТУПНЫЕ КОМАНДЫ

{EMOJIS['info']} /инфо [@user] - информация о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 - создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - результаты опроса
{EMOJIS['profile']} /профиль - ваш профиль
{EMOJIS['myrole']} /myrole - ваша роль
{EMOJIS['online']} /онлайн - кто онлайн
{EMOJIS['rules']} /правила - правила чата
{EMOJIS['roles']} /roles - список всех ролей
{EMOJIS['userrole']} /userrole @user - роль пользователя
{EMOJIS['exit']} /q - выйти из чата
{EMOJIS['cmd']} /CMD - этот список

{EMOJIS['gavel']} СИСТЕМА НАКАЗАНИЙ:
{EMOJIS['warning']} 3 предупреждения = автоматический бан

{EMOJIS['light']} По вопросам обращайтесь к администраторам чата."""
        
        self.send_message(chat_id, message)
    
    def handle_info(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /инфо - информация о пользователе"""
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            target_id = user_id
        
        user_info = self.get_user_info(target_id)
        self.db.add_user(target_id, chat_id)
        user_data = self.db.get_user(target_id, chat_id)
        user_stats = self.db.get_user_stats(target_id, chat_id)
        
        is_admin = self.is_chat_admin(target_id, chat_id)
        user_role = self.db.get_user_role(target_id, chat_id)
        
        if user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
        status = []
        if user_stats.get('muted'):
            status.append(f"{EMOJIS['mute']} В муте")
        if user_stats.get('banned'):
            status.append(f"{EMOJIS['no_entry']} Забанен")
        if user_stats.get('kicked'):
            status.append(f"{EMOJIS['kick']} Кикнут")
        if not status:
            status.append(f"{EMOJIS['green_circle']} Активен")
        
        join_date = user_stats.get('join_date', 'Неизвестно')
        if join_date and join_date != 'Неизвестно':
            try:
                dt = datetime.datetime.strptime(join_date[:19], "%Y-%m-%d %H:%M:%S")
                join_date = dt.strftime("%d.%m.%Y в %H:%M")
            except:
                pass
        
        self.db.cursor.execute(
            "SELECT reason, date, admin_id FROM warns_history WHERE user_id = ? AND chat_id = ? ORDER BY date DESC LIMIT 3",
            (target_id, chat_id)
        )
        recent_warns = self.db.cursor.fetchall()
        
        warns_history = ""
        if recent_warns:
            warns_history = f"\n{EMOJIS['warning']} Последние предупреждения:\n"
            for reason, warn_date, admin_id in recent_warns:
                admin_info = self.get_user_info(admin_id)
                dt = datetime.datetime.strptime(warn_date[:19], "%Y-%m-%d %H:%M:%S")
                formatted_date = dt.strftime("%d.%m.%Y")
                warns_history += f"  • {reason} ({formatted_date}, от [id{admin_id}|{admin_info['first_name']}])\n"
        
        message = f"""{EMOJIS['info']} Информация о пользователе

{EMOJIS['user']} ОСНОВНАЯ ИНФОРМАЦИЯ:
{EMOJIS['light']} Имя: {user_info['full_name']}
{EMOJIS['light']} ID: {target_id}
{role_text}
{EMOJIS['star']} Статус: {', '.join(status)}

{EMOJIS['chart']} СТАТИСТИКА:
{EMOJIS['warning']} Активные предупреждения: {user_stats.get('warns', 0)}
{EMOJIS['chart']} Всего предупреждений: {user_stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{warns_history}

{EMOJIS['cmd']} Полный список команд: /CMD"""
        
        self.send_message(chat_id, message)
    
    def handle_poll(self, user_id: int, chat_id: int, args: str):
        """Команда /опрос - создание опроса"""
        if not args.strip():
            self.send_message(chat_id, f"""{EMOJIS['poll']} Использование: /опрос [вопрос] | [вариант1] | [вариант2] | ...
            
{EMOJIS['light']} Примеры:
/опрос Какой день лучше для встречи? | Понедельник | Вторник | Среда
/опрос Любимый цвет? | Красный | Синий | Зеленый | Желтый

{EMOJIS['vote']} Голосовать: ответьте на сообщение с номером варианта (1, 2, 3...)
{EMOJIS['chart']} Результаты: /опросрезультаты""")
            return
        
        parts = args.split('|')
        if len(parts) < 3:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно указать вопрос и минимум 2 варианта ответа, разделенные |")
            return
        
        question = parts[0].strip()
        options = [opt.strip() for opt in parts[1:] if opt.strip()]
        
        if len(options) < 2:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно минимум 2 варианта ответа")
            return
        
        if len(options) > 10:
            self.send_message(chat_id, f"{EMOJIS['cross']} Максимум 10 вариантов ответа")
            return
        
        poll_id = self.db.create_poll(chat_id, user_id, question, options)
        user_info = self.get_user_info(user_id)
        
        options_text = ""
        for i, option in enumerate(options, 1):
            options_text += f"{i}. {option}\n"
        
        message = f"""{EMOJIS['poll']} Новый опрос #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['vote']} Варианты ответов:
{options_text}
{EMOJIS['user']} Создал: [id{user_id}|{user_info['full_name']}]

{EMOJIS['light']} Голосование: ответьте на это сообщение с номером варианта (1, 2, 3...)

{EMOJIS['chart']} Результаты: /опросрезультаты {poll_id}"""
        
        self.send_message(chat_id, message)
    
    def handle_poll_results(self, user_id: int, chat_id: int, args: str):
        """Команда /опросрезультаты - результаты опроса"""
        if not args.strip():
            active_polls = self.db.get_active_polls(chat_id)
            
            if not active_polls:
                self.send_message(chat_id, f"{EMOJIS['poll']} В этом чате нет активных опросов.\n{EMOJIS['light']} Создайте опрос: /опрос вопрос | вариант1 | вариант2")
                return
            
            message = f"{EMOJIS['poll']} Активные опросы:\n\n"
            for poll in active_polls[:5]:
                creator_info = self.get_user_info(poll['creator_id'])
                message += f"{EMOJIS['vote']} Опрос #{poll['poll_id']}: {poll['question'][:50]}...\n"
                message += f"   Создал: [id{poll['creator_id']}|{creator_info['first_name']}]\n"
                message += f"   /опросрезультаты {poll['poll_id']}\n\n"
            
            if len(active_polls) > 5:
                message += f"{EMOJIS['light']} ... и еще {len(active_polls) - 5} опросов"
            
            self.send_message(chat_id, message.strip())
            return
        
        try:
            poll_id = int(args.strip())
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Укажите номер опроса. Например: /опросрезультаты 1")
            return
        
        results = self.db.get_poll_results(poll_id)
        if not results:
            self.send_message(chat_id, f"{EMOJIS['cross']} Опрос #{poll_id} не найден")
            return
        
        question = results['question']
        options = results['options']
        vote_results = results['results']
        total_votes = results['total_votes']
        creator_info = self.get_user_info(results['creator_id'])
        
        results_text = ""
        for i, option in enumerate(options):
            votes = vote_results.get(i, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            bars = int(percentage / 10)
            progress_bar = "█" * bars + "░" * (10 - bars)
            
            results_text += f"{i+1}. {option}\n"
            results_text += f"   {progress_bar} {votes} голосов ({percentage:.1f}%)\n\n"
        
        message = f"""{EMOJIS['poll']} Результаты опроса #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['chart']} Результаты:
{results_text}
{EMOJIS['vote']} Всего голосов: {total_votes}
{EMOJIS['user']} Создал: [id{results['creator_id']}|{creator_info['full_name']}]

{EMOJIS['clock']} Создан: {results['created_at'][:19]}"""
        
        self.send_message(chat_id, message)
    
    def handle_poll_vote(self, user_id: int, chat_id: int, reply_message: Dict, vote_text: str):
        """Обработка голосования в опросе"""
        poll_match = re.search(r'Опрос #(\d+)', reply_message.get('text', ''))
        if not poll_match:
            return
        
        poll_id = int(poll_match.group(1))
        
        try:
            option_num = int(vote_text.strip())
            option_index = option_num - 1
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Пожалуйста], укажите номер варианта (1, 2, 3...)")
            return
        
        poll = self.db.get_poll(poll_id)
        if not poll or not poll['is_active']:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Этот опрос уже завершен]")
            return
        
        if option_index < 0 or option_index >= len(poll['options']):
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Неправильный номер варианта. Доступно: 1-{len(poll['options'])}]")
            return
        
        if self.db.vote_poll(poll_id, user_id, option_index):
            user_info = self.get_user_info(user_id)
            option_text = poll['options'][option_index]
            
            results = self.db.get_poll_results(poll_id)
            votes_for_option = results['results'].get(option_index, 0)
            total_votes = results['total_votes']
            percentage = (votes_for_option / total_votes * 100) if total_votes > 0 else 0
            
            message = f"""{EMOJIS['check']} [id{user_id}|{user_info['first_name']}], ваш голос учтен!

{EMOJIS['vote']} Вы выбрали: {option_text}
{EMOJIS['chart']} За этот вариант: {votes_for_option} голосов ({percentage:.1f}%)
{EMOJIS['light']} Всего голосов: {total_votes}

{EMOJIS['poll']} Результаты: /опросрезультаты {poll_id}"""
            
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Не удалось зарегистрировать ваш голос]")
    
    def handle_profile(self, user_id: int, chat_id: int):
        """Команда /профиль - профиль пользователя"""
        self.db.add_user(user_id, chat_id)
        stats = self.db.get_user_stats(user_id, chat_id)
        user_info = self.get_user_info(user_id)
        
        is_admin = self.is_chat_admin(user_id, chat_id)
        user_role = self.db.get_user_role(user_id, chat_id)
        
        if user_role:
            role_name, priority = user_role
            role_text = f"{EMOJIS['role']} {role_name} (приоритет {priority})"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор чата (приоритет 90)"
        else:
            role_text = f"{EMOJIS['user']} Обычный участник (приоритет 0)"
        
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
{role_text}
{EMOJIS['warning']} Активные предупреждения: {stats.get('warns', 0)}
{EMOJIS['chart']} Всего получено варнов: {stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{EMOJIS['star']} Статус: {status}

{EMOJIS['info']} Подробная информация: /инфо
{EMOJIS['cmd']} Все команды: /CMD"""
        
        self.send_message(chat_id, message)
    
    def handle_online(self, user_id: int, chat_id: int):
        """Команда /онлайн - кто онлайн"""
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
    
    def check_punishments(self):
        """Проверка истечения наказаний"""
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
        """Обработка входящих сообщений"""
        try:
            message = event.object.message
            chat_id = event.chat_id
            user_id = message['from_id']
            text = message.get('text', '').strip()
            
            # Проверяем, не обрабатывали ли мы уже это событие
            event_id = f"{chat_id}_{message.get('conversation_message_id', '')}"
            if event_id in self.processed_events:
                return
            self.processed_events.add(event_id)
            if len(self.processed_events) > 1000:
                self.processed_events.clear()
            
            print(f"{EMOJIS['robot']} Сообщение от {user_id} в чате {chat_id}: {text}")
            
            # Проверяем наказания
            user_data = self.db.get_user(user_id, chat_id)
            
            if user_data and user_data['ban_until'] > 0:
                ban_active = True if user_data['ban_until'] == 0 else user_data['ban_until'] > time.time()
                
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
            
            if user_data and user_data['mute_until'] > 0:
                mute_active = True if user_data['mute_until'] == 0 else user_data['mute_until'] > time.time()
                
                if mute_active:
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
            
            # Обработка команд
            if text.startswith('/'):
                command_parts = text.split(maxsplit=1)
                command = command_parts[0].lower()
                args = command_parts[1] if len(command_parts) > 1 else ""
                
                reply_message = message.get('reply_message')
                
                # Команды для ролей
                if command == '/newrole':
                    self.handle_new_role(user_id, chat_id, args)
                elif command == '/deleterole':
                    self.handle_delete_role(user_id, chat_id, args)
                elif command == '/updaterole':
                    self.handle_update_role(user_id, chat_id, args)
                elif command == '/setrole':
                    self.handle_set_role(user_id, chat_id, args, reply_message)
                elif command == '/removerole':
                    self.handle_remove_role(user_id, chat_id, args, reply_message)
                elif command == '/roles':
                    self.handle_roles_list(user_id, chat_id)
                elif command == '/myrole':
                    self.handle_my_role(user_id, chat_id)
                elif command == '/userrole':
                    self.handle_user_role(user_id, chat_id, args, reply_message)
                
                # Основные команды
                elif command == '/admin':
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
                elif command in ['/правила', '/rules']:
                    self.handle_rules(user_id, chat_id)
                elif command in ['/размут', '/unmute']:
                    self.handle_unmute(user_id, chat_id, args, reply_message)
                elif command in ['/разбан', '/unban']:
                    self.handle_unban(user_id, chat_id, args, reply_message)
                elif command in ['/снятьварн', '/unwarn', '/снятьпред']:
                    self.handle_unwarn(user_id, chat_id, args, reply_message)
                elif command in ['/инфо', '/info']:
                    self.handle_info(user_id, chat_id, args, reply_message)
                elif command in ['/опрос', '/poll', '/голосование']:
                    self.handle_poll(user_id, chat_id, args)
                elif command in ['/опросрезультаты', '/pollresults', '/результаты']:
                    self.handle_poll_results(user_id, chat_id, args)
                elif command in ['/cmd', '/CMD', '/команды', '/help']:
                    self.handle_cmd(user_id, chat_id)
                elif command in ['/профиль', '/profile']:
                    self.handle_profile(user_id, chat_id)
                elif command in ['/онлайн', '/online']:
                    self.handle_online(user_id, chat_id)
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. Используйте /CMD для списка команд.")
            
            elif reply_message and reply_message.get('from_id') == -int(GROUP_ID):
                reply_text = reply_message.get('text', '')
                if 'Опрос #' in reply_text and text.strip().isdigit():
                    self.handle_poll_vote(user_id, chat_id, reply_message, text)
            
            # Добавляем пользователя в базу
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка обработки сообщения: {e}")
    
    def run(self):
        """Запуск бота"""
        # Запускаем поток проверки наказаний
        punishment_thread = threading.Thread(target=self.check_punishments, daemon=True)
        punishment_thread.start()
        
        print(f"\n{EMOJIS['robot']} Бот запущен и слушает сообщения...")
        print(f"{EMOJIS['crown']} Админы определяются автоматически")
        print(f"{EMOJIS['role']} Система ролей с приоритетами активна")
        print(f"{EMOJIS['welcome']} Приветствие работает (исправлено)")
        print(f"{EMOJIS['cmd']} Команда /CMD - полный список команд")
        print(f"{EMOJIS['gear']} База данных: avrora_bot.db\n")
        
        for event in self.longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat:
                        self.process_message(event)
                
                elif event.type == VkBotEventType.CHAT_INVITE_USER:
                    if event.object.get('user_id') == -int(GROUP_ID):
                        # Бота добавили в чат
                        chat_id = event.chat_id
                        inviter_id = event.object.get('from_id')
                        self.handle_bot_added(chat_id, inviter_id)
                
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
    {EMOJIS['role']} Система ролей с приоритетами
    {EMOJIS['cmd']} Полный список команд: /CMD
    {EMOJIS['robot']} ====================================
    """)
    
    print(f"{EMOJIS['light']} Проверяем права бота...")
    
    if GROUP_TOKEN == "YOUR_VK_GROUP_TOKEN_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_TOKEN на валидный токен группы VK!")
    elif GROUP_ID == "YOUR_GROUP_ID_HERE":
        print(f"{EMOJIS['cross']} ОШИБКА: Замените GROUP_ID на ID вашей группы (только цифры)!")
    else:
        try:
            bot = VKAvroraBot()
            bot.run()
        except KeyboardInterrupt:
            print(f"\n{EMOJIS['exit']} Бот остановлен пользователем")
        except Exception as e:
            print(f"\n{EMOJIS['cross']} Критическая ошибка: {e}")    def __init__(self):
        if os.path.exists('avrora_bot.db'):
            # Не удаляем базу при каждом запуске
            print(f"{EMOJIS['gear']} Загружаем существующую базу данных...")
        
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
        
        # Таблица настроек чата - ФИКС: добавим недостающие колонки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_message TEXT DEFAULT 'Добро пожаловать в чат!',
                rules_text TEXT DEFAULT 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
                max_warns INTEGER DEFAULT 3,
                ban_duration INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Таблица опросов
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
        
        # Создаем начальные настройки для чатов, если их нет
        self.cursor.execute("SELECT chat_id FROM chat_settings")
        existing_chats = self.cursor.fetchall()
        
        self.conn.commit()
        print(f"{EMOJIS['check']} База данных инициализирована")
    
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
            settings = dict(zip(columns, row))
            # Проверяем, есть ли все необходимые поля
            if 'welcome_message' not in settings:
                settings['welcome_message'] = 'Добро пожаловать в чат!'
            if 'rules_text' not in settings:
                settings['rules_text'] = 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
            if 'max_warns' not in settings:
                settings['max_warns'] = 3
            if 'ban_duration' not in settings:
                settings['ban_duration'] = 10
            return settings
        
        # Создаем настройки по умолчанию, если их нет
        default_settings = {
            'chat_id': chat_id,
            'welcome_message': 'Добро пожаловать в чат!',
            'rules_text': 'Правила еще не установлены. Администраторы могут установить их командой /createpravila',
            'max_warns': 3,
            'ban_duration': 10
        }
        
        self.cursor.execute(
            "INSERT INTO chat_settings (chat_id, welcome_message, rules_text, max_warns, ban_duration) VALUES (?, ?, ?, ?, ?)",
            (chat_id, 
             default_settings['welcome_message'],
             default_settings['rules_text'],
             default_settings['max_warns'],
             default_settings['ban_duration'])
        )
        self.conn.commit()
        
        return self.get_chat_settings(chat_id)
    
    def update_chat_settings(self, chat_id: int, **kwargs):
        # Сначала убедимся, что настройки существуют
        self.get_chat_settings(chat_id)
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [chat_id]
        
        self.cursor.execute(
            f"UPDATE chat_settings SET {set_clause} WHERE chat_id = ?",
            values
        )
        self.conn.commit()
        return True
    
    def set_rules(self, chat_id: int, rules_text: str):
        """ФИКС: Правильно сохраняет правила"""
        return self.update_chat_settings(chat_id, rules_text=rules_text)
    
    def get_rules(self, chat_id: int) -> str:
        """ФИКС: Получает правила из настроек"""
        settings = self.get_chat_settings(chat_id)
        if settings and 'rules_text' in settings:
            return settings['rules_text']
        return 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
    
    def set_welcome_message(self, chat_id: int, welcome_message: str):
        """ФИКС: Сохраняет приветственное сообщение"""
        return self.update_chat_settings(chat_id, welcome_message=welcome_message)
    
    def get_welcome_message(self, chat_id: int) -> str:
        """ФИКС: Получает приветственное сообщение"""
        settings = self.get_chat_settings(chat_id)
        if settings and 'welcome_message' in settings:
            return settings['welcome_message']
        return 'Добро пожаловать в чат!'
    
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
    
    # Методы для опросов
    def create_poll(self, chat_id: int, creator_id: int, question: str, options: List[str]) -> int:
        options_json = json.dumps(options, ensure_ascii=False)
        votes_json = json.dumps({}, ensure_ascii=False)
        
        self.cursor.execute(
            "INSERT INTO polls (chat_id, creator_id, question, options, votes) VALUES (?, ?, ?, ?, ?)",
            (chat_id, creator_id, question, options_json, votes_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_poll(self, poll_id: int) -> Optional[Dict]:
        self.cursor.execute(
            "SELECT * FROM polls WHERE poll_id = ?",
            (poll_id,)
        )
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
        if str(user_id) in votes:
            del votes[str(user_id)]
        
        votes[str(user_id)] = option_index
        votes_json = json.dumps(votes, ensure_ascii=False)
        
        self.cursor.execute(
            "UPDATE polls SET votes = ? WHERE poll_id = ?",
            (votes_json, poll_id)
        )
        self.conn.commit()
        return True
    
    def get_poll_results(self, poll_id: int) -> Dict:
        poll = self.get_poll(poll_id)
        if not poll:
            return {}
        
        votes = poll['votes']
        options = poll['options']
        
        results = {i: 0 for i in range(len(options))}
        for vote in votes.values():
            if vote in results:
                results[vote] += 1
        
        total_votes = sum(results.values())
        
        return {
            'question': poll['question'],
            'options': options,
            'results': results,
            'total_votes': total_votes,
            'creator_id': poll['creator_id'],
            'created_at': poll['created_at']
        }
    
    def get_active_polls(self, chat_id: int) -> List[Dict]:
        self.cursor.execute(
            "SELECT poll_id, question, creator_id FROM polls WHERE chat_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (chat_id,)
        )
        rows = self.cursor.fetchall()
        return [{'poll_id': row[0], 'question': row[1], 'creator_id': row[2]} for row in rows]

# ========== ВК БОТ ==========
class VKAvroraBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=GROUP_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, GROUP_ID)
        self.db = Database()
        
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
        match = re.search(r'\[id(\d+)\|', text)
        if match:
            return int(match.group(1))
        
        match = re.search(r'@id(\d+)', text)
        if match:
            return int(match.group(1))
        
        if reply_message and 'from_id' in reply_message:
            return reply_message['from_id']
        
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
    
    # ========== ИСПРАВЛЕННЫЕ КОМАНДЫ ==========
    
    def handle_create_rules(self, user_id: int, chat_id: int, args: str):
        """ФИКСИРОВАННАЯ команда: /createpravila - установка правил"""
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
        
        # ФИКС: Правильно сохраняем правила
        if self.db.set_rules(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['rules']} Правила чата обновлены!

{EMOJIS['scroll']} Новые правила установлены.
{EMOJIS['light']} Теперь участники могут посмотреть их командой /правила

{EMOJIS['book']} Для просмотра: /правила
{EMOJIS['pen']} Для редактирования: /createpravila [новый текст]
""".strip()
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении правил. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_welcome(self, user_id: int, chat_id: int, args: str):
        """ФИКСИРОВАННАЯ команда: /приветствие - установка приветствия"""
        if not self.is_chat_admin(user_id, chat_id):
            self.send_message(chat_id, f"{EMOJIS['cross']} Эта команда только для администраторов чата!")
            return
        
        if not args.strip():
            current_welcome = self.db.get_welcome_message(chat_id)
            self.send_message(chat_id, f"""{EMOJIS['welcome']} Текущее приветствие: 
{current_welcome}

{EMOJIS['light']} Использование: /приветствие [текст]
Пример: /приветствие Добро пожаловать в наш чат! Правила: /правила""")
            return
        
        # ФИКС: Правильно сохраняем приветствие
        if self.db.set_welcome_message(chat_id, args.strip()):
            message = f"""{EMOJIS['check']} {EMOJIS['welcome']} Приветствие обновлено!

{EMOJIS['scroll']} Новое приветствие:
{args.strip()}

{EMOJIS['light']} Теперь это сообщение будет показываться новым участникам при входе в чат.
""".strip()
        else:
            message = f"{EMOJIS['cross']} Ошибка при сохранении приветствия. Попробуйте еще раз."
        
        self.send_message(chat_id, message)
    
    def handle_rules(self, user_id: int, chat_id: int):
        """ФИКСИРОВАННАЯ команда: /правила - просмотр правил"""
        rules_text = self.db.get_rules(chat_id)
        
        if not rules_text or rules_text == 'Правила еще не установлены. Администраторы могут установить их командой /createpravila':
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
    
    def handle_new_chat_member(self, chat_id: int, user_id: int):
        """ФИКСИРОВАННЫЙ обработчик: приветствие новых участников"""
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
        
        # ФИКС: Получаем приветствие из базы данных
        welcome_message = self.db.get_welcome_message(chat_id)
        user_info = self.get_user_info(user_id)
        
        message = f"""{EMOJIS['welcome']} Добро пожаловать!

{EMOJIS['party']} Приветствуем нового участника:
[id{user_id}|{user_info['full_name']}]

{EMOJIS['bell']} {welcome_message}

{EMOJIS['rules']} Обязательно ознакомьтесь с /правила
{EMOJIS['help']} Помощь по командам: /help
{EMOJIS['info']} Ваша статистика: /профиль
""".strip()
        self.send_message(chat_id, message)
    
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
        """ФИКС: Информация о настройках чата"""
        settings = self.db.get_chat_settings(chat_id)
        rules_text = settings.get('rules_text', '')
        has_rules = bool(rules_text.strip()) and rules_text != 'Правила еще не установлены. Администраторы могут установить их командой /createpravila'
        
        welcome_msg = settings.get('welcome_message', 'Добро пожаловать в чат!')
        if len(welcome_msg) > 50:
            welcome_msg = welcome_msg[:47] + "..."
        
        return f"""{EMOJIS['welcome']} Приветствие: {welcome_msg}
{EMOJIS['rules']} Правила: {'✅ Установлены' if has_rules else '❌ Не установлены'}
{EMOJIS['warning']} Макс. варнов: {settings.get('max_warns', 3)}
{EMOJIS['ban_hammer']} Длительность автобана: {settings.get('ban_duration', 10)} дней"""
    
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
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
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
        
        if reply_message:
            target_id = reply_message['from_id']
            if parts and (parts[0].startswith('@') or 'id' in parts[0] or parts[0].isdigit()):
                extracted_id = self.extract_mention_or_id(parts[0], reply_message)
                if extracted_id:
                    target_id = extracted_id
                    duration_idx = 1
                    reason_idx = 2
        else:
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
    
    # ========== НОВЫЕ КОМАНДЫ ==========
    
    def handle_info(self, user_id: int, chat_id: int, args: str, reply_message: Optional[Dict] = None):
        """Команда /инфо - информация о пользователе"""
        target_id = self.extract_mention_or_id(args, reply_message)
        if not target_id:
            target_id = user_id
        
        user_info = self.get_user_info(target_id)
        self.db.add_user(target_id, chat_id)
        user_data = self.db.get_user(target_id, chat_id)
        user_stats = self.db.get_user_stats(target_id, chat_id)
        
        is_admin = self.is_chat_admin(target_id, chat_id)
        db_role = self.db.get_role(target_id, chat_id)
        
        if db_role:
            role_text = f"{EMOJIS['crown']} {db_role}"
        elif is_admin:
            role_text = f"{EMOJIS['crown']} Администратор"
        else:
            role_text = f"{EMOJIS['user']} Участник"
        
        status = []
        if user_stats.get('muted'):
            status.append(f"{EMOJIS['mute']} В муте")
        if user_stats.get('banned'):
            status.append(f"{EMOJIS['no_entry']} Забанен")
        if user_stats.get('kicked'):
            status.append(f"{EMOJIS['kick']} Кикнут")
        if not status:
            status.append(f"{EMOJIS['green_circle']} Активен")
        
        join_date = user_stats.get('join_date', 'Неизвестно')
        if join_date and join_date != 'Неизвестно':
            try:
                dt = datetime.datetime.strptime(join_date[:19], "%Y-%m-%d %H:%M:%S")
                join_date = dt.strftime("%d.%m.%Y в %H:%M")
            except:
                pass
        
        self.db.cursor.execute(
            "SELECT reason, date, admin_id FROM warns_history WHERE user_id = ? AND chat_id = ? ORDER BY date DESC LIMIT 3",
            (target_id, chat_id)
        )
        recent_warns = self.db.cursor.fetchall()
        
        warns_history = ""
        if recent_warns:
            warns_history = f"\n{EMOJIS['warning']} Последние предупреждения:\n"
            for reason, warn_date, admin_id in recent_warns:
                admin_info = self.get_user_info(admin_id)
                dt = datetime.datetime.strptime(warn_date[:19], "%Y-%m-%d %H:%M:%S")
                formatted_date = dt.strftime("%d.%m.%Y")
                warns_history += f"  • {reason} ({formatted_date}, от [id{admin_id}|{admin_info['first_name']}])\n"
        
        message = f"""{EMOJIS['info']} Информация о пользователе

{EMOJIS['user']} Основная информация:
{EMOJIS['light']} Имя: {user_info['full_name']}
{EMOJIS['light']} ID: {target_id}
{EMOJIS['role']} Роль: {role_text}
{EMOJIS['star']} Статус: {', '.join(status)}

{EMOJIS['chart']} Статистика:
{EMOJIS['warning']} Активные предупреждения: {user_stats.get('warns', 0)}
{EMOJIS['chart']} Всего предупреждений: {user_stats.get('total_warns', 0)}
{EMOJIS['calendar']} В чате с: {join_date}
{warns_history}

{EMOJIS['light']} ID можно использовать для команд: /warn @id{target_id} причина
""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_poll(self, user_id: int, chat_id: int, args: str):
        """Команда /опрос - создание опроса"""
        if not args.strip():
            self.send_message(chat_id, f"""{EMOJIS['poll']} Использование: /опрос [вопрос] | [вариант1] | [вариант2] | ...
            
{EMOJIS['light']} Примеры:
/опрос Какой день лучше для встречи? | Понедельник | Вторник | Среда
/опрос Любимый цвет? | Красный | Синий | Зеленый | Желтый

{EMOJIS['vote']} После создания опроса участники могут голосовать, отвечая на сообщение с номером варианта (1, 2, 3...)
{EMOJIS['chart']} Чтобы увидеть результаты, используйте /опросрезультаты""")
            return
        
        parts = args.split('|')
        if len(parts) < 3:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно указать вопрос и минимум 2 варианта ответа, разделенные |")
            return
        
        question = parts[0].strip()
        options = [opt.strip() for opt in parts[1:] if opt.strip()]
        
        if len(options) < 2:
            self.send_message(chat_id, f"{EMOJIS['cross']} Нужно минимум 2 варианта ответа")
            return
        
        if len(options) > 10:
            self.send_message(chat_id, f"{EMOJIS['cross']} Максимум 10 вариантов ответа")
            return
        
        poll_id = self.db.create_poll(chat_id, user_id, question, options)
        user_info = self.get_user_info(user_id)
        
        options_text = ""
        for i, option in enumerate(options, 1):
            options_text += f"{i}. {option}\n"
        
        message = f"""{EMOJIS['poll']} Новый опрос #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['vote']} Варианты ответов:
{options_text}
{EMOJIS['user']} Создал: [id{user_id}|{user_info['full_name']}]

{EMOJIS['light']} Как голосовать:
1. Ответьте на это сообщение
2. Напишите номер выбранного варианта (1, 2, 3...)

{EMOJIS['chart']} Чтобы посмотреть результаты: /опросрезультаты {poll_id}
""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_poll_results(self, user_id: int, chat_id: int, args: str):
        """Команда /опросрезультаты - результаты опроса"""
        if not args.strip():
            active_polls = self.db.get_active_polls(chat_id)
            
            if not active_polls:
                self.send_message(chat_id, f"{EMOJIS['poll']} В этом чате нет активных опросов.\n{EMOJIS['light']} Создайте опрос командой: /опрос вопрос | вариант1 | вариант2")
                return
            
            message = f"{EMOJIS['poll']} Активные опросы:\n\n"
            for poll in active_polls[:5]:
                creator_info = self.get_user_info(poll['creator_id'])
                message += f"{EMOJIS['vote']} Опрос #{poll['poll_id']}: {poll['question'][:50]}...\n"
                message += f"   Создал: [id{poll['creator_id']}|{creator_info['first_name']}]\n"
                message += f"   /опросрезультаты {poll['poll_id']}\n\n"
            
            if len(active_polls) > 5:
                message += f"{EMOJIS['light']} ... и еще {len(active_polls) - 5} опросов"
            
            self.send_message(chat_id, message.strip())
            return
        
        try:
            poll_id = int(args.strip())
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} Укажите номер опроса. Например: /опросрезультаты 1")
            return
        
        results = self.db.get_poll_results(poll_id)
        if not results:
            self.send_message(chat_id, f"{EMOJIS['cross']} Опрос #{poll_id} не найден")
            return
        
        question = results['question']
        options = results['options']
        vote_results = results['results']
        total_votes = results['total_votes']
        creator_info = self.get_user_info(results['creator_id'])
        
        results_text = ""
        for i, option in enumerate(options):
            votes = vote_results.get(i, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            bars = int(percentage / 10)
            progress_bar = "█" * bars + "░" * (10 - bars)
            
            results_text += f"{i+1}. {option}\n"
            results_text += f"   {progress_bar} {votes} голосов ({percentage:.1f}%)\n\n"
        
        message = f"""{EMOJIS['poll']} Результаты опроса #{poll_id}

{EMOJIS['light']} Вопрос: {question}

{EMOJIS['chart']} Результаты:
{results_text}
{EMOJIS['vote']} Всего голосов: {total_votes}
{EMOJIS['user']} Создал: [id{results['creator_id']}|{creator_info['full_name']}]

{EMOJIS['clock']} Создан: {results['created_at'][:19]}
""".strip()
        
        self.send_message(chat_id, message)
    
    def handle_poll_vote(self, user_id: int, chat_id: int, reply_message: Dict, vote_text: str):
        """Обработка голосования в опросе"""
        poll_match = re.search(r'Опрос #(\d+)', reply_message.get('text', ''))
        if not poll_match:
            return
        
        poll_id = int(poll_match.group(1))
        
        try:
            option_num = int(vote_text.strip())
            option_index = option_num - 1
        except ValueError:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Пожалуйста], укажите номер варианта (1, 2, 3...)")
            return
        
        poll = self.db.get_poll(poll_id)
        if not poll or not poll['is_active']:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Этот опрос уже завершен]")
            return
        
        if option_index < 0 or option_index >= len(poll['options']):
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Неправильный номер варианта. Доступно: 1-{len(poll['options'])}]")
            return
        
        if self.db.vote_poll(poll_id, user_id, option_index):
            user_info = self.get_user_info(user_id)
            option_text = poll['options'][option_index]
            
            results = self.db.get_poll_results(poll_id)
            votes_for_option = results['results'].get(option_index, 0)
            total_votes = results['total_votes']
            percentage = (votes_for_option / total_votes * 100) if total_votes > 0 else 0
            
            message = f"""{EMOJIS['check']} [id{user_id}|{user_info['first_name']}], ваш голос учтен!

{EMOJIS['vote']} Вы выбрали: {option_text}
{EMOJIS['chart']} За этот вариант: {votes_for_option} голосов ({percentage:.1f}%)
{EMOJIS['light']} Всего голосов в опросе: {total_votes}

{EMOJIS['poll']} Чтобы посмотреть все результаты: /опросрезультаты {poll_id}
""".strip()
            
            self.send_message(chat_id, message)
        else:
            self.send_message(chat_id, f"{EMOJIS['cross']} [id{user_id}|Не удалось зарегистрировать ваш голос]")
    
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
{EMOJIS['info']} /инфо [@пользователь] - Информация о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 | ... - Создать опрос
{EMOJIS['chart']} /опросрезультаты [номер] - Результаты опроса
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
{EMOJIS['info']} /инфо [@пользователь] - Информация о пользователе
{EMOJIS['poll']} /опрос вопрос | вар1 | вар2 | ... - Создать опрос (если разрешено)
{EMOJIS['chart']} /опросрезультаты [номер] - Результаты опроса
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

{EMOJIS['info']} Подробная информация: /инфо
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
            
            if user_data and user_data['ban_until'] > 0:
                ban_active = True if user_data['ban_until'] == 0 else user_data['ban_until'] > time.time()
                
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
            
            if user_data and user_data['mute_until'] > 0:
                mute_active = True if user_data['mute_until'] == 0 else user_data['mute_until'] > time.time()
                
                if mute_active:
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
                
                elif command == '/инфо':
                    self.handle_info(user_id, chat_id, args, reply_message)
                
                elif command in ['/опрос', '/poll', '/голосование']:
                    self.handle_poll(user_id, chat_id, args)
                
                elif command in ['/опросрезультаты', '/pollresults', '/результаты']:
                    self.handle_poll_results(user_id, chat_id, args)
                
                elif command == '/help':
                    self.handle_help(user_id, chat_id)
                
                elif command == '/профиль':
                    self.handle_profile(user_id, chat_id)
                
                elif command == '/онлайн':
                    self.handle_online(user_id, chat_id)
                
                else:
                    self.send_message(chat_id, f"{EMOJIS['cross']} Неизвестная команда. Используйте /help для списка команд.")
            
            elif reply_message and reply_message.get('from_id') == -int(GROUP_ID):
                reply_text = reply_message.get('text', '')
                if 'Опрос #' in reply_text and text.strip().isdigit():
                    self.handle_poll_vote(user_id, chat_id, reply_message, text)
            
            self.db.add_user(user_id, chat_id)
            
        except Exception as e:
            print(f"{EMOJIS['cross']} Ошибка обработки сообщения: {e}")
    
    def run(self):
        punishment_thread = threading.Thread(target=self.check_punishments, daemon=True)
        punishment_thread.start()
        
        print(f"{EMOJIS['robot']} Бот запущен и слушает сообщения...")
        print(f"{EMOJIS['crown']} Админы определяются автоматически по правам в каждом чате")
        print(f"{EMOJIS['gear']} База данных: avrora_bot.db")
        print(f"{EMOJIS['info']} Новые команды: /инфо, /опрос, /опросрезультаты")
        print(f"{EMOJIS['check']} Исправлены баги с /createpravila и /приветствие")
        
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
