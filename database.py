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
                CREATE TABLE IF NOT EXISTS grupos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    nome_grupo TEXT NOT NULL,
                    descricao TEXT,
                    cor TEXT DEFAULT '#007acc',
                    data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arquivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    grupo_id INTEGER,
                    nome_arquivo TEXT NOT NULL,
                    caminho_arquivo TEXT NOT NULL,
                    tipo_arquivo TEXT NOT NULL,
                    favorito INTEGER DEFAULT 0,
                    data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                    FOREIGN KEY (grupo_id) REFERENCES grupos (id)
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
                    bbox TEXT,
                    data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (arquivo_id) REFERENCES arquivos (id)
                )
            ''')
            
            # Adicionar colunas se elas não existirem (para compatibilidade com DBs existentes)
            try:
                cursor.execute('ALTER TABLE arquivos ADD COLUMN favorito INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE arquivos ADD COLUMN grupo_id INTEGER REFERENCES grupos (id)')
            except sqlite3.OperationalError:
                pass
                
            conn.commit()

    @staticmethod
    def register_user(email, password):
        """Register a new user in the database"""
        try:
            if not email or "@" not in email or "." not in email:
                return False

            if not password or len(password) < 6:
                return False

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

    # MÉTODOS PARA GRUPOS
    @staticmethod
    def create_group(user_id, nome_grupo, descricao=None, cor='#007acc'):
        """Create a new group for the user"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO grupos (usuario_id, nome_grupo, descricao, cor) VALUES (?, ?, ?, ?)',
                    (user_id, nome_grupo, descricao, cor))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to create group: {str(e)}")
            return None

    @staticmethod
    def get_user_groups(user_id):
        """Get all groups for a user"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, nome_grupo, descricao, cor, data_criacao FROM grupos WHERE usuario_id = ? ORDER BY nome_grupo',
                    (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get groups: {str(e)}")
            return []

    @staticmethod
    def update_group(group_id, nome_grupo, descricao=None, cor=None):
        """Update group information"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE grupos SET nome_grupo = ?, descricao = ?, cor = ? WHERE id = ?',
                    (nome_grupo, descricao, cor, group_id))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to update group: {str(e)}")
            return False

    @staticmethod
    def delete_group(group_id):
        """Delete a group and move files to ungrouped"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                # Move files to ungrouped (NULL group_id)
                cursor.execute('UPDATE arquivos SET grupo_id = NULL WHERE grupo_id = ?', (group_id,))
                # Delete the group
                cursor.execute('DELETE FROM grupos WHERE id = ?', (group_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to delete group: {str(e)}")
            return False

    @staticmethod
    def get_group_file_count(group_id):
        """Get the number of files in a group"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM arquivos WHERE grupo_id = ?', (group_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"Failed to get file count: {str(e)}")
            return 0

    @staticmethod
    def save_file(user_id, filename, filepath, file_type, group_id=None):
        """Save file information to database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO arquivos (usuario_id, grupo_id, nome_arquivo, caminho_arquivo, tipo_arquivo, favorito) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, group_id, filename, filepath, file_type, 0))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            return None

    @staticmethod
    def get_user_files(user_id, favorites_only=False, group_id=None):
        """Get all files for a user, optionally filtered by group"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                
                base_query = '''
                    SELECT a.id, a.nome_arquivo, a.tipo_arquivo, a.data_upload, a.favorito, 
                           a.grupo_id, g.nome_grupo, g.cor
                    FROM arquivos a 
                    LEFT JOIN grupos g ON a.grupo_id = g.id
                    WHERE a.usuario_id = ?
                '''
                
                params = [user_id]
                
                if favorites_only:
                    base_query += ' AND a.favorito = 1'
                
                if group_id is not None:
                    if group_id == -1:  # Special case for ungrouped files
                        base_query += ' AND a.grupo_id IS NULL'
                    else:
                        base_query += ' AND a.grupo_id = ?'
                        params.append(group_id)
                
                base_query += ' ORDER BY a.favorito DESC, a.data_upload DESC'
                
                cursor.execute(base_query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get files: {str(e)}")
            return []

    @staticmethod
    def move_file_to_group(file_id, group_id):
        """Move a file to a different group"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE arquivos SET grupo_id = ? WHERE id = ?',
                    (group_id, file_id))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to move file: {str(e)}")
            return False

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
                cursor.execute('DELETE FROM anotacoes WHERE arquivo_id = ?', (file_id,))
                cursor.execute('DELETE FROM highlights WHERE arquivo_id = ?', (file_id,))
                cursor.execute('DELETE FROM arquivos WHERE id = ?', (file_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to delete file: {str(e)}")
            return False

    @staticmethod
    def toggle_favorite(file_id):
        """Toggle favorite status of a file"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT favorito FROM arquivos WHERE id = ?', (file_id,))
                result = cursor.fetchone()
                if result:
                    current_status = result[0]
                    new_status = 1 if current_status == 0 else 0
                    cursor.execute(
                        'UPDATE arquivos SET favorito = ? WHERE id = ?',
                        (new_status, file_id))
                    conn.commit()
                    return new_status
                return None
        except Exception as e:
            print(f"Failed to toggle favorite: {str(e)}")
            return None

    @staticmethod
    def is_favorite(file_id):
        """Check if a file is marked as favorite"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT favorito FROM arquivos WHERE id = ?', (file_id,))
                result = cursor.fetchone()
                return result[0] == 1 if result else False
        except Exception as e:
            print(f"Failed to check favorite status: {str(e)}")
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