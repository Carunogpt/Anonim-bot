import sqlite3

DB_NAME = 'bot_database.db'

def init_db():
    """Инициализирует базу данных и создает таблицы, если их нет."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                messages_received INTEGER DEFAULT 0,
                is_subscribed INTEGER DEFAULT 0,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def add_user_if_not_exists(user_id: int, username: str):
    """Добавляет нового пользователя в базу данных, если его там еще нет."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone() is None:
            cursor.execute(
                'INSERT INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            conn.commit()

def get_user_stats(user_id: int):
    """Получает статистику пользователя: количество сообщений и статус подписки."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT messages_received, is_subscribed FROM users WHERE user_id = ?',
            (user_id,)
        )
        return cursor.fetchone()

def get_user_info(user_id: int):
    """Получает информацию о лимитах пользователя."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT messages_received, is_subscribed FROM users WHERE user_id = ?',
            (user_id,)
        )
        return cursor.fetchone()


def increment_message_count(user_id: int):
    """Увеличивает счетчик полученных сообщений для пользователя."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET messages_received = messages_received + 1 WHERE user_id = ?',
            (user_id,)
        )
        conn.commit()

def activate_subscription(user_id: int):
    """Активирует подписку для пользователя."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET is_subscribed = 1 WHERE user_id = ?',
            (user_id,)
        )
        conn.commit()

# Можно добавить функцию для сброса дневных лимитов,
# которую нужно будет запускать раз в день (например, через cron).
def reset_daily_limits():
    """Сбрасывает счетчик полученных сообщений для всех пользователей."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET messages_received = 0')
        conn.commit()
        print("Дневные лимиты сброшены.")
