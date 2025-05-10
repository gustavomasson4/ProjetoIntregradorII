import sqlite3
import bcrypt 

class DatabaseManager:
    @staticmethod
    def initialize():
        """Initialize the database with required tables"""
        with sqlite3.connect('usuarios.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arquivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    nome_arquivo TEXT NOT NULL,
                    caminho_arquivo TEXT NOT NULL,
                    tipo_arquivo TEXT NOT NULL,
                    data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS anotacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arquivo_id INTEGER NOT NULL,
                    pagina INTEGER NOT NULL,
                    x1 REAL NOT NULL,
                    y1 REAL NOT NULL,
                    x2 REAL NOT NULL,
                    y2 REAL NOT NULL,
                    texto TEXT,
                    cor TEXT NOT NULL,
                    FOREIGN KEY (arquivo_id) REFERENCES arquivos (id)
                )
            ''')
            conn.commit()

    @staticmethod
    def register_user(email, password):
        """Register a new user in the database"""
        try:
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO usuarios (email, senha_hash) VALUES (?, ?)',
                    (email, password_hash.decode('utf-8'))
                )
                conn.commit()
                
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"Registration failed: {str(e)}")
            return False

    @staticmethod
    def verify_login(email, password):
        """Verify user credentials"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT senha_hash FROM usuarios WHERE email = ?',
                    (email,))
                result = cursor.fetchone()
                
                if result:
                    stored_hash = result[0].encode('utf-8')
                    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
                return False
        except Exception as e:
            print(f"Login verification failed: {str(e)}")
            return False

    @staticmethod
    def get_user_id(email):
        """Get user ID by email"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM usuarios WHERE email = ?',
                    (email,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Failed to get user ID: {str(e)}")
            return None

    @staticmethod
    def save_file(user_id, filename, filepath, file_type):
        """Save file information to database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO arquivos (usuario_id, nome_arquivo, caminho_arquivo, tipo_arquivo) VALUES (?, ?, ?, ?)',
                    (user_id, filename, filepath, file_type))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            return None

    @staticmethod
    def get_user_files(user_id):
        """Get all files for a user"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, nome_arquivo, tipo_arquivo, data_upload FROM arquivos WHERE usuario_id = ? ORDER BY data_upload DESC',
                    (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get files: {str(e)}")
            return []

    @staticmethod
    def get_annotations(file_id, page):
        """Get all annotations for a specific page of a file"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''SELECT x1, y1, x2, y2, texto, cor 
                    FROM anotacoes 
                    WHERE arquivo_id = ? AND pagina = ?''',
                    (file_id, page))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get annotations: {str(e)}")
            return []