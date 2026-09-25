from dotenv import load_dotenv
import mysql.connector
import os

load_dotenv()

def get_connection():
    """
    Crea y devuelve una nueva conexión a la base de datos MySQL.
    
    Utiliza las credenciales y configuración proporcionadas a través de 
    variables de entorno. Es responsabilidad del llamador cerrar la conexión 
    una vez finalizadas las operaciones.
    
    Returns:
        mysql.connector.connection.MySQLConnection: Objeto de conexión activa a la BD.
    """
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

def init_db():
    """
    Inicializa la estructura de la base de datos necesaria para la aplicación.
    
    Se ejecuta al iniciar la aplicación para asegurar que las tablas requeridas 
    existan:
    - `documents`: Almacena los metadatos y análisis de los archivos subidos.
    - `chat_messages`: Almacena el historial conversacional asociado a cada documento.
    """
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            document_id INT NOT NULL,
            role        ENUM('user', 'assistant') NOT NULL,
            content     TEXT NOT NULL,
            created_at  DATETIME NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")
