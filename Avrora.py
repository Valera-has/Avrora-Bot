import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import sqlite3
import time
import threading
import re
import random
from datetime import datetime, timedelta
import json

# === КОНФИГУРАЦИЯ ===
TOKEN = 'vk1.a.SOrelI5-sk-s6P3mwkBSMc671x5CjV-2lwYpH19HG12MFhNpwC8KLLfCVzfd54JrDBPb8NOxfm8pedKbbA4e-0f4X5T-h3aGfgqRJfhQwUx1N3QLf5Wv3SiECQP80st0zxRCP7_ZgSbOOvZchepgqZjoURASJ4IzpqJvCrxQiRrUL7R2m32oged5EV1QvYWG-tkagWs89rjM4k9QmG1QLg'
GROUP_ID = '236909937'
BOT_ID = -int(GROUP_ID)

# === ХРАНИЛИЩЕ МУТОВ ===
muted_users = {}

# === ХРАНИЛИЩЕ ИГРОВЫХ ПРЕДЛОЖЕНИЙ ===
game_offers = {}

# === СТАНДАРТНЫЕ РОЛИ ПО УМОЛЧАНИЮ ===
DEFAULT_ROLES = [
    {'name': 'Владелец', 'priority': 100, 'is_default': 1},
    {'name': 'Главный администратор', 'priority': 80, 'is_default': 1},
    {'name': 'Администратор', 'priority': 60, 'is_default': 1},
    {'name': 'Модератор', 'priority': 40, 'is_default': 1},
    {'name': 'Помощник', 'priority': 20, 'is_default': 1},
    {'name': 'Пользователь', 'priority': 0, 'is_default': 1}
]

# === НАСТРОЙКИ КОМАНД ПО УМОЛЧАНИЮ ===
DEFAULT_COMMAND_SETTINGS = {
    'kick': {'min_priority': 20, 'description': 'Кикнуть участника'},
    'ban': {'min_priority': 60, 'description': 'Забанить участника'},
    'mute': {'min_priority': 40, 'description': 'Замутить участника'},
    'silent': {'min_priority': 90, 'description': 'Режим тишины'},
    'setrole': {'min_priority': 60, 'description': 'Выдать роль'},
    'createrole': {'min_priority': 99, 'description': 'Создать роль'},
    'deleterole': {'min_priority': 99, 'description': 'Удалить роль'}
}

def parse_time(time_str):
    if time_str.endswith('m'):
        return int(time_str[:-1])
    elif time_str.endswith('h'):
        return int(time_str[:-1]) * 60
    elif time_str.endswith('d'):
        return int(time_str[:-1]) * 1440
    else:
        return int(time_str)

def check_muted_users():
    current_time = datetime.now()
    to_remove = []
    for user_id, data in muted_users.items():
        if data['end_time'] <= current_time:
            to_remove.append(user_id)
    for user_id in to_remove:
        del muted_users[user_id]
        print(f"✅ Мут пользователя {user_id} истек")

