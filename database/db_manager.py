import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "media.db")


class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Таблица плейлистов
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        
        # Таблица треков (только уникальные треки)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                duration REAL
            )
        """)
        
        # Таблица связи трек-плейлист (многие ко многим)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS track_playlist (
                track_id INTEGER,
                playlist_id INTEGER,
                PRIMARY KEY (track_id, playlist_id),
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    # Плейлисты
    def add_playlist(self, name):
        self.cursor.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()

    def delete_playlist(self, playlist_id):
        self.cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self.conn.commit()

    def get_playlists(self):
        self.cursor.execute("SELECT * FROM playlists ORDER BY name")
        return self.cursor.fetchall()

    # Треки
    def add_track(self, title, file_path, duration=0):
        """Добавляет трек в базу (если еще нет)"""
        # Проверяем, есть ли уже такой трек
        self.cursor.execute("SELECT id FROM tracks WHERE file_path = ?", (file_path,))
        existing = self.cursor.fetchone()
        
        if existing:
            return existing[0]  # Возвращаем ID существующего трека
        else:
            self.cursor.execute(
                "INSERT INTO tracks (title, file_path, duration) VALUES (?, ?, ?)",
                (title, file_path, duration)
            )
            self.conn.commit()
            return self.cursor.lastrowid

    def delete_track(self, track_id):
        """Удаляет трек из ВСЕХ плейлистов и из базы"""
        self.cursor.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        self.conn.commit()

    def get_tracks(self):
        """Получает ВСЕ треки"""
        self.cursor.execute("SELECT * FROM tracks ORDER BY title")
        return self.cursor.fetchall()

    def get_tracks_in_playlist(self, playlist_id):
        """Получает треки в конкретном плейлисте"""
        self.cursor.execute("""
            SELECT t.* FROM tracks t
            INNER JOIN track_playlist tp ON t.id = tp.track_id
            WHERE tp.playlist_id = ?
            ORDER BY t.title
        """, (playlist_id,))
        return self.cursor.fetchall()

    def get_all_tracks_with_playlists(self):
        """Получает все треки с информацией о плейлистах"""
        self.cursor.execute("""
            SELECT t.*, 
                   GROUP_CONCAT(p.name, ', ') as playlist_names,
                   GROUP_CONCAT(p.id, ', ') as playlist_ids
            FROM tracks t
            LEFT JOIN track_playlist tp ON t.id = tp.track_id
            LEFT JOIN playlists p ON tp.playlist_id = p.id
            GROUP BY t.id
            ORDER BY t.title
        """)
        return self.cursor.fetchall()

    # Работа с плейлистами
    def add_track_to_playlist(self, track_id, playlist_id):
        """Добавляет трек в плейлист"""
        try:
            self.cursor.execute(
                "INSERT INTO track_playlist (track_id, playlist_id) VALUES (?, ?)",
                (track_id, playlist_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Уже есть такая связь
            return False

    def remove_track_from_playlist(self, track_id, playlist_id):
        """Удаляет трек из плейлиста (но не из базы!)"""
        self.cursor.execute(
            "DELETE FROM track_playlist WHERE track_id = ? AND playlist_id = ?",
            (track_id, playlist_id)
        )
        self.conn.commit()

    def remove_track_from_all_playlists(self, track_id):
        """Удаляет трек из всех плейлистов"""
        self.cursor.execute(
            "DELETE FROM track_playlist WHERE track_id = ?",
            (track_id,)
        )
        self.conn.commit()

    def is_track_in_playlist(self, track_id, playlist_id):
        """Проверяет, есть ли трек в плейлисте"""
        self.cursor.execute(
            "SELECT 1 FROM track_playlist WHERE track_id = ? AND playlist_id = ?",
            (track_id, playlist_id)
        )
        return self.cursor.fetchone() is not None

    def get_track_playlists(self, track_id):
        """Получает все плейлисты, в которых есть трек"""
        self.cursor.execute("""
            SELECT p.* FROM playlists p
            INNER JOIN track_playlist tp ON p.id = tp.playlist_id
            WHERE tp.track_id = ?
            ORDER BY p.name
        """, (track_id,))
        return self.cursor.fetchall()