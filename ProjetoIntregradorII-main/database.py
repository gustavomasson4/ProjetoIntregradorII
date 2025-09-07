import sqlite3
import bcrypt
import os

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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS highlights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arquivo_id INTEGER NOT NULL,
                    pagina INTEGER NOT NULL,
                    texto_destacado TEXT NOT NULL,
                    cor TEXT NOT NULL DEFAULT 'yellow',
                    bbox TEXT, -- bounding box opcional: pode ser usado para guardar coordenadas como string JSON
                    data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (arquivo_id) REFERENCES arquivos (id)
                )
            ''')
            conn.commit()

    @staticmethod
    def register_user(email, password):
        """Register a new user in the database"""
        try:
            # Validação básica do email
            if not email or "@" not in email or "." not in email:
                return False

            # Validação da senha
            if not password or len(password) < 6:
                return False

            # Gera o hash da senha
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)

            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO usuarios (email, senha_hash) VALUES (?, ?)',
                    (email, password_hash)
                )
                conn.commit()

            return True
        except sqlite3.IntegrityError:
            # Email já existe
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
                    stored_hash = result[0]
                    # Ajuste para lidar com tipos de bytes e string
                    if isinstance(stored_hash, str):
                        stored_hash = stored_hash.encode('utf-8')
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
    def get_file_path(file_id):
        """Get file path by file ID"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT caminho_arquivo FROM arquivos WHERE id = ?',
                    (file_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Failed to get file path: {str(e)}")
            return None

    @staticmethod
    def delete_file(file_id):
        """Delete a file record from database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM arquivos WHERE id = ?',
                    (file_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to delete file: {str(e)}")
            return False

    @staticmethod
    def save_annotation(file_id, page, x1, y1, x2, y2, text, color):
        """Save an annotation to the database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO anotacoes 
                    (arquivo_id, pagina, x1, y1, x2, y2, texto, cor) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (file_id, page, x1, y1, x2, y2, text, color))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to save annotation: {str(e)}")
            return False

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

    @staticmethod
    def delete_annotation(file_id, page, x1, y1):
        """Delete an annotation from the database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''DELETE FROM anotacoes 
                    WHERE arquivo_id = ? AND pagina = ? AND x1 = ? AND y1 = ?''',
                    (file_id, page, x1, y1))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to delete annotation: {str(e)}")
            return False

    # ----------- MÉTODOS PARA HIGHLIGHTS (MARCA-TEXTO) -----------
    @staticmethod
    def save_highlight(file_id, page, texto_destacado, cor='yellow', bbox=None):
        """Save a highlight (marca-texto) to the database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO highlights 
                    (arquivo_id, pagina, texto_destacado, cor, bbox)
                    VALUES (?, ?, ?, ?, ?)''',
                    (file_id, page, texto_destacado, cor, bbox))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to save highlight: {str(e)}")
            return False

    @staticmethod
    def get_highlights(file_id, page):
        """Get all highlights for a specific page of a file"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''SELECT texto_destacado, cor, bbox, data_criacao
                    FROM highlights
                    WHERE arquivo_id = ? AND pagina = ?''',
                    (file_id, page))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get highlights: {str(e)}")
            return []

    @staticmethod
    def delete_highlight(file_id, page, texto_destacado):
        """Delete a highlight from the database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''DELETE FROM highlights 
                    WHERE arquivo_id = ? AND pagina = ? AND texto_destacado = ?''',
                    (file_id, page, texto_destacado))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to delete highlight: {str(e)}")
            return False