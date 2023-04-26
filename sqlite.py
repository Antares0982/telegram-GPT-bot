#!/usr/bin/env -S python3 -O
import sqlite3

# region blacklist
conn = sqlite3.connect("data/blacklist.db")
c = conn.cursor()
c.execute(
    """CREATE TABLE BLACKLIST
        (TGID    INT     NOT NULL    PRIMARY KEY);"""
)
print("Table created successfully")

conn.commit()
conn.close()

# endregion

# region gpt
conn = sqlite3.connect("data/gpt.db")
c = conn.cursor()
c.execute(
    """CREATE TABLE GPT
        (TGID    INT     NOT NULL    PRIMARY KEY);"""
)
print("Table created successfully")

conn.commit()
conn.close()

# endregion
