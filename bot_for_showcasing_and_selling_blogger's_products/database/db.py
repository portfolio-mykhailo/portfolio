# Database handling file: creates tables, adds data, retrieves data

import aiosqlite


async def start_db():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS Users(
            "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "ID_Telegram" INTEGER,
            "Tag" TEXT,
            "Name" TEXT,
            "Language" TEXT,
            "Admin" INTEGER
        )""")

        await cur.execute("""
        CREATE TABLE IF NOT EXISTS Stream(
            "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "ID_Telegram" INTEGER,
            "Name" TEXT,
            "Tag" TEXT,
            "Type" TEXT,
            "Screenshot" TEXT,
            "Processed" INTEGER DEFAULT 0,
            "Invited" INTEGER DEFAULT 0
        )""")

        await cur.execute("""
        CREATE TABLE IF NOT EXISTS Poetry(
            "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "ID_Telegram" INTEGER,
            "Name" TEXT,
            "Tag" TEXT,
            "Type" TEXT,
            "Screenshot" TEXT,
            "Processed" INTEGER DEFAULT 0
        )""")

        await cur.execute("""
            CREATE TABLE IF NOT EXISTS Settings(
            "Name" TEXT,
            "Value" INTEGER DEFAULT 0
        )""")

        await db.commit()


async def add_to_db(user_id: int, tag: str = None, name: str = None, language: str = None, admin: int = 0):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute('''
                INSERT INTO
                Users (ID_Telegram, Tag, Name, Language, Admin) 
                VALUES (?, ?, ?, ?, ?)''', (user_id, tag, name, language, admin))
        await db.commit()


async def get_language(user_id: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute(
            "SELECT Language FROM Users WHERE ID_Telegram = (?)", (user_id,)
        )
        result = await cur.fetchone()

        return result[0] if result else None


async def update_language(user_id: int, new_language: str):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute(
            "UPDATE Users SET Language = ? WHERE ID_Telegram = ?",
            (new_language, user_id),
        )
        await db.commit()


async def is_user():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute(
            "SELECT ID_Telegram FROM Users WHERE Admin = 0"
        )
        existing_records = await cur.fetchall()
        result = [record[0] for record in existing_records]

        return result


async def is_admin():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute(
            "SELECT ID_Telegram FROM Users WHERE Admin = 1"
        )
        existing_records = await cur.fetchall()
        result = [record[0] for record in existing_records]

        return result


async def is_profiled(user_id: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute(
            "SELECT ID_Telegram FROM Users WHERE ID_Telegram = ?", (user_id,)
        )
        existing_records = await cur.fetchone()
        if existing_records is not None:
            return True

        return False


async def get_all_users():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute(
            "SELECT * FROM Users"
        )
        existing_records = await cur.fetchall()
        result = {}
        for record in existing_records:
            result[record[1]] = record[2], record[3]

        return result


async def set_price(name: str, new_value: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("UPDATE Settings SET Value = ? WHERE Name = ?", (new_value, name))
        await db.commit()


async def get_price(name: str):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT Value FROM Settings WHERE Name = ?", (name,))
        value = await cur.fetchone()

        return value[0]


async def set_is_active():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        current_status = await get_is_active()
        value = 1 if current_status == 0 else 0
        await cur.execute("UPDATE Settings SET Value = ? WHERE Name = 'kinoterapy_status'", (value,))
        await db.commit()

        if value == 1:
            await cur.execute("DELETE FROM Stream")
            await cur.execute("UPDATE Settings SET Value = NULL WHERE Name IN (?, ?)",
                              ("channel_id", "group_id"))
            await db.commit()


async def get_is_active():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT Value FROM Settings WHERE Name = ?", ('kinoterapy_status',))
        status = await cur.fetchone()

        return status[0]


async def add_to_stream(data: dict):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("""INSERT INTO
                Stream (ID_Telegram, Name,  Tag, Type, Screenshot) 
                VALUES (?, ?, ?, ?, ?)""", (data["user_id"], data["name"], data["tag"], data["type"],
                                            data["screenshot"]))
        await db.commit()


async def add_to_poetry(data: dict):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("""INSERT INTO
                Poetry (ID_Telegram, Name,  Tag, Type, Screenshot) 
                VALUES (?, ?, ?, ?, ?)""", (data["user_id"], data["name"], data["tag"], data["type"],
                                            data["screenshot"]))
        await db.commit()


async def change_processed(user_id: int, processed: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        if processed == 1:
            await cur.execute("UPDATE Stream SET Processed = 1 WHERE ID_Telegram = ?", (user_id,))
        elif processed == 2:
            await cur.execute("DELETE FROM Stream WHERE ID_Telegram = ?; ",
                              (user_id, ))

        await db.commit()


async def change_poetry_processed(user_id: int, processed: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        if processed == 1:
            await cur.execute("UPDATE Poetry SET Processed = 1 WHERE ID_Telegram = ?", (user_id,))
        elif processed == 2:
            await cur.execute("DELETE FROM Poetry WHERE ID_Telegram = ?; ",
                              (user_id, ))

        await db.commit()


async def get_not_invited():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram FROM Stream WHERE Invited = 0 AND Processed = 1")
        results = await cur.fetchall()

        return [result[0] for result in results]


async def change_invited(user_id: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("UPDATE Stream SET Invited = 1 WHERE ID_Telegram = ?", (user_id,))
    
        await db.commit()


async def invoices():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram, Tag, Type, Screenshot FROM Stream WHERE Processed = 0")
        existing_records = await cur.fetchall()
        result = [record for record in existing_records]

        return result
    

async def poetry_invoices():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram, Name FROM Poetry WHERE Processed = 0")
        existing_records = await cur.fetchall()
        result = [record for record in existing_records]

        return result


async def accepted_invoices():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram, Name FROM Stream WHERE Processed = 1")
        existing_records = await cur.fetchall()
        result = [record for record in existing_records]

        return result


async def payed_for_group():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram FROM Stream WHERE Processed = 1")
        existing_records = await cur.fetchall()
        result = [record[0] for record in existing_records]

        return result


async def with_call_back():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram, Name FROM Stream WHERE Processed = 1 AND Type = 'personal'")
        existing_records = await cur.fetchall()
        result = [record for record in existing_records]

        return result
    

async def get_info_about_invoice(user_id: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram, Tag, Type, Screenshot, Invited FROM Stream WHERE ID_Telegram = ?",
                          (user_id, ))
        result = await cur.fetchone()
        return result


async def get_info_about_poetry_invoice(user_id: int):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT ID_Telegram, Tag, Screenshot FROM Poetry WHERE ID_Telegram = ?",
                          (user_id, ))
        result = await cur.fetchone()
        return result


async def get_channel_data():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT Value FROM Settings WHERE Name IN (?, ?)",
                          ("channel_id", "group_id"))
        results = await cur.fetchall()
        result = [result[0] for result in results]

        return result


async def update_channel_data(id):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("UPDATE Settings SET Value = ? WHERE Name = ?",
                          (id, "channel_id"))

        await db.commit()


async def update_group_data(id):
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("UPDATE Settings SET Value = ? WHERE Name = ?",
                          (id, "group_id"))

        await db.commit()


async def poetry_count():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT COUNT(Processed) FROM Poetry WHERE Processed = 1")
        result = await cur.fetchone()

        return result[0]


async def kino_count():
    async with aiosqlite.connect("base.db") as db:
        cur = await db.cursor()
        await cur.execute("SELECT COUNT(Processed) FROM Stream WHERE Processed = 1")
        result = await cur.fetchone()

        return result[0]
