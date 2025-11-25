import sqlite3
import bcrypt
import os
from datetime import datetime, timedelta

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
                    favorito INTEGER DEFAULT 0,
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
                    bbox TEXT,
                    data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (arquivo_id) REFERENCES arquivos (id)
                )
            ''')
            
            # Nova tabela para tokens de recuperação de senha
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER DEFAULT 0,
                    FOREIGN KEY (email) REFERENCES usuarios (email)
                )
            ''')
            
            # Adicionar a coluna favorito se ela não existir (para compatibilidade com DBs existentes)
            try:
                cursor.execute('ALTER TABLE arquivos ADD COLUMN favorito INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass  # Coluna já existe
                
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
    def email_exists(email):
        """Check if email exists in the database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT COUNT(*) FROM usuarios WHERE email = ?',
                    (email,))
                result = cursor.fetchone()
                return result[0] > 0
        except Exception as e:
            print(f"Failed to check email existence: {str(e)}")
            return False

    @staticmethod
    def save_reset_token(email, token):
        """Save password reset token"""
        try:
            # Token expira em 1 hora
            created_at = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
            
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                
                # Marcar tokens anteriores como usados
                cursor.execute(
                    'UPDATE password_reset_tokens SET used = 1 WHERE email = ? AND used = 0',
                    (email,)
                )
                
                # Inserir novo token
                cursor.execute(
                    '''INSERT INTO password_reset_tokens 
                    (email, token, created_at, expires_at, used) 
                    VALUES (?, ?, ?, ?, 0)''',
                    (email, token, created_at, expires_at)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to save reset token: {str(e)}")
            return False

    @staticmethod
    def verify_reset_token(email, token):
        """Verify if reset token is valid and not expired"""
        try:
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''SELECT COUNT(*) FROM password_reset_tokens 
                    WHERE email = ? AND token = ? AND used = 0 AND expires_at > ?''',
                    (email, token, current_time)
                )
                result = cursor.fetchone()
                return result[0] > 0
        except Exception as e:
            print(f"Failed to verify reset token: {str(e)}")
            return False

    @staticmethod
    def reset_password_with_token(email, token, new_password):
        """Reset password using valid token"""
        try:
            # Primeiro verifica se o token é válido
            if not DatabaseManager.verify_reset_token(email, token):
                return False
            
            # Gera hash da nova senha
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt)
            
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                
                # Atualiza a senha
                cursor.execute(
                    'UPDATE usuarios SET senha_hash = ? WHERE email = ?',
                    (password_hash, email)
                )
                
                # Marca o token como usado
                cursor.execute(
                    'UPDATE password_reset_tokens SET used = 1 WHERE email = ? AND token = ?',
                    (email, token)
                )
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Failed to reset password: {str(e)}")
            return False

    @staticmethod
    def cleanup_expired_tokens():
        """Remove expired tokens from database"""
        try:
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM password_reset_tokens WHERE expires_at < ?',
                    (current_time,)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to cleanup tokens: {str(e)}")
            return False

    @staticmethod
    def save_file(user_id, filename, filepath, file_type):
        """Save file information to database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO arquivos (usuario_id, nome_arquivo, caminho_arquivo, tipo_arquivo, favorito) VALUES (?, ?, ?, ?, ?)',
                    (user_id, filename, filepath, file_type, 0))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            return None

    @staticmethod
    def get_user_files(user_id, favorites_only=False):
        """Get all files for a user"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                if favorites_only:
                    cursor.execute(
                        'SELECT id, nome_arquivo, tipo_arquivo, data_upload, favorito FROM arquivos WHERE usuario_id = ? AND favorito = 1 ORDER BY data_upload DESC',
                        (user_id,))
                else:
                    cursor.execute(
                        'SELECT id, nome_arquivo, tipo_arquivo, data_upload, favorito FROM arquivos WHERE usuario_id = ? ORDER BY favorito DESC, data_upload DESC',
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
                # Deletar também as anotações e highlights relacionados
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
                # Primeiro, obter o status atual
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

    # ... (código existente) ...
    
    # ==================== MÉTODOS PARA GRUPOS ====================
    @staticmethod
    def create_group(user_id, name, description="", color="#007acc"):
        """Create a new group for organizing files"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS grupos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER NOT NULL,
                        nome TEXT NOT NULL,
                        descricao TEXT,
                        cor TEXT DEFAULT '#007acc',
                        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                cursor.execute(
                    'INSERT INTO grupos (usuario_id, nome, descricao, cor) VALUES (?, ?, ?, ?)',
                    (user_id, name, description, color)
                )
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
                cursor.execute('''
                    SELECT id, nome, descricao, cor, data_criacao 
                    FROM grupos 
                    WHERE usuario_id = ? 
                    ORDER BY nome
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get groups: {str(e)}")
            return []

    @staticmethod
    def update_group(group_id, name, description, color):
        """Update group information"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE grupos SET nome = ?, descricao = ?, cor = ? WHERE id = ?',
                    (name, description, color, group_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Failed to update group: {str(e)}")
            return False

    @staticmethod
    def delete_group(group_id):
        """Delete a group and unassign all files from it"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE arquivos SET grupo_id = NULL WHERE grupo_id = ?', (group_id,))
                cursor.execute('DELETE FROM grupos WHERE id = ?', (group_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Failed to delete group: {str(e)}")
            return False

    @staticmethod
    def get_group_file_count(group_id):
        """Get number of files in a group"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM arquivos WHERE grupo_id = ?', (group_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Failed to get file count: {str(e)}")
            return 0

    @staticmethod
    def move_file_to_group(file_id, group_id):
        """Move a file to a different group"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE arquivos SET grupo_id = ? WHERE id = ?',
                    (group_id, file_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Failed to move file: {str(e)}")
            return False

    @staticmethod
    def save_file(user_id, filename, filepath, file_type, group_id=None):
        """Save file information to database with optional group"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                
                # Ensure grupo_id column exists
                cursor.execute("PRAGMA table_info(arquivos)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'grupo_id' not in columns:
                    cursor.execute('ALTER TABLE arquivos ADD COLUMN grupo_id INTEGER')
                
                cursor.execute(
                    'INSERT INTO arquivos (usuario_id, nome_arquivo, caminho_arquivo, tipo_arquivo, favorito, grupo_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, filename, filepath, file_type, 0, group_id)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to save file: {str(e)}")
            return None

    @staticmethod
    def get_user_files(user_id, favorites_only=False, group_id=None):
        """Get all files for a user with optional filtering"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                
                # Ensure grupo_id column exists
                cursor.execute("PRAGMA table_info(arquivos)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'grupo_id' not in columns:
                    cursor.execute('ALTER TABLE arquivos ADD COLUMN grupo_id INTEGER')
                
                query = '''
                    SELECT a.id, a.nome_arquivo, a.tipo_arquivo, a.data_upload, a.favorito, 
                           a.grupo_id, g.nome as grupo_nome, g.cor as grupo_cor
                    FROM arquivos a
                    LEFT JOIN grupos g ON a.grupo_id = g.id
                    WHERE a.usuario_id = ?
                '''
                params = [user_id]
                
                if favorites_only:
                    query += ' AND a.favorito = 1'
                
                if group_id is not None:
                    if group_id == -1:
                        query += ' AND a.grupo_id IS NULL'
                    else:
                        query += ' AND a.grupo_id = ?'
                        params.append(group_id)
                
                query += ' ORDER BY a.favorito DESC, a.data_upload DESC'
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get files: {str(e)}")
            return []

    # ==================== MÉTODOS PARA ANOTAÇÕES GERAIS ====================
    @staticmethod
    def criar_anotacao_geral(user_id, titulo, conteudo, arquivo_id=None, grupo_id=None, tags=""):
        """Create a general note"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS anotacoes_gerais (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER NOT NULL,
                        titulo TEXT NOT NULL,
                        conteudo TEXT,
                        arquivo_id INTEGER,
                        grupo_id INTEGER,
                        tags TEXT,
                        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                        data_modificacao TEXT DEFAULT CURRENT_TIMESTAMP,
                        cor TEXT DEFAULT 'yellow',
                        favorito INTEGER DEFAULT 0,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                        FOREIGN KEY (arquivo_id) REFERENCES arquivos (id),
                        FOREIGN KEY (grupo_id) REFERENCES grupos (id)
                    )
                ''')
                cursor.execute('''
                    INSERT INTO anotacoes_gerais 
                    (usuario_id, titulo, conteudo, arquivo_id, grupo_id, tags) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, titulo, conteudo, arquivo_id, grupo_id, tags))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to create note: {str(e)}")
            return None

    @staticmethod
    def get_anotacoes_gerais(user_id):
        """Get all general notes for a user"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ag.id, ag.usuario_id, ag.titulo, ag.conteudo, 
                           ag.arquivo_id, ag.grupo_id, ag.tags, ag.data_criacao, 
                           ag.data_modificacao, ag.cor, ag.favorito,
                           a.nome_arquivo, g.nome as grupo_nome
                    FROM anotacoes_gerais ag
                    LEFT JOIN arquivos a ON ag.arquivo_id = a.id
                    LEFT JOIN grupos g ON ag.grupo_id = g.id
                    WHERE ag.usuario_id = ?
                    ORDER BY ag.data_modificacao DESC
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get notes: {str(e)}")
            return []

    @staticmethod
    def atualizar_anotacao_geral(anotacao_id, titulo, conteudo, tags=""):
        """Update a general note"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE anotacoes_gerais 
                    SET titulo = ?, conteudo = ?, tags = ?, 
                        data_modificacao = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (titulo, conteudo, tags, anotacao_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Failed to update note: {str(e)}")
            return False

    @staticmethod
    def deletar_anotacao_geral(anotacao_id):
        """Delete a general note"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM anotacoes_gerais WHERE id = ?', (anotacao_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Failed to delete note: {str(e)}")
            return False

    @staticmethod
    def toggle_favorito_anotacao(anotacao_id):
        """Toggle favorite status of a note"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT favorito FROM anotacoes_gerais WHERE id = ?', (anotacao_id,))
                result = cursor.fetchone()
                if result:
                    current_status = result[0]
                    new_status = 1 if current_status == 0 else 0
                    cursor.execute(
                        'UPDATE anotacoes_gerais SET favorito = ? WHERE id = ?',
                        (new_status, anotacao_id)
                    )
                    conn.commit()
                    return new_status
                return None
        except Exception as e:
            print(f"Failed to toggle favorite: {str(e)}")
            return None

    # ==================== MÉTODOS PARA RECOMENDAÇÕES ====================
    @staticmethod
    def save_user_preferences(user_id, genres, authors, keywords):
        """Save user reading preferences"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER NOT NULL,
                        generos TEXT,
                        autores TEXT,
                        palavras_chave TEXT,
                        data_atualizacao TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                
                # Check if preferences exist
                cursor.execute('SELECT id FROM user_preferences WHERE usuario_id = ?', (user_id,))
                if cursor.fetchone():
                    cursor.execute('''
                        UPDATE user_preferences 
                        SET generos = ?, autores = ?, palavras_chave = ?, 
                            data_atualizacao = CURRENT_TIMESTAMP 
                        WHERE usuario_id = ?
                    ''', (genres, authors, keywords, user_id))
                else:
                    cursor.execute('''
                        INSERT INTO user_preferences (usuario_id, generos, autores, palavras_chave) 
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, genres, authors, keywords))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to save preferences: {str(e)}")
            return False

    @staticmethod
    def get_user_preferences(user_id):
        """Get user reading preferences"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT generos, autores, palavras_chave 
                    FROM user_preferences 
                    WHERE usuario_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'genres': result[0] or '',
                        'authors': result[1] or '',
                        'keywords': result[2] or ''
                    }
                return None
        except Exception as e:
            print(f"Failed to get preferences: {str(e)}")
            return None

    @staticmethod
    def save_book_rating(user_id, book_title, rating, review=""):
        """Save user book rating"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS book_ratings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER NOT NULL,
                        titulo_livro TEXT NOT NULL,
                        avaliacao INTEGER NOT NULL,
                        resenha TEXT,
                        data_avaliacao TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO book_ratings (usuario_id, titulo_livro, avaliacao, resenha) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, book_title, rating, review))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to save rating: {str(e)}")
            return False

    @staticmethod
    def get_user_ratings(user_id):
        """Get all user book ratings"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT titulo_livro, avaliacao, resenha, data_avaliacao 
                    FROM book_ratings 
                    WHERE usuario_id = ? 
                    ORDER BY data_avaliacao DESC
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Failed to get ratings: {str(e)}")
            return []