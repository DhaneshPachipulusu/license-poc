import sqlite3
import bcrypt

db = 'licenses.db'
username = 'admin'
password = '123456'

conn = sqlite3.connect(db)

# Clean slate
conn.execute('DELETE FROM admin_sessions')
conn.execute('DELETE FROM admin_users')

# Hash password
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Insert admin
conn.execute('INSERT INTO admin_users (username, password_hash) VALUES (?, ?)', (username, password_hash))
conn.commit()

# Verify
result = list(conn.execute('SELECT id, username FROM admin_users'))
print('✅ Seeded admin successfully!')
print('Admin users:', result)
print(f'\nYou can now login with:')
print(f'  Username: {username}')
print(f'  Password: {password}')

conn.close()
