import sqlite3

with sqlite3.connect("data/news.db") as conn:
    cur = conn.cursor()
    cur.execute("ALTER TABLE articles ADD COLUMN preprocessed_content TEXT")
