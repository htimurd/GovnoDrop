import time
import aiosqlite

DB_PATH = "govno_drop.db"

START_COINS = 1000
DAILY_BONUS = 200
DAILY_COOLDOWN = 24 * 60 * 60  # секунд


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    coins INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_daily INTEGER NOT NULL DEFAULT 0,
    banned INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    obtained_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def get_or_create_user(user_id: int, username: str | None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            if username and row["username"] != username:
                await db.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?", (username, user_id)
                )
                await db.commit()
            return dict(row)

        now = int(time.time())
        await db.execute(
            "INSERT INTO users (user_id, username, coins, created_at, last_daily, banned) "
            "VALUES (?, ?, ?, ?, 0, 0)",
            (user_id, username, START_COINS, now),
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row)


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row[0])


async def set_banned(user_id: int, banned: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (int(banned), user_id))
        await db.commit()


async def add_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id)
        )
        await db.commit()


async def get_coins(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def try_claim_daily(user_id: int) -> tuple[bool, int]:
    """Возвращает (успех, секунд_до_след_попытки)."""
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        last = row[0] if row else 0
        elapsed = now - last
        if elapsed < DAILY_COOLDOWN:
            return False, DAILY_COOLDOWN - elapsed
        await db.execute(
            "UPDATE users SET coins = coins + ?, last_daily = ? WHERE user_id = ?",
            (DAILY_BONUS, now, user_id),
        )
        await db.commit()
        return True, 0


async def add_item(user_id: int, item_key: str) -> int:
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO inventory (user_id, item_key, obtained_at) VALUES (?, ?, ?)",
            (user_id, item_key, now),
        )
        await db.commit()
        return cur.lastrowid


async def remove_item(item_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def get_inventory(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM inventory WHERE user_id = ? ORDER BY obtained_at DESC", (user_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_item(item_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def top_by_coins(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, username, coins FROM users "
            "WHERE banned = 0 ORDER BY coins DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def top_by_items(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT u.user_id, u.username, COUNT(i.id) as item_count
            FROM users u
            LEFT JOIN inventory i ON i.user_id = u.user_id
            WHERE u.banned = 0
            GROUP BY u.user_id
            ORDER BY item_count DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), SUM(coins) FROM users")
        users_count, total_coins = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM inventory")
        (items_count,) = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
        (banned_count,) = await cur.fetchone()
        return {
            "users_count": users_count or 0,
            "total_coins": total_coins or 0,
            "items_count": items_count or 0,
            "banned_count": banned_count or 0,
        }


async def all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]
