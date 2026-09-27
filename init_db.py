import sqlite3
import bcrypt

conn = sqlite3.connect("halisaha.db")
cursor = conn.cursor()

# Tabloları oluştur
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_gk INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rater_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    UNIQUE(rater_id, target_id),
    FOREIGN KEY(rater_id) REFERENCES users(id),
    FOREIGN KEY(target_id) REFERENCES users(id)
)
""")

# 14 Oyuncu Listesi (İlk 2 kişi kaleci olarak işaretlendi)
default_players = [
    ("ali_gk", 1), ("veli_gk", 1),
    ("ahmet", 0), ("mehmet", 0), ("can", 0), ("burak", 0),
    ("mert", 0), ("emre", 0), ("kemal", 0), ("serkan", 0),
    ("oguz", 0), ("tolga", 0), ("hakan", 0), ("selim", 0)
]

# Varsayılan şifre: 1234
salt = bcrypt.gensalt()
hashed_pw = bcrypt.hashpw(b"1234", salt).decode('utf-8')

for username, is_gk in default_players:
    cursor.execute("""
    INSERT OR IGNORE INTO users (username, password_hash, is_gk)
    VALUES (?, ?, ?)
    """, (username, hashed_pw, is_gk))

conn.commit()
conn.close()
print("Veritabanı hazırlandı! 14 oyuncu eklendi (Hepsinin şifresi: 1234).")
