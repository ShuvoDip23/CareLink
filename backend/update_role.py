import sqlite3
con = sqlite3.connect('carelink.db')
con.execute("UPDATE users SET role='admin' WHERE email='rahulcoc729@gmail.com'")
con.commit()
con.close()
print('User role updated successfully!')
