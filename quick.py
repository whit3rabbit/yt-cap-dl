import sqlite3

DB_NAME = 'youtube_data.db'

def update_database():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Rename the existing 'cleaned_subtitles' table to 'cleaned_subtitles_old'
        cursor.execute('''
            ALTER TABLE cleaned_subtitles RENAME TO cleaned_subtitles_old
        ''')

        # Create the new 'cleaned_subtitles' table with the updated schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleaned_subtitles (
                video_url TEXT PRIMARY KEY,
                channel_name TEXT,
                video_title TEXT,
                subtitles TEXT
            )
        ''')

        # Copy the data from the old table to the new table
        cursor.execute('''
            INSERT INTO cleaned_subtitles (video_url, subtitles)
            SELECT video_url, subtitles FROM cleaned_subtitles_old
        ''')

        # Drop the old 'cleaned_subtitles_old' table
        cursor.execute('''
            DROP TABLE cleaned_subtitles_old
        ''')

        # Check if the 'video_title' column exists in the 'downloaded_videos' table
        cursor.execute('''
            PRAGMA table_info(downloaded_videos)
        ''')
        columns = [column[1] for column in cursor.fetchall()]

        if 'video_title' not in columns:
            # Add the 'video_title' column to the 'downloaded_videos' table
            cursor.execute('''
                ALTER TABLE downloaded_videos
                ADD COLUMN video_title TEXT
            ''')
            print("Added 'video_title' column to 'downloaded_videos' table.")
        else:
            print("'video_title' column already exists in 'downloaded_videos' table.")

        conn.commit()
        print("Database updated successfully.")

if __name__ == '__main__':
    update_database()