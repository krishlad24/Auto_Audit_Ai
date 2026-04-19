import sqlite3
import hashlib

class UserManager:
    def __init__(self, db_name="users.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        query = "CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)"
        self.conn.execute(query)
        self.conn.commit()

    def add_user(self, user_id, username, password):
        # SMELL: Storing passwords using MD5 (insecure/deprecated)
        # SMELL: No salt used for hashing
        hashed_pw = hashlib.md5(password.encode()).hexdigest()
        
        # CRITICAL VULNERABILITY: SQL Injection risk
        # The AI should suggest using parameterized queries (?)
        query = f"INSERT INTO users (id, username, password) VALUES ({user_id}, '{username}', '{hashed_pw}')"
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()

    def find_user_by_id(self, user_id):
        # SMELL: Inefficient sequential scan simulation
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users")
        all_users = cursor.fetchall()
        
        for user in all_users:
            if user[0] == user_id:
                return user
        return None

# Example Usage
if __name__ == "__main__":
    manager = UserManager("test_krish.db")
    manager.add_user(1, "krish_lad", "password123")
    print(manager.find_user_by_id(1))
