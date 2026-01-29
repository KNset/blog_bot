import sqlite3
import logging

DB_NAME = "blog_bot.db"

def init_db(initial_admin_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create admins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    # Create posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            link TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add initial admin if not exists
    try:
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (initial_admin_id,))
        conn.commit()
    except Exception as e:
        logging.error(f"Error adding initial admin: {e}")
        
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error adding admin: {e}")
        return False
    finally:
        conn.close()

def add_post(title, description, link, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO posts (title, description, link, content) VALUES (?, ?, ?, ?)",
            (title, description, link, content)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error adding post: {e}")
        return False
    finally:
        conn.close()

def get_all_posts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Get latest posts first
    cursor.execute("SELECT title, description, link, content, created_at FROM posts ORDER BY created_at DESC")
    posts = cursor.fetchall()
    conn.close()
    return posts
