# modules/database.py
"""
Provides thread-safe SQLite operations for storing and retrieving key/value data,
as well as structured data for notes and internal events.
"""
import sqlite3
import os
from threading import Lock 
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Union


from core.logger import logger
from core.settings import settings


class Database:
    _write_lock = Lock() # Class-level lock for all write operations


    def __init__(self, db_path: Optional[str] = None):
        """
        Initializes the database connection.
        """
        self.db_path = db_path if db_path else settings.get_db_path()
        self.conn: Optional[sqlite3.Connection] = None
        
        try:
            # Ensure the directory for the database exists
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Database directory created: {db_dir}")


            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
            self.conn.row_factory = sqlite3.Row # Access columns by name
            self.create_tables()
            logger.info(f"Database connection established to {self.db_path}")
        except sqlite3.Error as e:
            logger.critical(f"Database connection critical error for {self.db_path}", extra={"error": str(e)}, exc_info=True)
            raise SystemExit(f"Fatal: Could not connect to or initialize database at {self.db_path}. Error: {e}") from e
        except OSError as e_os: 
            logger.critical(f"OS error during database directory creation for {self.db_path}", extra={"error": str(e_os)}, exc_info=True)
            raise SystemExit(f"Fatal: OS error setting up database directory. Error: {e_os}") from e_os


    def _execute_query(
        self, 
        query: str, 
        params: Tuple = (), 
        fetch_one: bool = False, 
        fetch_all: bool = False, 
        is_write: bool = False
    ) -> Any:
        """Internal helper to execute SQL queries."""
        if not self.conn:
            logger.error("Database connection is not available for query.", extra={"query": query[:100]})
            return None

        log_extra = {"query_snippet": query[:150], "params": str(params)}
        try:
            if is_write:
                with Database._write_lock: 
                    with self.conn: 
                        cursor = self.conn.cursor()
                        cursor.execute(query, params)
                        return cursor.lastrowid if "INSERT" in query.upper() or "REPLACE" in query.upper() else cursor.rowcount
            else: 
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                if fetch_one:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                return None 

        except sqlite3.Error as e:
            logger.error("Database query error.", extra={**log_extra, "sqlite_error": str(e)}, exc_info=True)
            return None
        except Exception as e_generic:
            logger.error("Generic error during database query.", extra={**log_extra, "error_type": type(e_generic).__name__, "error": str(e_generic)}, exc_info=True)
            return None


    def create_tables(self) -> None:
        """Creates necessary tables if they don't exist."""
        if not self.conn:
            logger.error("Cannot create tables, database connection is not available.")
            return
            
        queries = [
            '''CREATE TABLE IF NOT EXISTS user_data (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )''',
            '''CREATE TABLE IF NOT EXISTS thoughts_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                tags TEXT,
                timestamp TEXT NOT NULL, 
                created_at TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'NOW')),
                updated_at TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'NOW'))
            )''',
            # Trigger to auto-update 'updated_at' timestamp on thoughts_notes table
            '''CREATE TRIGGER IF NOT EXISTS trg_thoughts_notes_update_updated_at
                AFTER UPDATE ON thoughts_notes
                FOR EACH ROW
                BEGIN
                    UPDATE thoughts_notes SET updated_at = (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'NOW')) WHERE id = OLD.id;
                END;
            ''',
            '''CREATE TABLE IF NOT EXISTS internal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL, 
                event_time TEXT,          
                description TEXT NOT NULL,
                created_at TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'NOW'))
            )'''
        ]
        try:
            with self.conn: 
                for query in queries:
                    cursor = self.conn.cursor()
                    cursor.execute(query)
            logger.info("Standard database tables ensured (user_data, thoughts_notes, internal_events).")
        except sqlite3.Error as e:
            logger.error("Error creating database tables.", extra={"error": str(e)}, exc_info=True)
            raise 


    def store_kv_data(self, key: str, value: str) -> bool:
        """Stores or replaces a key-value pair in the user_data table."""
        result = self._execute_query('REPLACE INTO user_data (key, value) VALUES (?, ?)', (key, value), is_write=True)
        return result is not None 


    def retrieve_kv_data(self, key: str) -> Optional[str]:
        """Retrieves a value by key from the user_data table."""
        row = self._execute_query('SELECT value FROM user_data WHERE key=?', (key,), fetch_one=True)
        return row['value'] if row else None


    def add_thought_note_db(self, content: str, title: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[int]:
        """Adds a new thought/note to the thoughts_notes table."""
        timestamp_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        tags_str = ",".join(sorted(list(set(tag.strip().lower() for tag in tags)))) if tags and isinstance(tags, list) else None
        query = 'INSERT INTO thoughts_notes (title, content, tags, timestamp) VALUES (?, ?, ?, ?)'
        last_row_id = self._execute_query(query, (title, content, tags_str, timestamp_iso), is_write=True)
        return last_row_id if last_row_id is not None and last_row_id > 0 else None


    def get_thought_notes_db(
        self, 
        search_term: Optional[str] = None, 
        tag_filter: Optional[str] = None, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Dict[str, Any]]: 
        """Retrieves thought notes."""
        # ... (implementation simplified for brevity) ...
        return []


    def close(self) -> None:
        """Closes the database connection if it's open."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.info(f"Database connection to {self.db_path} closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection to {self.db_path}.", extra={"error": str(e)}, exc_info=True)