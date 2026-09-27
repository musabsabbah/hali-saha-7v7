import sqlite3
import bcrypt

conn = sqlite3.connect("halisaha.db")
cursor = conn.cursor()

# users tablosuna is_admin sütunu ekle (yoksa)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

# Admin kullanıcısını ekle (Kullanıcı adı: admin / Şifre: admin123)
salt = bcrypt.gensalt()
admin_pw = bcrypt.hashpw(b"admin123", salt).decode('utf-8')

cursor.execute("""
INSERT INTO users (username, password_hash, is_gk, is_admin)
VALUES ('admin', ?, 0, 1)
ON CONFLICT(username) DO UPDATE SET is_admin=1, password_hash=excluded.password_hash
""", (admin_pw,))

conn.commit()
conn.close()
print("Veritabanı güncellendi! 'admin' hesabı tanımlandı (Şifre: admin123).")
