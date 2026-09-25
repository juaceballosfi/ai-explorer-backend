from dotenv import load_dotenv
import mysql.connector
import os

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

def init_db():
    print("Initializing database...")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(255),
            size          INT,
            local_url     VARCHAR(255),
            upload_date    DATETIME,
            analysis_result JSON
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")
