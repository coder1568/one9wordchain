import aiosqlite
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = 'wordchain_bot.db'):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.initialize_database()
        return self

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def initialize_database(self):
        # First, check if we need to migrate existing tables
        await self.conn.execute("PRAGMA foreign_keys = OFF")
        
        # Drop and recreate tables with proper schema
        sql = """
        -- Drop existing tables if they exist
        DROP TABLE IF EXISTS gameplayer;
        DROP TABLE IF EXISTS donation;
        DROP TABLE IF EXISTS wordlist;
        DROP TABLE IF EXISTS game;
        DROP TABLE IF EXISTS player;

        -- Recreate tables with proper schema
        CREATE TABLE IF NOT EXISTS player (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT UNIQUE NOT NULL,
            game_count INTEGER NOT NULL DEFAULT 0,
            win_count INTEGER NOT NULL DEFAULT 0,
            word_count INTEGER NOT NULL DEFAULT 0,
            letter_count INTEGER NOT NULL DEFAULT 0,
            longest_word TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS game (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id BIGINT NOT NULL,
            players INTEGER DEFAULT 0,
            game_mode TEXT NOT NULL,
            winner BIGINT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, start_time)
        );

        CREATE TABLE IF NOT EXISTS gameplayer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT NOT NULL,
            group_id BIGINT NOT NULL,
            game_id INTEGER NOT NULL,
            won INTEGER NOT NULL DEFAULT 0,
            word_count INTEGER NOT NULL DEFAULT 0,
            letter_count INTEGER NOT NULL DEFAULT 0,
            longest_word TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES game(id) ON DELETE CASCADE,
            UNIQUE(user_id, game_id)
        );

        CREATE TABLE IF NOT EXISTS donation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT NOT NULL,
            donation_id TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            donate_time TIMESTAMP NOT NULL,
            telegram_payment_charge_id TEXT NOT NULL,
            provider_payment_charge_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS wordlist (
            word TEXT PRIMARY KEY,
            accepted INTEGER NOT NULL DEFAULT 0,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_game_group_id ON game(group_id);
        CREATE INDEX IF NOT EXISTS idx_gameplayer_user_id ON gameplayer(user_id);
        CREATE INDEX IF NOT EXISTS idx_gameplayer_game_id ON gameplayer(game_id);
        """
        
        try:
            # Execute the SQL
            await self.conn.executescript(sql)
            await self.conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
        finally:
            await self.conn.execute("PRAGMA foreign_keys = ON")
            await self.conn.commit()

    async def execute(self, query: str, *args):
        try:
            cursor = await self.conn.execute(query, args)
            await self.conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"Error executing query: {query}")
            logger.error(f"Error: {e}")
            raise

    async def fetch(self, query: str, *args):
        cursor = await self.execute(query, *args)
        return await cursor.fetchall()

    async def fetchrow(self, query: str, *args):
        cursor = await self.execute(query, *args)
        return await cursor.fetchone()

    async def fetchval(self, query: str, *args):
        row = await self.fetchrow(query, *args)
        return row[0] if row else None

# Global database instance
db = Database()
