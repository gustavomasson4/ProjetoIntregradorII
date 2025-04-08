import sqlite3
import bcrypt
import tkinter as tk
from tkinter import messagebox, ttk

#configuração do banco de dados
def criar_banco_dados():
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

#funções de segurança
def cadastrar_usuario(email, senha):
    try:
        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt)
        
        conn = sqlite3.connect('usuarios.db')
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO usuarios (email, senha_hash) VALUES (?, ?)', 
                      (email, senha_hash))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Erro ao cadastrar: {e}")
        return False

def verificar_login(email, senha):
    try:
        conn = sqlite3.connect('usuarios.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT senha_hash FROM usuarios WHERE email = ?', (email,))
        resultado = cursor.fetchone()
        
        conn.close()
        
        if resultado:
            return bcrypt.checkpw(senha.encode('utf-8'), resultado[0])
        return False
    except Exception as e:
        print(f"Erro ao verificar login: {e}")
        return False

#interface gráfica responsiva
class ResponsiveLoginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Login Responsivo")
        
        #obter dimensões da tela
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        #definir tamanho da janela (80% da tela)
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        #centralizar janela
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        self.root.minsize(int(screen_width * 0.5), int(screen_height * 0.5))
        
        #criar banco de dados
        criar_banco_dados()
        
        #estilo
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12), padding=10)
        self.style.configure('TEntry', font=('Arial', 12), padding=8)
        
        #frame principal
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        #frame do formulário (centralizado)
        self.form_frame = ttk.Frame(self.main_frame)
        self.form_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        #widgets
        self.label_email = ttk.Label(self.form_frame, text="Email:")
        self.label_senha = ttk.Label(self.form_frame, text="Senha:")
        
        self.entry_email = ttk.Entry(self.form_frame, width=30)
        self.entry_senha = ttk.Entry(self.form_frame, width=30, show="*")
        
        self.btn_frame = ttk.Frame(self.form_frame)
        self.btn_login = ttk.Button(self.btn_frame, text="Login", command=self.fazer_login)
        self.btn_cadastrar = ttk.Button(self.btn_frame, text="Cadastrar", command=self.abrir_tela_cadastro)
        
        #layout responsivo
        self.label_email.grid(row=0, column=0, sticky="e", pady=10, padx=5)
        self.label_senha.grid(row=1, column=0, sticky="e", pady=10, padx=5)
        
        self.entry_email.grid(row=0, column=1, pady=10, padx=5)
        self.entry_senha.grid(row=1, column=1, pady=10, padx=5)
        
        self.btn_frame.grid(row=2, columnspan=2, pady=20)
        self.btn_login.pack(side='left', padx=10)
        self.btn_cadastrar.pack(side='left', padx=10)
        
        #configurar redimensionamento
        self.root.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event):
        #ajustar tamanho da fonte baseado na altura da janela
        new_font_size = max(10, int(self.root.winfo_height() / 50))
        self.style.configure('TLabel', font=('Arial', new_font_size))
        self.style.configure('TButton', font=('Arial', new_font_size))
        self.style.configure('TEntry', font=('Arial', new_font_size))
    
    def fazer_login(self):
        email = self.entry_email.get()
        senha = self.entry_senha.get()
        
        if not email or not senha:
            messagebox.showerror("Erro", "Preencha todos os campos!")
            return
        
        if verificar_login(email, senha):
            messagebox.showinfo("Sucesso", "Login realizado com sucesso!")
            #abrir aplicação principal aqui
        else:
            messagebox.showerror("Erro", "Email ou senha incorretos!")
    
    def abrir_tela_cadastro(self):
        self.tela_cadastro = tk.Toplevel(self.root)
        self.tela_cadastro.title("Cadastro de Usuário")
        
        #centralizar janela de cadastro
        window_width = int(self.root.winfo_width() * 0.8)
        window_height = int(self.root.winfo_height() * 0.8)
        position_x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        position_y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        
        self.tela_cadastro.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        #frame do formulário
        form_frame = ttk.Frame(self.tela_cadastro)
        form_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        #widgets
        labels = ["Email:", "Senha:", "Confirmar Senha:"]
        self.entries = []
        
        for i, text in enumerate(labels):
            label = ttk.Label(form_frame, text=text)
            entry = ttk.Entry(form_frame, width=30, show="*" if i > 0 else "")
            label.grid(row=i, column=0, sticky="e", pady=10, padx=5)
            entry.grid(row=i, column=1, pady=10, padx=5)
            self.entries.append(entry)
        
        btn_cadastrar = ttk.Button(form_frame, text="Cadastrar", 
                                 command=lambda: self.realizar_cadastro(
                                     self.entries[0].get(),
                                     self.entries[1].get(),
                                     self.entries[2].get()
                                 ))
        btn_cadastrar.grid(row=3, columnspan=2, pady=20)
    
    def realizar_cadastro(self, email, senha, conf_senha):
        if not all([email, senha, conf_senha]):
            messagebox.showerror("Erro", "Preencha todos os campos!")
            return
        
        if senha != conf_senha:
            messagebox.showerror("Erro", "As senhas não coincidem!")
            return
        
        if len(senha) < 6:
            messagebox.showerror("Erro", "A senha deve ter pelo menos 6 caracteres!")
            return
        
        if cadastrar_usuario(email, senha):
            messagebox.showinfo("Sucesso", "Cadastro realizado com sucesso!")
            self.tela_cadastro.destroy()
        else:
            messagebox.showerror("Erro", "Email já cadastrado!")

#iniciar aplicação
if __name__ == "__main__":
    root = tk.Tk()
    app = ResponsiveLoginApp(root)
    root.mainloop()