def delete_message(vk, peer_id, msg_id, conversation_message_id):
    try:
        if conversation_message_id:
            vk.messages.delete(
                conversation_message_ids=[conversation_message_id],
                peer_id=peer_id,
                delete_for_all=1
            )
        else:
            vk.messages.delete(
                message_ids=[msg_id],
                delete_for_all=1
            )
        return True
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")
        return False

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS greetings (
            chat_id INTEGER PRIMARY KEY,
            greeting_text TEXT,
            is_enabled INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER,
            chat_id INTEGER,
            ban_until TEXT,
            ban_reason TEXT,
            banned_by INTEGER,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kicked_users (
            user_id INTEGER,
            chat_id INTEGER,
            kicked_by INTEGER,
            kicked_reason TEXT,
            kicked_date TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            silent_mode INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS silent_settings (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            action_type TEXT DEFAULT 'kick'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role_name TEXT,
            priority INTEGER,
            is_default INTEGER DEFAULT 0,
            UNIQUE(chat_id, role_name),
            UNIQUE(chat_id, priority)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            chat_id INTEGER,
            role_name TEXT,
            assigned_by INTEGER,
            assigned_date TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_settings (
            chat_id INTEGER,
            command_name TEXT,
            min_priority INTEGER,
            description TEXT,
            PRIMARY KEY (chat_id, command_name)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_activation (
            chat_id INTEGER PRIMARY KEY,
            is_active INTEGER DEFAULT 0,
            activated_by INTEGER,
            activated_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для статистики сообщений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_stats (
            user_id INTEGER,
            chat_id INTEGER,
            message_count INTEGER DEFAULT 0,
            last_message_date TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # Таблица для валюты и игр
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id INTEGER,
            chat_id INTEGER,
            balance INTEGER DEFAULT 100,
            last_bonus_date TEXT,
            married_to INTEGER DEFAULT NULL,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def init_chat_roles(chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        for role in DEFAULT_ROLES:
            cursor.execute('SELECT COUNT(*) FROM roles WHERE chat_id = ? AND role_name = ?', 
                          (chat_id, role['name']))
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.execute('''
                    INSERT INTO roles (chat_id, role_name, priority, is_default)
                    VALUES (?, ?, ?, ?)
                ''', (chat_id, role['name'], role['priority'], role['is_default']))
                print(f"✅ Добавлена роль '{role['name']}' для чата {chat_id}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка инициализации ролей: {e}")
        return False

def init_command_settings(chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        for cmd_name, settings in DEFAULT_COMMAND_SETTINGS.items():
            cursor.execute('''
                INSERT OR IGNORE INTO command_settings (chat_id, command_name, min_priority, description)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, cmd_name, settings['min_priority'], settings['description']))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка инициализации команд: {e}")
        return False

def is_bot_activated(chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_active FROM bot_activation WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    except:
        return False

def activate_bot(chat_id, user_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO bot_activation (chat_id, is_active, activated_by, activated_date)
            VALUES (?, 1, ?, CURRENT_TIMESTAMP)
        ''', (chat_id, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_command_min_priority(chat_id, command_name):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT min_priority FROM command_settings WHERE chat_id = ? AND command_name = ?', 
                      (chat_id, command_name))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else DEFAULT_COMMAND_SETTINGS.get(command_name, {}).get('min_priority', 0)
    except:
        return DEFAULT_COMMAND_SETTINGS.get(command_name, {}).get('min_priority', 0)

def set_command_min_priority(chat_id, command_name, min_priority, user_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO command_settings (chat_id, command_name, min_priority, description)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, command_name, min_priority, DEFAULT_COMMAND_SETTINGS.get(command_name, {}).get('description', '')))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# === ФУНКЦИИ ДЛЯ ВАЛЮТЫ И ИГР ===
def get_balance(user_id, chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM user_balance WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        return 100
    except:
        return 100

def update_balance(user_id, chat_id, amount):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_balance (user_id, chat_id, balance)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                balance = balance + ?
        ''', (user_id, chat_id, amount, amount))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def set_balance(user_id, chat_id, amount):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_balance (user_id, chat_id, balance)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                balance = ?
        ''', (user_id, chat_id, amount, amount))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_daily_bonus(user_id, chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT last_bonus_date FROM user_balance WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if result and result[0] == today:
            conn.close()
            return False, 0
        
        bonus = random.randint(50, 200)
        
        cursor.execute('''
            INSERT INTO user_balance (user_id, chat_id, balance, last_bonus_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                balance = balance + ?,
                last_bonus_date = ?
        ''', (user_id, chat_id, bonus, today, bonus, today))
        
        conn.commit()
        conn.close()
        return True, bonus
    except:
        return False, 0

def get_married(user_id, chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT married_to FROM user_balance WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        return None
    except:
        return None

def set_married(user_id, chat_id, partner_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_balance SET married_to = ? WHERE user_id = ? AND chat_id = ?
        ''', (partner_id, user_id, chat_id))
        cursor.execute('''
            UPDATE user_balance SET married_to = ? WHERE user_id = ? AND chat_id = ?
        ''', (user_id, partner_id, chat_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def divorce(user_id, chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        partner = get_married(user_id, chat_id)
        if partner:
            cursor.execute('''
                UPDATE user_balance SET married_to = NULL WHERE user_id = ? AND chat_id = ?
            ''', (user_id, chat_id))
            cursor.execute('''
                UPDATE user_balance SET married_to = NULL WHERE user_id = ? AND chat_id = ?
            ''', (partner, chat_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_top_balance(chat_id, limit=10):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, balance FROM user_balance 
            WHERE chat_id = ? 
            ORDER BY balance DESC 
            LIMIT ?
        ''', (chat_id, limit))
        result = cursor.fetchall()
        conn.close()
        return result
    except:
        return []

def parse_bet_amount(amount_str):
    if amount_str.endswith('к'):
        return int(amount_str[:-1]) * 1000
    elif amount_str.endswith('кк'):
        return int(amount_str[:-2]) * 1000000
    else:
        return int(amount_str)

def format_amount(amount):
    if amount >= 1000000:
        return f"{amount//1000000}кк"
    elif amount >= 1000:
        return f"{amount//1000}к"
    return str(amount)

# === ФУНКЦИИ ДЛЯ СТАТИСТИКИ ===
def update_message_stats(user_id, chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO message_stats (user_id, chat_id, message_count, last_message_date)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                message_count = message_count + 1,
                last_message_date = ?
        ''', (user_id, chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка обновления статистики: {e}")
        return False

def get_user_stats(user_id, chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_count, last_message_date 
            FROM message_stats 
            WHERE user_id = ? AND chat_id = ?
        ''', (user_id, chat_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0], result[1]
        return 0, None
    except:
        return 0, None

def get_chat_stats(chat_id, limit=10):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, message_count 
            FROM message_stats 
            WHERE chat_id = ? 
            ORDER BY message_count DESC 
            LIMIT ?
        ''', (chat_id, limit))
        
        result = cursor.fetchall()
        conn.close()
        return result
    except:
        return []

def get_chat_members_count(vk, peer_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        return len(members.get('items', []))
    except:
        return 0

# === ФУНКЦИИ ДЛЯ РОЛЕЙ ===
def get_user_role(chat_id, user_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.role_name, r.priority
            FROM user_roles ur
            JOIN roles r ON ur.role_name = r.role_name AND ur.chat_id = r.chat_id
            WHERE ur.user_id = ? AND ur.chat_id = ?
        ''', (user_id, chat_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {'role_name': result[0], 'priority': result[1]}
        
        return {'role_name': 'Пользователь', 'priority': 0}
    except:
        return {'role_name': 'Пользователь', 'priority': 0}

def get_user_priority(chat_id, user_id):
    role = get_user_role(chat_id, user_id)
    return role['priority']

def can_use_command(chat_id, user_id, command_name):
    user_priority = get_user_priority(chat_id, user_id)
    min_priority = get_command_min_priority(chat_id, command_name)
    return user_priority >= min_priority

def can_manage(chat_id, admin_id, target_id):
    admin_priority = get_user_priority(chat_id, admin_id)
    target_priority = get_user_priority(chat_id, target_id)
    return admin_priority > target_priority

def set_user_role_by_priority(chat_id, user_id, priority, assigned_by):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT role_name FROM roles WHERE chat_id = ? AND priority = ?', (chat_id, priority))
        role = cursor.fetchone()
        
        if not role:
            conn.close()
            return False, f"❌ Роль с приоритетом {priority} не найдена"
        
        role_name = role[0]
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_roles (user_id, chat_id, role_name, assigned_by)
            VALUES (?, ?, ?, ?)
        ''', (user_id, chat_id, role_name, assigned_by))
        
        conn.commit()
        conn.close()
        return True, f"✅ Назначена роль '{role_name}' (приоритет {priority})"
    except Exception as e:
        return False, str(e)

def remove_user_role(chat_id, user_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_roles WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def create_custom_role(chat_id, role_name, priority):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT role_id FROM roles WHERE chat_id = ? AND role_name = ?', (chat_id, role_name))
        if cursor.fetchone():
            conn.close()
            return False, f"❌ Роль '{role_name}' уже существует"
        
        cursor.execute('SELECT role_id FROM roles WHERE chat_id = ? AND priority = ?', (chat_id, priority))
        if cursor.fetchone():
            conn.close()
            return False, f"❌ Роль с приоритетом {priority} уже существует"
        
        if priority > 100:
            priority = 100
        if priority < 0:
            priority = 0
        
        cursor.execute('''
            INSERT INTO roles (chat_id, role_name, priority, is_default)
            VALUES (?, ?, ?, 0)
        ''', (chat_id, role_name, priority))
        
        conn.commit()
        conn.close()
        return True, f"✅ Роль '{role_name}' создана (приоритет {priority})"
    except Exception as e:
        return False, str(e)

def delete_role_by_priority(chat_id, priority):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT role_name, is_default FROM roles WHERE chat_id = ? AND priority = ?', (chat_id, priority))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, f"❌ Роль с приоритетом {priority} не найдена"
        
        role_name, is_default = result
        
        if is_default == 1:
            conn.close()
            return False, f"❌ Нельзя удалить стандартную роль '{role_name}'"
        
        cursor.execute('DELETE FROM user_roles WHERE chat_id = ? AND role_name = ?', (chat_id, role_name))
        cursor.execute('DELETE FROM roles WHERE chat_id = ? AND priority = ?', (chat_id, priority))
        
        conn.commit()
        conn.close()
        return True, f"✅ Роль '{role_name}' удалена"
    except Exception as e:
        return False, str(e)

def get_all_roles(chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT role_name, priority, is_default 
            FROM roles 
            WHERE chat_id = ? 
            ORDER BY priority DESC
        ''', (chat_id,))
        
        roles = cursor.fetchall()
        conn.close()
        return roles
    except:
        return []

def get_chat_members_with_roles(chat_id):
    try:
        conn = sqlite3.connect('tom_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ur.user_id, r.role_name, r.priority
            FROM user_roles ur
            JOIN roles r ON ur.role_name = r.role_name AND ur.chat_id = r.chat_id
            WHERE ur.chat_id = ?
            ORDER BY r.priority DESC
        ''', (chat_id,))
        
        result = cursor.fetchall()
        conn.close()
        return result
    except:
        return []

def assign_all_roles_from_vk(vk, peer_id):
    """Назначает роли всем админам и владельцу на основе их прав в VK"""
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        owner_assigned = False
        
        for member in members['items']:
            member_id = member.get('member_id')
            if member_id and member_id > 0:
                if member.get('is_owner'):
                    set_user_role_by_priority(peer_id, member_id, 100, BOT_ID)
                    print(f"✅ Владельцу {member_id} назначена роль 100")
                    owner_assigned = True
                elif member.get('is_admin'):
                    current_priority = get_user_priority(peer_id, member_id)
                    if current_priority < 80:
                        set_user_role_by_priority(peer_id, member_id, 80, BOT_ID)
                        print(f"✅ Администратору {member_id} назначена роль 80")
        
        return owner_assigned
    except Exception as e:
        print(f"Ошибка назначения ролей: {e}")
        return False

def update_user_role(vk, peer_id, user_id):
    """Обновляет роль конкретного пользователя"""
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        for member in members['items']:
            if member.get('member_id') == user_id:
                if member.get('is_owner'):
                    set_user_role_by_priority(peer_id, user_id, 100, BOT_ID)
                    print(f"✅ Роль пользователя {user_id} обновлена до Владельца (100)")
                    return True
                elif member.get('is_admin'):
                    set_user_role_by_priority(peer_id, user_id, 80, BOT_ID)
                    print(f"✅ Роль пользователя {user_id} обновлена до Администратора (80)")
                    return True
                else:
                    # Если нет прав, снимаем роль
                    current_role = get_user_role(peer_id, user_id)
                    if current_role['priority'] > 0:
                        remove_user_role(peer_id, user_id)
                        print(f"⚠️ Роль пользователя {user_id} сброшена до Пользователя")
                    return True
        return False
    except Exception as e:
        print(f"Ошибка обновления роли: {e}")
        return False

# === ФУНКЦИИ ДЛЯ РЕЖИМА ТИШИНЫ ===
def get_silent_settings(chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT enabled, action_type FROM silent_settings WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0] == 1, result[1]
    return False, 'kick'

def set_silent_settings(chat_id, enabled, action_type='kick'):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO silent_settings (chat_id, enabled, action_type) 
        VALUES (?, ?, ?)
    ''', (chat_id, 1 if enabled else 0, action_type))
    conn.commit()
    conn.close()

def create_silent_keyboard():
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        label='🔨 Кикать',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': 'silent_action_kick'}
    )
    keyboard.add_callback_button(
        label='🔇 Удалять',
        color=VkKeyboardColor.SECONDARY,
        payload={'button': 'silent_action_mute'}
    )
    keyboard.add_line()
    keyboard.add_callback_button(
        label='❌ Отмена',
        color=VkKeyboardColor.NEGATIVE,
        payload={'button': 'silent_action_cancel'}
    )
    return keyboard

# === ФУНКЦИИ ДЛЯ ПРИВЕТСТВИЙ ===
def get_greeting(chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT greeting_text FROM greetings WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_greeting(chat_id, text):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO greetings (chat_id, greeting_text) VALUES (?, ?)', (chat_id, text))
    conn.commit()
    conn.close()

def remove_greeting(chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM greetings WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

# === ФУНКЦИИ ДЛЯ БАНА И КИКА ===
def ban_user(user_id, chat_id, days, reason, banned_by):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    
    ban_until = datetime.now() + timedelta(days=days)
    ban_until_str = ban_until.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT OR REPLACE INTO banned_users (user_id, chat_id, ban_until, ban_reason, banned_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, chat_id, ban_until_str, reason, banned_by))
    
    cursor.execute('DELETE FROM kicked_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    
    conn.commit()
    conn.close()
    return ban_until

def unban_user(user_id, chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banned_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    conn.commit()
    conn.close()

def is_user_banned(user_id, chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT ban_until, ban_reason FROM banned_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        ban_until = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        if ban_until > datetime.now():
            return True, result[1], ban_until
        else:
            unban_user(user_id, chat_id)
            return False, None, None
    return False, None, None

def kick_user(user_id, chat_id, kicked_by, reason):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO kicked_users (user_id, chat_id, kicked_by, kicked_reason)
        VALUES (?, ?, ?, ?)
    ''', (user_id, chat_id, kicked_by, reason))
    
    cursor.execute('DELETE FROM banned_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    
    conn.commit()
    conn.close()

def is_user_kicked(user_id, chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT kicked_by, kicked_reason FROM kicked_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None, result

def unkick_user(user_id, chat_id):
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM kicked_users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    conn.commit()
    conn.close()

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def sms(vk, peer_id, message, keyboard=None, reply_to=None):
    params = {
        'peer_id': peer_id,
        'message': message,
        'random_id': get_random_id()
    }
    if keyboard:
        params['keyboard'] = keyboard.get_keyboard()
    if reply_to:
        params['reply_to'] = reply_to
    try:
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def kick_from_chat(vk, peer_id, user_id):
    try:
        if peer_id > 2000000000:
            chat_id = peer_id - 2000000000
            vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
            return True
    except:
        pass
    return False

def is_chat_admin(vk, peer_id, user_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        for member in members['items']:
            if member.get('member_id') == user_id:
                return member.get('is_admin') or member.get('is_owner')
        return False
    except:
        return False

def get_user_name(vk, user_id):
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"Пользователь {user_id}"

def extract_user_id(text):
    match = re.search(r'\[id(\d+)\|', text)
    if match:
        return int(match.group(1))
    match = re.search(r'@id(\d+)', text)
    if match:
        return int(match.group(1))
    if text.isdigit():
        return int(text)
    return None

def create_exit_keyboard(user_id):
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        label='🔨 Кикнуть',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': f'kick_{user_id}'}
    )
    keyboard.add_callback_button(
        label='🚫 Забанить',
        color=VkKeyboardColor.NEGATIVE,
        payload={'button': f'ban_{user_id}'}
    )
    return keyboard

def create_ban_keyboard(user_id):
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        label='1 день',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': f'ban_days_1_{user_id}'}
    )
    keyboard.add_callback_button(
        label='3 дня',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': f'ban_days_3_{user_id}'}
    )
    keyboard.add_callback_button(
        label='7 дней',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': f'ban_days_7_{user_id}'}
    )
    keyboard.add_line()
    keyboard.add_callback_button(
        label='14 дней',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': f'ban_days_14_{user_id}'}
    )
    keyboard.add_callback_button(
        label='30 дней',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': f'ban_days_30_{user_id}'}
    )
    keyboard.add_line()
    keyboard.add_callback_button(
        label='❌ Отмена',
        color=VkKeyboardColor.NEGATIVE,
        payload={'button': f'ban_cancel_{user_id}'}
    )
    return keyboard

def create_start_keyboard():
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        label='🚀 Старт',
        color=VkKeyboardColor.POSITIVE,
        payload={'button': 'start'}
    )
    return keyboard

def create_rps_keyboard():
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        label='🗻 Камень',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': 'rps_rock'}
    )
    keyboard.add_callback_button(
        label='✂️ Ножницы',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': 'rps_scissors'}
    )
    keyboard.add_callback_button(
        label='📄 Бумага',
        color=VkKeyboardColor.PRIMARY,
        payload={'button': 'rps_paper'}
    )
    return keyboard

def create_offer_keyboard(offer_id, action):
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button(
        label='✅ Принять',
        color=VkKeyboardColor.POSITIVE,
        payload={'button': f'{action}_accept_{offer_id}'}
    )
    keyboard.add_callback_button(
        label='❌ Отказаться',
        color=VkKeyboardColor.NEGATIVE,
        payload={'button': f'{action}_decline_{offer_id}'}
    )
    return keyboard

# === КОМАНДЫ ===
def hello(vk, peer_id, user_id):
    """Активация бота"""
    
    # Проверяем, может ли пользователь активировать бота
    if not is_chat_admin(vk, peer_id, user_id):
        sms(vk, peer_id, "❌ Выдайте админку боту")
        return
    
    # Если бот уже активирован
    if is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот уже активирован!")
        return
    
    # Инициализация
    init_chat_roles(peer_id)
    init_command_settings(peer_id)
    
    # Назначаем роли всем админам и владельцу
    assign_all_roles_from_vk(vk, peer_id)
    
    # Обновляем роль активатора
    update_user_role(vk, peer_id, user_id)
    
    # Активируем бота
    activate_bot(peer_id, user_id)
    
    name = get_user_name(vk, user_id)
    user_role = get_user_role(peer_id, user_id)
    
    response = f"🤖 БОТ АКТИВИРОВАН!\n\n"
    response += f"👤 Активировал: [id{user_id}|{name}]\n"
    response += f"👑 Ваша роль: {user_role['role_name']} (приоритет: {user_role['priority']})\n"
    response += f"💰 Вам начислено 100 ТомКоинов!\n\n"
    response += "📋 Основные команды:\n"
    response += "🔹 /help — список всех команд\n"
    response += "🔹 /myrole — моя роль\n"
    response += "🔹 /roles — список ролей\n"
    response += "🔹 /stats — моя статистика\n"
    response += "🔹 /top — топ активных участников\n"
    response += "🔹 /balance — мой баланс\n"
    response += "🔹 /bonus — ежедневный бонус\n"
    response += "🔹 /casino [сумма] — сыграть в казино\n"
    response += "🔹 /rps [@user] [сумма] — камень-ножницы-бумага\n"
    response += "🔹 /marry [@user] — предложить брак\n"
    response += "🔹 /divorce — развод\n"
    response += "🔹 /transfer [@user] [сумма] — перевести ТомКоины\n\n"
    response += "💡 Введите /help для просмотра всех команд"
    
    sms(vk, peer_id, response)

def cmd_help(vk, peer_id, user_id):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован! Активируйте командой /start (только для админов)")
        return
    
    user_priority = get_user_priority(peer_id, user_id)
    
    # Получаем актуальные требования для каждой команды
    kick_req = get_command_min_priority(peer_id, 'kick')
    mute_req = get_command_min_priority(peer_id, 'mute')
    ban_req = get_command_min_priority(peer_id, 'ban')
    setrole_req = get_command_min_priority(peer_id, 'setrole')
    silent_req = get_command_min_priority(peer_id, 'silent')
    createrole_req = get_command_min_priority(peer_id, 'createrole')
    deleterole_req = get_command_min_priority(peer_id, 'deleterole')
    
    response = "📚 СПИСОК КОМАНД\n\n"
    
    response += "👥 Общие команды:\n"
    response += "• /help — это сообщение\n"
    response += "• /myrole — моя роль\n"
    response += "• /roles — список ролей\n"
    response += "• /members — участники с ролями\n"
    response += "• /stats — моя статистика сообщений\n"
    response += "• /top — топ активных участников\n"
    response += "• том — позвать бота\n\n"
    
    response += "💰 Экономические команды:\n"
    response += "• /balance — мой баланс ТомКоинов\n"
    response += "• /bonus — ежедневный бонус (50-200 ТК)\n"
    response += "• /transfer [@user] [сумма] — перевести ТомКоины\n"
    response += "• /casino [сумма] — сыграть в казино (x5 или проигрыш)\n"
    response += "• /rps [@user] [сумма] — камень-ножницы-бумага\n"
    response += "• /marry [@user] — предложить брак\n"
    response += "• /divorce — развестись\n"
    response += "• /topmoney — топ богачей\n\n"
    
    if user_priority >= kick_req:
        response += f"🔨 Команды модерации (нужен приоритет {kick_req}+):\n"
        response += "• /kick @user [причина] — кикнуть\n"
    if user_priority >= mute_req:
        response += "• /mute @user [время] [причина] — заглушить\n"
        response += "• /unmute @user — размутить\n\n"
    
    if user_priority >= ban_req:
        response += f"🛡️ Команды администрации (нужен приоритет {ban_req}+):\n"
        response += "• /ban @user [дни] [причина] — забанить\n"
        response += "• /unban @user — разбанить\n\n"
    
    if user_priority >= setrole_req:
        response += f"⚙️ Команды администрирования (нужен приоритет {setrole_req}+):\n"
        response += "• /setgreeting [текст] — приветствие\n"
        response += "• /delgreeting — удалить приветствие\n"
        response += "• /setrole @user [приоритет] — выдать роль\n"
        response += "• /unrole @user — снять роль\n\n"
    
    if user_priority >= silent_req or user_priority >= createrole_req or user_priority >= deleterole_req:
        response += "🔧 Команды управления:\n"
        if user_priority >= silent_req:
            response += f"• /silent — режим тишины (нужен приоритет {silent_req}+)\n"
        if user_priority >= createrole_req:
            response += f"• /createrole [приоритет] [название] — создать роль (нужен приоритет {createrole_req}+)\n"
        if user_priority >= deleterole_req:
            response += f"• /deleterole [приоритет] — удалить роль (нужен приоритет {deleterole_req}+)\n"
        if user_priority >= 99:
            response += "• /createcmd [команда] [приоритет] — изменить требования к команде\n"
        response += "\n"
    
    response += "📌 Примеры:\n"
    response += "/setrole @user 60\n"
    response += "/createrole 75 Зам.админа\n"
    response += "/mute @user 1h спам\n"
    response += "/createcmd mute 30\n"
    response += "/casino 1000\n"
    response += "/rps @user 500\n\n"
    response += "💡 Форматы суммы: 1к = 1000, 1кк = 1000000\n"
    response += "💡 Форматы времени: 30m, 2h, 1d"
    
    sms(vk, peer_id, response)

def cmd_balance(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    balance = get_balance(user_id, peer_id)
    married_to = get_married(user_id, peer_id)
    
    response = f"💰 БАЛАНС\n\n"
    response += f"👤 {get_user_name(vk, user_id)}\n"
    response += f"💵 ТомКоинов: {format_amount(balance)}\n"
    
    if married_to:
        partner_name = get_user_name(vk, married_to)
        response += f"💍 В браке с: [id{married_to}|{partner_name}]\n"
    else:
        response += f"💔 В браке: нет\n"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_bonus(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    success, bonus = get_daily_bonus(user_id, peer_id)
    
    if success:
        response = f"🎁 ЕЖЕДНЕВНЫЙ БОНУС!\n\n"
        response += f"💰 Вы получили {format_amount(bonus)} ТомКоинов!\n"
        response += f"💵 Ваш баланс: {format_amount(get_balance(user_id, peer_id))}"
        sms(vk, peer_id, response, reply_to=reply_to)
    else:
        response = f"❌ Вы уже получали бонус сегодня!\n"
        response += f"💡 Возвращайтесь завтра!"
        sms(vk, peer_id, response, reply_to=reply_to)

def cmd_casino(vk, peer_id, user_id, args, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not args:
        sms(vk, peer_id, "❌ /casino [сумма]\n/casino 1000\n/casino 5к", reply_to=reply_to)
        return
    
    try:
        bet = parse_bet_amount(args[0])
        if bet <= 0:
            raise ValueError
    except:
        sms(vk, peer_id, "❌ Неверная сумма!\nФорматы: 1000, 5к, 1кк", reply_to=reply_to)
        return
    
    balance = get_balance(user_id, peer_id)
    
    if bet > balance:
        sms(vk, peer_id, f"❌ Недостаточно средств! У вас {format_amount(balance)} ТК", reply_to=reply_to)
        return
    
    # Казино: шанс 40% на выигрыш x5
    win = random.random() < 0.4
    
    if win:
        win_amount = bet * 5
        update_balance(user_id, peer_id, win_amount)
        new_balance = get_balance(user_id, peer_id)
        
        response = f"🎰 КАЗИНО - ПОБЕДА!\n\n"
        response += f"🎉 Вы выиграли {format_amount(win_amount)} ТомКоинов!\n"
        response += f"💰 Ставка: {format_amount(bet)} ТК\n"
        response += f"💵 Итоговый баланс: {format_amount(new_balance)} ТК"
        sms(vk, peer_id, response, reply_to=reply_to)
    else:
        update_balance(user_id, peer_id, -bet)
        new_balance = get_balance(user_id, peer_id)
        
        response = f"🎰 КАЗИНО - ПРОИГРЫШ\n\n"
        response += f"😭 Вы проиграли {format_amount(bet)} ТомКоинов!\n"
        response += f"💵 Итоговый баланс: {format_amount(new_balance)} ТК"
        sms(vk, peer_id, response, reply_to=reply_to)

def cmd_transfer(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    target_id = None
    amount = None
    
    if target_from_reply:
        target_id = target_from_reply
        if args:
            try:
                amount = parse_bet_amount(args[0])
            except:
                pass
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    args.remove(arg)
                    if args:
                        try:
                            amount = parse_bet_amount(args[0])
                        except:
                            pass
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /transfer [@user] [сумма]\n/transfer @user 1000", reply_to=reply_to)
        return
    
    if target_id == user_id:
        sms(vk, peer_id, "❌ Нельзя перевести самому себе!", reply_to=reply_to)
        return
    
    if not amount or amount <= 0:
        sms(vk, peer_id, "❌ Неверная сумма!\nФорматы: 1000, 5к, 1кк", reply_to=reply_to)
        return
    
    balance = get_balance(user_id, peer_id)
    
    if amount > balance:
        sms(vk, peer_id, f"❌ Недостаточно средств! У вас {format_amount(balance)} ТК", reply_to=reply_to)
        return
    
    update_balance(user_id, peer_id, -amount)
    update_balance(target_id, peer_id, amount)
    
    target_name = get_user_name(vk, target_id)
    
    response = f"💸 ПЕРЕВОД\n\n"
    response += f"📤 Отправитель: [id{user_id}|{get_user_name(vk, user_id)}]\n"
    response += f"📥 Получатель: [id{target_id}|{target_name}]\n"
    response += f"💰 Сумма: {format_amount(amount)} ТК\n"
    response += f"💵 Ваш баланс: {format_amount(get_balance(user_id, peer_id))} ТК"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_rps(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    target_id = None
    amount = 0
    
    if target_from_reply:
        target_id = target_from_reply
        if args:
            try:
                amount = parse_bet_amount(args[0])
            except:
                pass
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    args.remove(arg)
                    if args:
                        try:
                            amount = parse_bet_amount(args[0])
                        except:
                            pass
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /rps [@user] [сумма]\n/rps @user 500", reply_to=reply_to)
        return
    
    if target_id == user_id:
        sms(vk, peer_id, "❌ Нельзя играть с самим собой!", reply_to=reply_to)
        return
    
    if amount < 0:
        sms(vk, peer_id, "❌ Сумма не может быть отрицательной!", reply_to=reply_to)
        return
    
    balance = get_balance(user_id, peer_id)
    target_balance = get_balance(target_id, peer_id)
    
    if amount > 0 and amount > balance:
        sms(vk, peer_id, f"❌ У вас недостаточно средств! У вас {format_amount(balance)} ТК", reply_to=reply_to)
        return
    
    if amount > 0 and amount > target_balance:
        sms(vk, peer_id, f"❌ У соперника недостаточно средств! У него {format_amount(target_balance)} ТК", reply_to=reply_to)
        return
    
    offer_id = random.randint(100000, 999999)
    game_offers[offer_id] = {
        'type': 'rps',
        'from_id': user_id,
        'to_id': target_id,
        'amount': amount,
        'peer_id': peer_id,
        'created': datetime.now()
    }
    
    target_name = get_user_name(vk, target_id)
    user_name = get_user_name(vk, user_id)
    
    if amount > 0:
        response = f"🎮 ИГРОВОЕ ПРЕДЛОЖЕНИЕ\n\n"
        response += f"👤 [id{user_id}|{user_name}] предлагает сыграть в КАМЕНЬ-НОЖНИЦЫ-БУМАГА\n"
        response += f"💰 Ставка: {format_amount(amount)} ТомКоинов\n"
        response += f"👥 Соперник: [id{target_id}|{target_name}]\n\n"
        response += f"Принять предложение?"
    else:
        response = f"🎮 ИГРОВОЕ ПРЕДЛОЖЕНИЕ\n\n"
        response += f"👤 [id{user_id}|{user_name}] предлагает сыграть в КАМЕНЬ-НОЖНИЦЫ-БУМАГА (без ставки)\n"
        response += f"👥 Соперник: [id{target_id}|{target_name}]\n\n"
        response += f"Принять предложение?"
    
    keyboard = create_offer_keyboard(offer_id, 'rps')
    sms(vk, peer_id, response, keyboard, reply_to=reply_to)

def cmd_marry(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    target_id = None
    
    if target_from_reply:
        target_id = target_from_reply
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /marry [@user]\n/marry @user", reply_to=reply_to)
        return
    
    if target_id == user_id:
        sms(vk, peer_id, "❌ Нельзя жениться на себе!", reply_to=reply_to)
        return
    
    # Проверяем, не женат ли уже
    if get_married(user_id, peer_id):
        sms(vk, peer_id, "❌ Вы уже в браке! Используйте /divorce для развода", reply_to=reply_to)
        return
    
    if get_married(target_id, peer_id):
        target_name = get_user_name(vk, target_id)
        sms(vk, peer_id, f"❌ [id{target_id}|{target_name}] уже в браке!", reply_to=reply_to)
        return
    
    offer_id = random.randint(100000, 999999)
    game_offers[offer_id] = {
        'type': 'marry',
        'from_id': user_id,
        'to_id': target_id,
        'peer_id': peer_id,
        'created': datetime.now()
    }
    
    target_name = get_user_name(vk, target_id)
    user_name = get_user_name(vk, user_id)
    
    response = f"💍 ПРЕДЛОЖЕНИЕ РУКИ И СЕРДЦА\n\n"
    response += f"👤 [id{user_id}|{user_name}] делает предложение [id{target_id}|{target_name}]\n\n"
    response += f"Принять предложение?"
    
    keyboard = create_offer_keyboard(offer_id, 'marry')
    sms(vk, peer_id, response, keyboard, reply_to=reply_to)

def cmd_divorce(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    married_to = get_married(user_id, peer_id)
    
    if not married_to:
        sms(vk, peer_id, "❌ Вы не состоите в браке!", reply_to=reply_to)
        return
    
    partner_name = get_user_name(vk, married_to)
    
    divorce(user_id, peer_id)
    
    response = f"💔 РАЗВОД\n\n"
    response += f"👤 [id{user_id}|{get_user_name(vk, user_id)}] развелся с [id{married_to}|{partner_name}]\n"
    response += f"💸 Брак расторгнут!"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_top_money(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    top_users = get_top_balance(peer_id, 10)
    
    if not top_users:
        sms(vk, peer_id, "💰 Топ богачей пока пуст!", reply_to=reply_to)
        return
    
    response = "🏆 ТОП БОГАЧЕЙ\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, (user_id_stat, balance) in enumerate(top_users[:10]):
        medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
        user_name = get_user_name(vk, user_id_stat)
        response += f"{medal} {user_name} — {format_amount(balance)} ТК\n"
    
    # Добавляем информацию о себе
    my_balance = get_balance(user_id, peer_id)
    position = None
    for i, (uid, _) in enumerate(top_users):
        if uid == user_id:
            position = i + 1
            break
    
    response += f"\n📌 Ваш баланс: {format_amount(my_balance)} ТК"
    if position:
        response += f" (место: {position})"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_stats(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    user_name = get_user_name(vk, user_id)
    user_role = get_user_role(peer_id, user_id)
    message_count, last_message = get_user_stats(user_id, peer_id)
    members_count = get_chat_members_count(vk, peer_id)
    balance = get_balance(user_id, peer_id)
    married_to = get_married(user_id, peer_id)
    
    response = f"📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ\n\n"
    response += f"👤 Имя: {user_name}\n"
    response += f"🎭 Роль: {user_role['role_name']} (приоритет: {user_role['priority']})\n"
    response += f"💬 Сообщений в чате: {message_count}\n"
    response += f"💰 ТомКоинов: {format_amount(balance)}\n"
    
    if married_to:
        partner_name = get_user_name(vk, married_to)
        response += f"💍 В браке с: [id{married_to}|{partner_name}]\n"
    else:
        response += f"💔 В браке: нет\n"
    
    if last_message:
        last_date = datetime.strptime(last_message, '%Y-%m-%d %H:%M:%S')
        response += f"🕐 Последнее сообщение: {last_date.strftime('%d.%m.%Y %H:%M')}\n"
    
    response += f"👥 Всего участников в чате: {members_count}\n\n"
    
    # Определяем уровень активности
    if message_count == 0:
        response += "📝 Статус: Новенький, пиши больше!"
    elif message_count < 50:
        response += "📝 Статус: Новичок"
    elif message_count < 200:
        response += "📝 Статус: Активный участник"
    elif message_count < 500:
        response += "📝 Статус: Опытный болтун"
    else:
        response += "📝 Статус: Легенда чата!"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_top(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    top_users = get_chat_stats(peer_id, 10)
    
    if not top_users:
        sms(vk, peer_id, "📊 Статистика пока пуста. Пишите сообщения, чтобы попасть в топ!", reply_to=reply_to)
        return
    
    response = "🏆 ТОП АКТИВНЫХ УЧАСТНИКОВ\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, (user_id_stat, count) in enumerate(top_users[:10]):
        medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
        user_name = get_user_name(vk, user_id_stat)
        response += f"{medal} {user_name} — {count} сообщ.\n"
    
    # Добавляем информацию о себе, если не в топе
    user_count, _ = get_user_stats(user_id, peer_id)
    if user_count > 0:
        position = None
        for i, (uid, cnt) in enumerate(top_users):
            if uid == user_id:
                position = i + 1
                break
        
        if position:
            response += f"\n📌 Ваша позиция: {position} место ({user_count} сообщ.)"
        else:
            response += f"\n📌 Вы не в топ-10, у вас {user_count} сообщений"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_createcmd(vk, peer_id, user_id, args):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!")
        return
    
    if get_user_priority(peer_id, user_id) < 99:
        sms(vk, peer_id, "❌ Недостаточно прав! Нужен приоритет 99+")
        return
    
    if len(args) < 2:
        sms(vk, peer_id, "❌ /createcmd [команда] [приоритет]\n/createcmd mute 30")
        return
    
    command_name = args[0].lower()
    
    if command_name not in DEFAULT_COMMAND_SETTINGS:
        sms(vk, peer_id, f"❌ Команда '{command_name}' не найдена\nДоступные: {', '.join(DEFAULT_COMMAND_SETTINGS.keys())}")
        return
    
    try:
        min_priority = int(args[1])
        if min_priority < 0:
            min_priority = 0
        if min_priority > 100:
            min_priority = 100
    except:
        sms(vk, peer_id, "❌ Приоритет должен быть числом!")
        return
    
    success = set_command_min_priority(peer_id, command_name, min_priority, user_id)
    
    if success:
        sms(vk, peer_id, f"✅ Команда '{command_name}' теперь требует приоритет {min_priority}+")
    else:
        sms(vk, peer_id, "❌ Ошибка при обновлении команды")

def tom(vk, peer_id):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован! Активируйте командой /start (только для админов)")
    else:
        sms(vk, peer_id, "Звал?")

def cmd_silent(vk, peer_id, user_id):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!")
        return
    
    if not can_use_command(peer_id, user_id, 'silent'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'silent')}+")
        return
    
    silent_enabled, silent_action = get_silent_settings(peer_id)
    
    if silent_enabled:
        set_silent_settings(peer_id, False, 'kick')
        keyboard = VkKeyboard(inline=True)
        keyboard.add_callback_button(
            label='🔇 Включить',
            color=VkKeyboardColor.PRIMARY,
            payload={'button': 'silent_turn_on'}
        )
        sms(vk, peer_id, "🔊 Режим тишины ВЫКЛЮЧЕН", keyboard)
    else:
        keyboard = create_silent_keyboard()
        sms(vk, peer_id, "🔇 Включить режим тишины?", keyboard)

def cmd_setrole(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'setrole'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'setrole')}+", reply_to=reply_to)
        return
    
    target_id = None
    priority = None
    
    if target_from_reply:
        target_id = target_from_reply
        if args:
            try:
                priority = int(args[0])
            except:
                pass
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    args.remove(arg)
                    if args:
                        try:
                            priority = int(args[0])
                        except:
                            pass
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /setrole @user [приоритет]", reply_to=reply_to)
        return
    
    if priority is None:
        sms(vk, peer_id, "❌ /setrole @user [приоритет]\n/setrole @user 60", reply_to=reply_to)
        return
    
    admin_priority = get_user_priority(peer_id, user_id)
    target_priority = get_user_priority(peer_id, target_id)
    
    conn = sqlite3.connect('tom_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT role_name FROM roles WHERE chat_id = ? AND priority = ?', (peer_id, priority))
    role = cursor.fetchone()
    conn.close()
    
    if not role:
        sms(vk, peer_id, f"❌ Приоритет {priority} не найден\n/roles", reply_to=reply_to)
        return
    
    if admin_priority <= priority:
        sms(vk, peer_id, f"❌ Нельзя назначить роль с приоритетом {priority}, ваш: {admin_priority}", reply_to=reply_to)
        return
    
    if admin_priority <= target_priority:
        sms(vk, peer_id, f"❌ Нельзя управлять (приоритет {target_priority})", reply_to=reply_to)
        return
    
    success, message = set_user_role_by_priority(peer_id, target_id, priority, user_id)
    
    if success:
        target_name = get_user_name(vk, target_id)
        sms(vk, peer_id, f"{message}\n👤 [id{target_id}|{target_name}]", reply_to=reply_to)
    else:
        sms(vk, peer_id, message, reply_to=reply_to)

def cmd_unrole(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'setrole'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'setrole')}+", reply_to=reply_to)
        return
    
    target_id = None
    
    if target_from_reply:
        target_id = target_from_reply
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /unrole @user", reply_to=reply_to)
        return
    
    admin_priority = get_user_priority(peer_id, user_id)
    target_priority = get_user_priority(peer_id, target_id)
    
    if admin_priority <= target_priority:
        sms(vk, peer_id, f"❌ Нельзя управлять (приоритет {target_priority})", reply_to=reply_to)
        return
    
    user_role = get_user_role(peer_id, target_id)
    
    if user_role['role_name'] == 'Пользователь':
        sms(vk, peer_id, f"❌ Нет роли", reply_to=reply_to)
        return
    
    remove_user_role(peer_id, target_id)
    target_name = get_user_name(vk, target_id)
    sms(vk, peer_id, f"✅ С [id{target_id}|{target_name}] снята '{user_role['role_name']}'", reply_to=reply_to)

def cmd_createrole(vk, peer_id, user_id, args, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'createrole'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'createrole')}+", reply_to=reply_to)
        return
    
    if len(args) < 2:
        sms(vk, peer_id, "❌ /createrole [приоритет] [название]\n/createrole 75 Зам.админа", reply_to=reply_to)
        return
    
    try:
        priority = int(args[0])
    except:
        sms(vk, peer_id, "❌ Приоритет — число!", reply_to=reply_to)
        return
    
    role_name = ' '.join(args[1:])
    
    admin_priority = get_user_priority(peer_id, user_id)
    
    if admin_priority < 99:
        sms(vk, peer_id, f"❌ Нужен приоритет 99+, ваш: {admin_priority}", reply_to=reply_to)
        return
    
    success, message = create_custom_role(peer_id, role_name, priority)
    sms(vk, peer_id, message, reply_to=reply_to)

def cmd_deleterole(vk, peer_id, user_id, args, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'deleterole'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'deleterole')}+", reply_to=reply_to)
        return
    
    if len(args) < 1:
        sms(vk, peer_id, "❌ /deleterole [приоритет]\n/deleterole 75", reply_to=reply_to)
        return
    
    try:
        priority = int(args[0])
    except:
        sms(vk, peer_id, "❌ Приоритет — число!", reply_to=reply_to)
        return
    
    admin_priority = get_user_priority(peer_id, user_id)
    
    if admin_priority < 99:
        sms(vk, peer_id, f"❌ Нужен приоритет 99+, ваш: {admin_priority}", reply_to=reply_to)
        return
    
    success, message = delete_role_by_priority(peer_id, priority)
    sms(vk, peer_id, message, reply_to=reply_to)

def cmd_roles(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    roles = get_all_roles(peer_id)
    
    if not roles:
        sms(vk, peer_id, "❌ Ролей нет", reply_to=reply_to)
        return
    
    response = "📋 СПИСОК РОЛЕЙ:\n\n"
    
    for role_name, priority, is_default in roles:
        marker = "⭐ " if is_default else "🔹 "
        response += f"{marker}{role_name} — {priority}\n"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_myrole(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    # Обновляем роль пользователя перед показом
    update_user_role(vk, peer_id, user_id)
    
    user_role = get_user_role(peer_id, user_id)
    user_name = get_user_name(vk, user_id)
    
    response = f"👤 {user_name}\n\n"
    response += f"🎭 Роль: {user_role['role_name']}\n"
    response += f"📊 Приоритет: {user_role['priority']}\n\n"
    
    response += "📋 Доступные команды:\n"
    if user_role['priority'] >= get_command_min_priority(peer_id, 'kick'):
        response += "✓ /kick — кикнуть\n"
    if user_role['priority'] >= get_command_min_priority(peer_id, 'mute'):
        response += "✓ /mute — замутить\n"
    if user_role['priority'] >= get_command_min_priority(peer_id, 'ban'):
        response += "✓ /ban — забанить\n"
    if user_role['priority'] >= get_command_min_priority(peer_id, 'setrole'):
        response += "✓ /setrole — выдать роль\n"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_members(vk, peer_id, user_id, reply_to):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    members = get_chat_members_with_roles(peer_id)
    
    if not members:
        sms(vk, peer_id, "❌ Нет участников с ролями", reply_to=reply_to)
        return
    
    response = "👥 УЧАСТНИКИ С РОЛЯМИ:\n\n"
    for member_id, role_name, priority in members[:20]:
        member_name = get_user_name(vk, member_id)
        response += f"• {member_name}\n  🎭 {role_name} ({priority})\n\n"
    
    if len(members) > 20:
        response += f"\n📌 И еще {len(members)-20} участников"
    
    sms(vk, peer_id, response, reply_to=reply_to)

def cmd_kick(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'kick'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'kick')}+", reply_to=reply_to)
        return
    
    target_id = None
    reason = ""
    
    if target_from_reply:
        target_id = target_from_reply
        reason = ' '.join(args) if args else "Не указана"
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    args.remove(arg)
                    reason = ' '.join(args) if args else "Не указана"
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /kick @user [причина]", reply_to=reply_to)
        return
    
    if target_id == user_id:
        sms(vk, peer_id, "❌ Нельзя кикнуть себя", reply_to=reply_to)
        return
    
    if not can_manage(peer_id, user_id, target_id):
        target_priority = get_user_priority(peer_id, target_id)
        sms(vk, peer_id, f"❌ Нельзя (приоритет {target_priority})", reply_to=reply_to)
        return
    
    target_name = get_user_name(vk, target_id)
    kick_user(target_id, peer_id, user_id, reason)
    
    if kick_from_chat(vk, peer_id, target_id):
        sms(vk, peer_id, f"👢 [id{target_id}|{target_name}] кикнут\n📝 Причина: {reason}", reply_to=reply_to)

def cmd_ban(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'ban'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'ban')}+", reply_to=reply_to)
        return
    
    target_id = None
    days = 7
    reason = "Не указана"
    
    if target_from_reply:
        target_id = target_from_reply
        if args:
            try:
                days = int(args[0])
                if days < 1:
                    days = 1
                if days > 365:
                    days = 365
                reason = ' '.join(args[1:]) if len(args) > 1 else "Не указана"
            except:
                reason = ' '.join(args)
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    args.remove(arg)
                    if args:
                        try:
                            days = int(args[0])
                            reason = ' '.join(args[1:]) if len(args) > 1 else "Не указана"
                        except:
                            reason = ' '.join(args)
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /ban @user [дни] [причина]", reply_to=reply_to)
        return
    
    if target_id == user_id:
        sms(vk, peer_id, "❌ Нельзя забанить себя", reply_to=reply_to)
        return
    
    if not can_manage(peer_id, user_id, target_id):
        target_priority = get_user_priority(peer_id, target_id)
        sms(vk, peer_id, f"❌ Нельзя (приоритет {target_priority})", reply_to=reply_to)
        return
    
    target_name = get_user_name(vk, target_id)
    ban_until = ban_user(target_id, peer_id, days, reason, user_id)
    kick_from_chat(vk, peer_id, target_id)
    
    sms(vk, peer_id, f"🚫 [id{target_id}|{target_name}] забанен на {days} дн.\n📝 Причина: {reason}", reply_to=reply_to)

def cmd_mute(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'mute'):
        sms(vk, peer_id, f"❌ Недостаточно прав! Нужен приоритет {get_command_min_priority(peer_id, 'mute')}+", reply_to=reply_to)
        return
    
    target_id = None
    time_str = "30m"
    reason = "Не указана"
    
    if target_from_reply:
        target_id = target_from_reply
        if args:
            time_str = args[0]
            reason = ' '.join(args[1:]) if len(args) > 1 else "Не указана"
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    args.remove(arg)
                    if args:
                        time_str = args[0]
                        reason = ' '.join(args[1:]) if len(args) > 1 else "Не указана"
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /mute @user [время] [причина]\n/mute @user 1h спам", reply_to=reply_to)
        return
    
    if target_id == user_id:
        sms(vk, peer_id, "❌ Нельзя замутить себя", reply_to=reply_to)
        return
    
    if not can_manage(peer_id, user_id, target_id):
        target_priority = get_user_priority(peer_id, target_id)
        sms(vk, peer_id, f"❌ Нельзя (приоритет {target_priority})", reply_to=reply_to)
        return
    
    try:
        minutes = parse_time(time_str)
        if minutes < 1:
            minutes = 1
        if minutes > 1440:
            minutes = 1440
    except:
        sms(vk, peer_id, f"❌ Неверный формат: 30m, 2h, 1d", reply_to=reply_to)
        return
    
    end_time = datetime.now() + timedelta(minutes=minutes)
    target_name = get_user_name(vk, target_id)
    
    muted_users[target_id] = {
        'end_time': end_time,
        'reason': reason,
        'admin_id': user_id,
        'chat_id': peer_id
    }
    
    time_display = f"{minutes}м"
    if minutes >= 1440:
        time_display = f"{minutes//1440}д"
    elif minutes >= 60:
        time_display = f"{minutes//60}ч {minutes%60}м"
    
    sms(vk, peer_id, f"🔇 [id{target_id}|{target_name}] замучен\n📝 Причина: {reason}\n⏰ Время: {time_display}", reply_to=reply_to)

def cmd_unmute(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    target_id = None
    
    if target_from_reply:
        target_id = target_from_reply
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /unmute @user", reply_to=reply_to)
        return
    
    if target_id not in muted_users:
        sms(vk, peer_id, f"❌ Не в муте", reply_to=reply_to)
        return
    
    del muted_users[target_id]
    target_name = get_user_name(vk, target_id)
    sms(vk, peer_id, f"🔊 [id{target_id}|{target_name}] размучен", reply_to=reply_to)

def cmd_unban(vk, peer_id, user_id, args, reply_to, target_from_reply):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    target_id = None
    
    if target_from_reply:
        target_id = target_from_reply
    else:
        if args:
            for arg in args:
                uid = extract_user_id(arg)
                if uid:
                    target_id = uid
                    break
    
    if not target_id:
        sms(vk, peer_id, "❌ /unban @user", reply_to=reply_to)
        return
    
    is_banned, _, _ = is_user_banned(target_id, peer_id)
    
    if not is_banned:
        sms(vk, peer_id, f"❌ Не в бане", reply_to=reply_to)
        return
    
    unban_user(target_id, peer_id)
    target_name = get_user_name(vk, target_id)
    sms(vk, peer_id, f"✅ [id{target_id}|{target_name}] разбанен", reply_to=reply_to)

def set_greeting_command(vk, peer_id, user_id, args, reply_to=None):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'setrole') and get_user_priority(peer_id, user_id) < 60:
        sms(vk, peer_id, "❌ Недостаточно прав!", reply_to=reply_to)
        return
    
    if not args:
        current = get_greeting(peer_id)
        if current:
            sms(vk, peer_id, f"📝 Текущее приветствие:\n{current}", reply_to=reply_to)
        else:
            sms(vk, peer_id, "📝 /setgreeting [текст]\n{user} {mention} {time}", reply_to=reply_to)
        return
    
    text = ' '.join(args)
    set_greeting(peer_id, text)
    sms(vk, peer_id, f"✅ Приветствие установлено!", reply_to=reply_to)

def del_greeting_command(vk, peer_id, user_id, reply_to=None):
    if not is_bot_activated(peer_id):
        sms(vk, peer_id, "❌ Бот не активирован!", reply_to=reply_to)
        return
    
    if not can_use_command(peer_id, user_id, 'setrole') and get_user_priority(peer_id, user_id) < 60:
        sms(vk, peer_id, "❌ Недостаточно прав!", reply_to=reply_to)
        return
    
    remove_greeting(peer_id)
    sms(vk, peer_id, "✅ Приветствие удалено!", reply_to=reply_to)

def send_welcome_on_add(vk, peer_id, added_by_id):
    try:
        init_chat_roles(peer_id)
        init_command_settings(peer_id)
        adder_name = get_user_name(vk, added_by_id)
        
        # Назначаем роли владельцу и админам СРАЗУ при добавлении
        assign_all_roles_from_vk(vk, peer_id)
        
        welcome_text = f"""🤖 Том успешно добавлен в чат!

👤 Добавил: [id{added_by_id}|{adder_name}]

⚙️ Выполнена настройка:
• Создана система ролей
• Настроены права доступа
• ✅ Владельцу выдана роль с приоритетом 100
• ✅ Администраторам выдана роль с приоритетом 80

📋 Для активации бота нажмите кнопку ниже или введите /start
⚠️ Активировать бота может только владелец чата или администраторы!

💡 Все команды станут доступны после активации"""
        
        keyboard = create_start_keyboard()
        sms(vk, peer_id, welcome_text, keyboard)
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def send_user_greeting(vk, peer_id, new_user_id):
    try:
        greeting = get_greeting(peer_id)
        if greeting:
            user_name = get_user_name(vk, new_user_id)
            greeting_text = greeting.replace('{user}', user_name)
            greeting_text = greeting_text.replace('{mention}', f"[id{new_user_id}|{user_name}]")
            greeting_text = greeting_text.replace('{time}', datetime.now().strftime('%H:%M'))
            sms(vk, peer_id, f"🎉 {greeting_text}")
            return True
        return False
    except:
        return False

# === ОБРАБОТЧИКИ ИГР ===
def handle_rps_choice(vk, peer_id, user_id, choice, offer_id):
    if offer_id not in game_offers:
        return
    
    offer = game_offers[offer_id]
    if offer['type'] != 'rps':
        return
    
    if 'player1_choice' not in offer:
        # Первый игрок выбирает
        offer['player1_choice'] = choice
        offer['player1_id'] = user_id
        game_offers[offer_id] = offer
        
        # Отправляем второму игроку
        target_id = offer['to_id'] if offer['from_id'] == user_id else offer['from_id']
        target_name = get_user_name(vk, target_id)
        
        response = f"🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА\n\n"
        response += f"👤 {get_user_name(vk, user_id)} выбрал свой ход!\n"
        response += f"👥 Ждем выбор {target_name}..."
        
        sms(vk, peer_id, response)
        
        # Отправляем клавиатуру второму игроку
        keyboard = create_rps_keyboard()
        sms(vk, peer_id, f"🎮 {target_name}, ваш ход! Выберите:", keyboard)
        
    elif 'player1_choice' in offer and 'player2_choice' not in offer:
        # Второй игрок выбирает
        if user_id != offer['player1_id']:
            offer['player2_choice'] = choice
            offer['player2_id'] = user_id
            
            # Определяем победителя
            p1_choice = offer['player1_choice']
            p2_choice = offer['player2_choice']
            amount = offer['amount']
            
            # Карта игры
            rules = {
                'rock': {'scissors': 'rock', 'paper': 'paper'},
                'scissors': {'paper': 'scissors', 'rock': 'rock'},
                'paper': {'rock': 'paper', 'scissors': 'scissors'}
            }
            
            choice_names = {'rock': '🗻 Камень', 'scissors': '✂️ Ножницы', 'paper': '📄 Бумага'}
            
            if p1_choice == p2_choice:
                winner = None
                result_text = "НИЧЬЯ!"
            elif rules[p1_choice].get(p2_choice) == p1_choice:
                winner = offer['player1_id']
                result_text = f"🏆 Победил: {get_user_name(vk, winner)}!"
            else:
                winner = offer['player2_id']
                result_text = f"🏆 Победил: {get_user_name(vk, winner)}!"
            
            response = f"🎮 РЕЗУЛЬТАТ ИГРЫ\n\n"
            response += f"👤 {get_user_name(vk, offer['player1_id'])}: {choice_names[p1_choice]}\n"
            response += f"👤 {get_user_name(vk, offer['player2_id'])}: {choice_names[p2_choice]}\n\n"
            response += f"{result_text}\n"
            
            if amount > 0 and winner:
                update_balance(winner, peer_id, amount)
                loser = offer['player1_id'] if winner == offer['player2_id'] else offer['player2_id']
                update_balance(loser, peer_id, -amount)
                response += f"💰 {get_user_name(vk, winner)} получает {format_amount(amount)} ТомКоинов!\n"
                response += f"💵 Новый баланс победителя: {format_amount(get_balance(winner, peer_id))} ТК"
            elif amount > 0 and not winner:
                response += f"💰 Ничья! Ставка возвращается."
            
            sms(vk, peer_id, response)
            
            # Удаляем предложение
            del game_offers[offer_id]

def handle_marry_accept(vk, peer_id, user_id, offer_id):
    if offer_id not in game_offers:
        return
    
    offer = game_offers[offer_id]
    if offer['type'] != 'marry':
        return
    
    if user_id != offer['to_id']:
        return
    
    # Свадьба
    set_married(offer['from_id'], peer_id, offer['to_id'])
    
    response = f"💍 СВАДЬБА СОСТОЯЛАСЬ! 💍\n\n"
    response += f"👰 Невеста: [id{offer['to_id']}|{get_user_name(vk, offer['to_id'])}]\n"
    response += f"🤵 Жених: [id{offer['from_id']}|{get_user_name(vk, offer['from_id'])}]\n\n"
    response += f"🎉 Поздравляем молодоженов! 🎉"
    
    sms(vk, peer_id, response)
    
    del game_offers[offer_id]

def handle_offer_decline(vk, peer_id, user_id, offer_id, offer_type):
    if offer_id not in game_offers:
        return
    
    offer = game_offers[offer_id]
    if offer['type'] != offer_type:
        return
    
    if user_id != offer['to_id']:
        return
    
    from_name = get_user_name(vk, offer['from_id'])
    
    if offer_type == 'rps':
        response = f"🎮 [id{offer['from_id']}|{from_name}], ваш соперник отказался играть!"
    else:
        response = f"💔 [id{offer['from_id']}|{from_name}], вам отказали!"
    
    sms(vk, peer_id, response)
    
    del game_offers[offer_id]

# === ОСНОВНОЙ КОД ===
if __name__ == '__main__':
    init_db()
    
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    
    print("🤖 Бот запущен!")
    
    def background_mute_checker():
        while True:
            time.sleep(60)
            check_muted_users()
    
    mute_thread = threading.Thread(target=background_mute_checker, daemon=True)
    mute_thread.start()
    
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                text = msg.get('text', '').strip().lower()
                peer_id = msg.get('peer_id')
                user_id = msg.get('from_id')
                msg_id = msg.get('id')
                conversation_message_id = msg.get('conversation_message_id')
                
                reply_to = None
                target_from_reply = None
                
                if 'reply_message' in msg and msg['reply_message']:
                    target_from_reply = msg['reply_message']['from_id']
                    reply_to = msg['reply_message']['id']
                
                if peer_id <= 2000000000:
                    continue
                
                # Инициализируем структуры
                init_chat_roles(peer_id)
                init_command_settings(peer_id)
                
                # Обновляем статистику сообщений (для всех сообщений)
                if user_id > 0:
                    update_message_stats(user_id, peer_id)
                
                # Проверяем бан/кик только если бот активирован
                if is_bot_activated(peer_id):
                    is_banned, _, _ = is_user_banned(user_id, peer_id)
                    if is_banned:
                        kick_from_chat(vk, peer_id, user_id)
                        continue
                    
                    is_kicked, _ = is_user_kicked(user_id, peer_id)
                    if is_kicked:
                        kick_from_chat(vk, peer_id, user_id)
                        continue
                    
                    if user_id in muted_users:
                        mute_data = muted_users[user_id]
                        if mute_data['end_time'] > datetime.now():
                            delete_message(vk, peer_id, msg_id, conversation_message_id)
                            continue
                        else:
                            del muted_users[user_id]
                    
                    silent_enabled, silent_action = get_silent_settings(peer_id)
                    if silent_enabled and not is_chat_admin(vk, peer_id, user_id) and not text.startswith('/'):
                        if silent_action == 'kick':
                            kick_user(user_id, peer_id, BOT_ID, "Нарушение режима тишины")
                            kick_from_chat(vk, peer_id, user_id)
                        elif silent_action == 'mute':
                            delete_message(vk, peer_id, msg_id, conversation_message_id)
                        continue
                
                # Обработка действий с участниками
                if 'action' in msg and msg['action']:
                    action_type = msg['action'].get('type', '')
                    
                    if action_type == 'chat_invite_user':
                        member_id = msg['action'].get('member_id', 0)
                        if member_id == BOT_ID:
                            added_by = msg['from_id']
                            send_welcome_on_add(vk, peer_id, added_by)
                            continue
                        elif member_id > 0 and member_id != BOT_ID and is_bot_activated(peer_id):
                            is_kicked, _ = is_user_kicked(member_id, peer_id)
                            is_banned, _, _ = is_user_banned(member_id, peer_id)
                            
                            if is_kicked:
                                unkick_user(member_id, peer_id)
                                send_user_greeting(vk, peer_id, member_id)
                            elif is_banned:
                                kick_from_chat(vk, peer_id, member_id)
                            else:
                                send_user_greeting(vk, peer_id, member_id)
                            continue
                    
                    elif action_type == 'chat_kick_user' and is_bot_activated(peer_id):
                        member_id = msg['action'].get('member_id', 0)
                        if member_id > 0:
                            user_name = get_user_name(vk, member_id)
                            keyboard = create_exit_keyboard(member_id)
                            sms(vk, peer_id, f"👤 [id{member_id}|{user_name}] вышел!", keyboard)
                            continue
                
                # Обработка команд
                if text == "/start" or text == "/старт":
                    if is_bot_activated(peer_id):
                        sms(vk, peer_id, "❌ Бот уже активирован!", reply_to=reply_to)
                    else:
                        hello(vk, peer_id, user_id)
                
                elif not is_bot_activated(peer_id):
                    # Если бот не активирован, игнорируем все команды кроме /start
                    if text and not text.startswith('/') and text != "том":
                        sms(vk, peer_id, "❌ Бот не активирован! Активируйте командой /start (только для админов)", reply_to=reply_to)
                
                else:
                    # Бот активирован, обрабатываем все команды
                    if text == "/help" or text == "/помощь":
                        cmd_help(vk, peer_id, user_id)
                    
                    elif text == "/balance" or text == "/баланс" or text == "/балланс":
                        cmd_balance(vk, peer_id, user_id, reply_to)
                    
                    elif text == "/bonus" or text == "/бонус":
                        cmd_bonus(vk, peer_id, user_id, reply_to)
                    
                    elif text.startswith("/casino"):
                        args = text[7:].strip().split()
                        cmd_casino(vk, peer_id, user_id, args, reply_to)
                    
                    elif text.startswith("/transfer"):
                        args = text[9:].strip().split()
                        cmd_transfer(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/rps"):
                        args = text[4:].strip().split()
                        cmd_rps(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/marry"):
                        args = text[6:].strip().split()
                        cmd_marry(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text == "/divorce" or text == "/развод":
                        cmd_divorce(vk, peer_id, user_id, reply_to)
                    
                    elif text == "/topmoney" or text == "/топденег":
                        cmd_top_money(vk, peer_id, user_id, reply_to)
                    
                    elif text == "/stats" or text == "/статистика":
                        cmd_stats(vk, peer_id, user_id, reply_to)
                    
                    elif text == "/top" or text == "/топ":
                        cmd_top(vk, peer_id, user_id, reply_to)
                    
                    elif text.startswith("/createcmd"):
                        args = text[10:].strip().split()
                        cmd_createcmd(vk, peer_id, user_id, args)
                    
                    elif text.startswith("/setgreeting"):
                        parts = text.split(' ', 1)
                        args = [parts[1]] if len(parts) > 1 else []
                        set_greeting_command(vk, peer_id, user_id, args, reply_to)
                    
                    elif text == "/delgreeting":
                        del_greeting_command(vk, peer_id, user_id, reply_to)
                    
                    elif text.startswith("/kick"):
                        args = text[5:].strip().split()
                        cmd_kick(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/ban"):
                        args = text[4:].strip().split()
                        cmd_ban(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/unban"):
                        args = text[6:].strip().split()
                        cmd_unban(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/mute"):
                        args = text[5:].strip().split()
                        cmd_mute(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/unmute"):
                        args = text[7:].strip().split()
                        cmd_unmute(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text == "/silent" or text == "/тишина":
                        cmd_silent(vk, peer_id, user_id)
                    
                    elif text.startswith("/setrole"):
                        args = text[8:].strip().split()
                        cmd_setrole(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/unrole"):
                        args = text[7:].strip().split()
                        cmd_unrole(vk, peer_id, user_id, args, reply_to, target_from_reply)
                    
                    elif text.startswith("/createrole"):
                        args = text[11:].strip().split()
                        cmd_createrole(vk, peer_id, user_id, args, reply_to)
                    
                    elif text.startswith("/deleterole"):
                        args = text[11:].strip().split()
                        cmd_deleterole(vk, peer_id, user_id, args, reply_to)
                    
                    elif text == "/roles":
                        cmd_roles(vk, peer_id, user_id, reply_to)
                    
                    elif text == "/myrole":
                        cmd_myrole(vk, peer_id, user_id, reply_to)
                    
                    elif text == "/members":
                        cmd_members(vk, peer_id, user_id, reply_to)
                    
                    elif text == "том" or text == "том.":
                        tom(vk, peer_id)
            
            elif event.type == VkBotEventType.MESSAGE_EVENT:
                event_obj = event.object
                payload = event_obj.get('payload', {})
                peer_id = event_obj.get('peer_id')
                user_id = event_obj.get('user_id')
                event_id = event_obj.get('event_id')
                
                if not peer_id or not user_id:
                    continue
                
                button = payload.get('button', '') if isinstance(payload, dict) else ''
                
                if button == 'start':
                    if is_bot_activated(peer_id):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Бот уже активирован!"}'
                            )
                        except:
                            pass
                    else:
                        hello(vk, peer_id, user_id)
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"✅ Бот активирован!"}'
                            )
                        except:
                            pass
                    continue
                
                if not is_bot_activated(peer_id):
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"❌ Бот не активирован!"}'
                        )
                    except:
                        pass
                    continue
                
                # Обработка игровых кнопок
                if button.startswith('rps_'):
                    choice = button.split('_')[1]
                    # Ищем активное предложение для этого пользователя
                    for offer_id, offer in list(game_offers.items()):
                        if offer['type'] == 'rps' and (offer['from_id'] == user_id or offer['to_id'] == user_id):
                            handle_rps_choice(vk, peer_id, user_id, choice, offer_id)
                            break
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"✅ Выбор сделан!"}'
                        )
                    except:
                        pass
                
                elif button.startswith('rps_accept_'):
                    offer_id = int(button.split('_')[2])
                    # Отправляем клавиатуру для выбора
                    keyboard = create_rps_keyboard()
                    sms(vk, peer_id, f"🎮 Выберите: камень, ножницы или бумага?", keyboard)
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"✅ Предложение принято! Выберите ход."}'
                        )
                    except:
                        pass
                
                elif button.startswith('rps_decline_'):
                    offer_id = int(button.split('_')[2])
                    handle_offer_decline(vk, peer_id, user_id, offer_id, 'rps')
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"❌ Вы отказались"}'
                        )
                    except:
                        pass
                
                elif button.startswith('marry_accept_'):
                    offer_id = int(button.split('_')[2])
                    handle_marry_accept(vk, peer_id, user_id, offer_id)
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"💍 Поздравляем с браком!"}'
                        )
                    except:
                        pass
                
                elif button.startswith('marry_decline_'):
                    offer_id = int(button.split('_')[2])
                    handle_offer_decline(vk, peer_id, user_id, offer_id, 'marry')
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"❌ Вы отказались"}'
                        )
                    except:
                        pass
                
                elif button.startswith('silent_action_'):
                    action = button.replace('silent_action_', '')
                    
                    if not can_use_command(peer_id, user_id, 'silent'):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Недостаточно прав!"}'
                            )
                        except:
                            pass
                        continue
                    
                    if action == 'cancel':
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Отмена"}'
                            )
                        except:
                            pass
                        continue
                    
                    if action == 'kick':
                        set_silent_settings(peer_id, True, 'kick')
                        response = "🔇 Режим тишины: КИКАТЬ\n💡 /silent - выключить"
                    else:
                        set_silent_settings(peer_id, True, 'mute')
                        response = "🔇 Режим тишины: УДАЛЯТЬ\n💡 /silent - выключить"
                    
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"✅ Режим включен!"}'
                        )
                    except:
                        pass
                    
                    sms(vk, peer_id, response)
                    continue
                
                elif button == 'silent_turn_on':
                    if not can_use_command(peer_id, user_id, 'silent'):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Недостаточно прав!"}'
                            )
                        except:
                            pass
                        continue
                    
                    keyboard = create_silent_keyboard()
                    sms(vk, peer_id, "🔇 Включить режим тишины?", keyboard)
                    
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"⚡ Выберите действие"}'
                        )
                    except:
                        pass
                    continue
                
                admin_priority = get_user_priority(peer_id, user_id)
                
                if button.startswith('kick_'):
                    target_id = int(button.split('_')[1])
                    
                    if not can_use_command(peer_id, user_id, 'kick'):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Недостаточно прав!"}'
                            )
                        except:
                            pass
                        continue
                    
                    if not can_manage(peer_id, user_id, target_id):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Нельзя!"}'
                            )
                        except:
                            pass
                        continue
                    
                    target_name = get_user_name(vk, target_id)
                    kick_user(target_id, peer_id, user_id, "Вышел из чата")
                    kick_from_chat(vk, peer_id, target_id)
                    
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"✅ Кикнут!"}'
                        )
                    except:
                        pass
                    
                    sms(vk, peer_id, f"👢 [id{target_id}|{target_name}] кикнут!")
                
                elif button.startswith('ban_') and not button.startswith('ban_days_') and not button.startswith('ban_cancel_'):
                    target_id = int(button.split('_')[1])
                    
                    if not can_use_command(peer_id, user_id, 'ban'):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Недостаточно прав!"}'
                            )
                        except:
                            pass
                        continue
                    
                    if not can_manage(peer_id, user_id, target_id):
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"❌ Нельзя!"}'
                            )
                        except:
                            pass
                        continue
                    
                    target_name = get_user_name(vk, target_id)
                    keyboard = create_ban_keyboard(target_id)
                    sms(vk, peer_id, f"🚫 Срок бана для [id{target_id}|{target_name}]:", keyboard)
                
                elif button.startswith('ban_days_'):
                    parts = button.split('_')
                    if len(parts) >= 4:
                        days = int(parts[2])
                        target_id = int(parts[3])
                        
                        if not can_manage(peer_id, user_id, target_id):
                            try:
                                vk.messages.sendMessageEventAnswer(
                                    event_id=event_id,
                                    peer_id=peer_id,
                                    user_id=user_id,
                                    event_data='{"type":"show_snackbar","text":"❌ Нельзя!"}'
                                )
                            except:
                                pass
                            continue
                        
                        target_name = get_user_name(vk, target_id)
                        ban_until = ban_user(target_id, peer_id, days, "Вышел из чата", user_id)
                        kick_from_chat(vk, peer_id, target_id)
                        
                        try:
                            vk.messages.sendMessageEventAnswer(
                                event_id=event_id,
                                peer_id=peer_id,
                                user_id=user_id,
                                event_data='{"type":"show_snackbar","text":"✅ Забанен!"}'
                            )
                        except:
                            pass
                        
                        sms(vk, peer_id, f"🚫 [id{target_id}|{target_name}] забанен на {days} дн.")
                
                elif button.startswith('ban_cancel_'):
                    try:
                        vk.messages.sendMessageEventAnswer(
                            event_id=event_id,
                            peer_id=peer_id,
                            user_id=user_id,
                            event_data='{"type":"show_snackbar","text":"❌ Отмена"}'
                        )
                    except:
                        pass
                        
        except Exception as e:
            print(f"❌ Ошибка: {e}")
