import sqlite3
import os
from .utils import load_proxies_from_file
import logging

DB_NAME = 'youtube_data.db'

class DatabaseConnection:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()  # Rollback if any exception occurs
        self.conn.close()

def init_db():
    if not os.path.exists(DB_NAME):
        with DatabaseConnection(DB_NAME) as cursor:
            create_tables(cursor)
            print(f"Database '{DB_NAME}' created successfully.")
    else:
        print(f"Database '{DB_NAME}' already exists.")


def create_tables():
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloaded_videos (
                video_id TEXT PRIMARY KEY,
                channel_name TEXT,
                video_title TEXT,
                download_date TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_links (
                video_url TEXT PRIMARY KEY,
                video_title TEXT,
                date_scraped TEXT,
                channel_name TEXT
            )
        ''')

        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_video_url ON video_links (video_url)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checked_proxies (
                proxy TEXT PRIMARY KEY,
                is_valid INTEGER,
                last_checked_date TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleaned_subtitles (
                video_url TEXT PRIMARY KEY,
                channel_name TEXT,
                video_title TEXT,
                subtitles TEXT
            )
        ''')

def save_video_links_batch(videos_data):
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.executemany('''
            INSERT OR REPLACE INTO video_links (video_url, video_title, date_scraped, channel_name)
            VALUES (?, ?, ?, ?)
        ''', videos_data)

def load_video_links(channel_name):
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            SELECT video_url FROM video_links
            WHERE channel_name = ?
        ''', (channel_name,))
        return [row[0] for row in cursor.fetchall()]

def get_video_link_count(channel_name):
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            SELECT COUNT(*) FROM video_links
            WHERE channel_name = ?
        ''', (channel_name,))
        return cursor.fetchone()[0]

def mark_video_downloaded(video_url, channel_name, video_title):
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO downloaded_videos (video_id, channel_name, video_title, download_date)
            VALUES (?, ?, ?, date('now'))
        ''', (video_url, channel_name, video_title))

def save_cleaned_subtitles(video_url, channel_name, video_title, cleaned_subtitles):
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO cleaned_subtitles (video_url, channel_name, video_title, subtitles)
            VALUES (?, ?, ?, ?)
        ''', (video_url, channel_name, video_title, cleaned_subtitles))

##########
# PROXY  #
##########
def save_checked_proxy(proxy, is_valid, last_checked_date):
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO checked_proxies (proxy, is_valid, last_checked_date)
            VALUES (?, ?, ?)
        ''', (proxy, is_valid, last_checked_date))


def load_unchecked_proxies():
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            SELECT proxy FROM checked_proxies WHERE is_valid IS NULL
        ''')

        unchecked_proxies = [row[0] for row in cursor.fetchall()]
        return unchecked_proxies

def load_valid_proxies():
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            SELECT proxy FROM checked_proxies WHERE is_valid = 1
        ''')
        valid_proxies = [row[0] for row in cursor.fetchall()]
        return valid_proxies

def count_valid_proxies():
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            SELECT COUNT(*) FROM checked_proxies WHERE is_valid = 1
        ''')
        count = cursor.fetchone()[0]
        return count

def delete_all_proxies():
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            DELETE FROM checked_proxies
        ''')

def load_proxies_from_file(file_path):
    valid_proxies, invalid_proxies = load_proxies_from_file(file_path)

    with DatabaseConnection('youtube_data.db') as cursor:
        for proxy in valid_proxies:
            cursor.execute('''
                INSERT OR IGNORE INTO checked_proxies (proxy, is_valid, last_checked_date)
                VALUES (?, NULL, NULL)
            ''', (proxy,))

    if invalid_proxies:
        logging.warning(f"The following proxies have an invalid format and were skipped: {', '.join(invalid_proxies)}")

    return len(valid_proxies)

def load_all_proxies():
    with DatabaseConnection('youtube_data.db') as cursor:
        cursor.execute('''
            SELECT proxy FROM checked_proxies
        ''')

        all_proxies = [row[0] for row in cursor.fetchall()]

        return all_proxies

create_tables()