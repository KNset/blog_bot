import sqlite3
import logging

DEFAULT_DB_NAME = "blog_bot.db"

def init_db(initial_admin_id, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
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

    # Create child_bots table (only needed for main bot, but harmless if in all)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS child_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            admin_id INTEGER NOT NULL,
            db_path TEXT NOT NULL,
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

def is_admin(user_id, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_admin(user_id, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
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

def add_post(title, description, link, content, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
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

def get_all_posts(db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Get latest posts first
    cursor.execute("SELECT id, title, description, link, content, created_at FROM posts ORDER BY created_at DESC")
    posts = cursor.fetchall()
    conn.close()
    return posts

def get_post(post_id, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, link, content, created_at FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    conn.close()
    return post

def update_post(post_id, title, description, link, content, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE posts SET title = ?, description = ?, link = ?, content = ? WHERE id = ?",
            (title, description, link, content, post_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error updating post: {e}")
        return False
    finally:
        conn.close()

def delete_post(post_id, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error deleting post: {e}")
        return False
    finally:
        conn.close()

# --- Child Bot Management Functions ---

def add_child_bot(token, admin_id, child_db_path, db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO child_bots (token, admin_id, db_path) VALUES (?, ?, ?)",
            (token, admin_id, child_db_path)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error adding child bot: {e}")
        return False
    finally:
        conn.close()

def get_all_child_bots(db_path=DEFAULT_DB_NAME):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, token, admin_id, db_path, created_at FROM child_bots")
    bots = cursor.fetchall()
    conn.close()
    return bots
