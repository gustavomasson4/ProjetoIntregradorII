import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
from database import DatabaseManager


class PasswordRecoveryWindow:
    """Window for password recovery functionality"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.setup_window()
        self.setup_ui()

    def setup_window(self):
        """Configure the password recovery window"""
        self.window.title("Recuperação de Senha")
        self.window.grab_set()  # Make window modal
        
        # Center the window
        window_width = 500
        window_height = 280
        position_x = self.parent.winfo_x() + (self.parent.winfo_width() - window_width) // 2
        position_y = self.parent.winfo_y() + (self.parent.winfo_height() - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        # Make window non-resizable
        self.window.resizable(False, False)

    def setup_ui(self):
        """Set up the recovery interface"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Recuperação de Senha",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 15))
        
        # Instructions
        instruction_label = ttk.Label(
            main_frame,
            text="Digite seu email para receber instruções de recuperação:",
            font=('Arial', 10)
        )
        instruction_label.pack(pady=(0, 10))
        
        # Email entry frame
        email_frame = ttk.Frame(main_frame)
        email_frame.pack(pady=10)
        
        ttk.Label(
            email_frame,
            text="Email:",
            font=('Arial', 10)
        ).grid(row=0, column=0, sticky="e", padx=(0, 10))
        
        self.email_entry = ttk.Entry(email_frame, width=35, font=('Arial', 10))
        self.email_entry.grid(row=0, column=1)
        self.email_entry.focus()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)
        
        self.send_button = ttk.Button(
            button_frame,
            text="Enviar Token de Recuperação",
            command=self.send_recovery_email,
            width=25
        )
        self.send_button.pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancelar",
            command=self.window.destroy,
            width=12
        ).pack(side='left', padx=5)
        
        # Separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill='x', pady=15)
        
        # Token entry section
        ttk.Label(
            main_frame,
            text="Já possui um token? Digite-o abaixo:",
            font=('Arial', 10, 'italic')
        ).pack(pady=(0, 10))
        
        token_entry_frame = ttk.Frame(main_frame)
        token_entry_frame.pack()
        
        self.token_entry = ttk.Entry(token_entry_frame, width=35, font=('Arial', 10))
        self.token_entry.pack(side='left', padx=(0, 10))
        
        ttk.Button(
            token_entry_frame,
            text="Usar Token",
            command=self.use_token,
            width=15
        ).pack(side='left')
        
        # Bind Enter keys
        self.email_entry.bind('<Return>', lambda e: self.send_recovery_email())
        self.token_entry.bind('<Return>', lambda e: self.use_token())

    def send_recovery_email(self):
        """Send recovery email to user"""
        email = self.email_entry.get().strip()
        
        if not email:
            messagebox.showerror("Erro", "Por favor, digite seu email!")
            return
        
        if "@" not in email or "." not in email:
            messagebox.showerror("Erro", "Por favor, digite um email válido!")
            return
        
        # Disable button to prevent multiple clicks
        self.send_button.config(state='disabled', text="Enviando...")
        self.window.update()
        
        try:
            # Check if user exists
            if not DatabaseManager.user_exists(email):
                # Don't reveal if email exists or not for security
                messagebox.showinfo(
                    "Email Enviado", 
                    "Se o email estiver cadastrado, você receberá as instruções de recuperação em breve."
                )
                self.send_button.config(state='normal', text="Enviar Token de Recuperação")
                return
            
            # Generate token
            token = DatabaseManager.generate_reset_token(email)
            
            if token:
                # Send email (in development, this just prints to console)
                DatabaseManager.send_reset_email(email, token)
                
                messagebox.showinfo(
                    "Token Gerado", 
                    f"Token de recuperação gerado com sucesso!\n\n"
                    f"Para: {email}\n"
                    f"Token: {token}\n\n"
                    f"(Em produção, este token seria enviado por email)\n\n"
                    f"Use o campo 'Token' abaixo para continuar."
                )
            else:
                messagebox.showerror(
                    "Erro", 
                    "Não foi possível gerar o token de recuperação."
                )
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado: {str(e)}")
        finally:
            self.send_button.config(state='normal', text="Enviar Token de Recuperação")

    def use_token(self):
        """Use recovery token to reset password"""
        token = self.token_entry.get().strip()
        
        if not token:
            messagebox.showerror("Erro", "Por favor, digite o token de recuperação!")
            return
        
        try:
            # Validate token
            email, error = DatabaseManager.validate_reset_token(token)
            
            if error:
                messagebox.showerror("Token Inválido", error)
                return
            
            # Token is valid, show password reset dialog
            self.show_password_reset_dialog(token, email)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado: {str(e)}")

    def show_password_reset_dialog(self, token, email):
        """Show dialog to reset password"""
        reset_window = tk.Toplevel(self.window)
        reset_window.title("Redefinir Senha")
        reset_window.grab_set()
        
        # Center the window
        window_width = 420
        window_height = 280
        position_x = self.window.winfo_x() + (self.window.winfo_width() - window_width) // 2
        position_y = self.window.winfo_y() + (self.window.winfo_height() - window_height) // 2
        reset_window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        reset_window.resizable(False, False)
        
        main_frame = ttk.Frame(reset_window, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        ttk.Label(
            main_frame,
            text="Redefinir Senha",
            font=('Arial', 14, 'bold')
        ).pack(pady=(0, 15))
        
        # Show email
        ttk.Label(
            main_frame,
            text=f"Redefinindo senha para: {email}",
            font=('Arial', 10),
            foreground='blue'
        ).pack(pady=(0, 20))
        
        # Password fields
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack()
        
        ttk.Label(
            fields_frame,
            text="Nova senha:"
        ).grid(row=0, column=0, sticky="e", pady=10, padx=5)
        
        password_entry = ttk.Entry(fields_frame, width=25, show="*", font=('Arial', 10))
        password_entry.grid(row=0, column=1, pady=10, padx=5)
        password_entry.focus()
        
        ttk.Label(
            fields_frame,
            text="Confirmar senha:"
        ).grid(row=1, column=0, sticky="e", pady=10, padx=5)
        
        confirm_entry = ttk.Entry(fields_frame, width=25, show="*", font=('Arial', 10))
        confirm_entry.grid(row=1, column=1, pady=10, padx=5)
        
        # Password requirements
        ttk.Label(
            main_frame,
            text="A senha deve ter pelo menos 6 caracteres",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        ).pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)
        
        def reset_password():
            new_password = password_entry.get()
            confirm_password = confirm_entry.get()
            
            if not new_password or not confirm_password:
                messagebox.showerror("Erro", "Por favor, preencha todos os campos!")
                return
            
            if new_password != confirm_password:
                messagebox.showerror("Erro", "As senhas não coincidem!")
                return
            
            if len(new_password) < 6:
                messagebox.showerror("Erro", "A senha deve ter pelo menos 6 caracteres!")
                return
            
            try:
                success, message = DatabaseManager.reset_password_with_token(token, new_password)
                
                if success:
                    messagebox.showinfo("Sucesso", "Senha alterada com sucesso!\n\nVocê já pode fazer login com a nova senha.")
                    reset_window.destroy()
                    self.window.destroy()
                else:
                    messagebox.showerror("Erro", message)
                    
            except Exception as e:
                messagebox.showerror("Erro", f"Erro inesperado: {str(e)}")
        
        ttk.Button(
            button_frame,
            text="Redefinir Senha",
            command=reset_password,
            width=18
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancelar",
            command=reset_window.destroy,
            width=12
        ).pack(side='left', padx=5)
        
        # Bind Enter key
        password_entry.bind('<Return>', lambda e: confirm_entry.focus())
        confirm_entry.bind('<Return>', lambda e: reset_password())


class TokenValidationWindow:
    """Standalone window for token validation (for development testing)"""
    
    def __init__(self, parent=None):
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.setup_window()
        self.setup_ui()

    def setup_window(self):
        """Configure the token validation window"""
        self.window.title("Validar Token de Recuperação")
        
        # Center the window
        window_width = 400
        window_height = 180
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        self.window.resizable(False, False)

    def setup_ui(self):
        """Set up the token validation interface"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        ttk.Label(
            main_frame,
            text="Validar Token de Recuperação",
            font=('Arial', 14, 'bold')
        ).pack(pady=(0, 20))
        
        # Token entry
        token_frame = ttk.Frame(main_frame)
        token_frame.pack(pady=10)
        
        ttk.Label(
            token_frame,
            text="Token:"
        ).grid(row=0, column=0, sticky="e", padx=5)
        
        self.token_entry = ttk.Entry(token_frame, width=35, font=('Arial', 10))
        self.token_entry.grid(row=0, column=1, padx=5)
        self.token_entry.focus()
        
        # Button
        ttk.Button(
            main_frame,
            text="Validar Token",
            command=self.validate_token,
            width=20
        ).pack(pady=20)
        
        self.token_entry.bind('<Return>', lambda e: self.validate_token())

    def validate_token(self):
        """Validate the entered token"""
        token = self.token_entry.get().strip()
        
        if not token:
            messagebox.showerror("Erro", "Por favor, digite um token!")
            return
        
        try:
            email, error = DatabaseManager.validate_reset_token(token)
            
            if error:
                messagebox.showerror("Token Inválido", error)
            else:
                messagebox.showinfo("Token Válido", f"Token válido para o email:\n{email}")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado: {str(e)}")


class PasswordRecoveryTestApp:
    """Application for testing password recovery functionality"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Teste de Recuperação de Senha")
        self.setup_window()
        self.setup_ui()
        
        # Initialize database
        try:
            DatabaseManager.initialize()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao inicializar banco: {str(e)}")

    def setup_window(self):
        """Configure main test window"""
        window_width = 420
        window_height = 400
        
        # Center the window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        self.root.resizable(False, False)

    def setup_ui(self):
        """Set up the test interface"""
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        ttk.Label(
            main_frame,
            text="Sistema de Testes",
            font=('Arial', 16, 'bold')
        ).pack(pady=(0, 10))
        
        ttk.Label(
            main_frame,
            text="Recuperação de Senha",
            font=('Arial', 12)
        ).pack(pady=(0, 25))
        
        # Test buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(expand=True)
        
        buttons = [
            ("Testar Recuperação Completa", self.test_full_recovery),
            ("Validar Token Existente", self.test_token_validation),
            ("Criar Usuário de Teste", self.create_test_user),
            ("Ver Tokens no Banco", self.show_database_tokens),
            ("Limpar Tokens Expirados", self.clean_expired_tokens),
            ("Sair", self.root.quit)
        ]
        
        for text, command in buttons:
            ttk.Button(
                button_frame,
                text=text,
                command=command,
                width=30
            ).pack(pady=5)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Pronto para testes",
            font=('Arial', 9),
            foreground='green'
        )
        self.status_label.pack(side='bottom', pady=15)

    def test_full_recovery(self):
        """Test the full recovery process"""
        try:
            PasswordRecoveryWindow(self.root)
            self.update_status("Janela de recuperação aberta", "blue")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir recuperação: {str(e)}")
            self.update_status("Erro ao abrir recuperação", "red")

    def test_token_validation(self):
        """Test token validation"""
        try:
            TokenValidationWindow(self.root)
            self.update_status("Janela de validação aberta", "blue")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir validação: {str(e)}")
            self.update_status("Erro ao abrir validação", "red")

    def create_test_user(self):
        """Create a test user for testing"""
        test_email = "teste@email.com"
        test_password = "123456"
        
        try:
            if DatabaseManager.register_user(test_email, test_password):
                messagebox.showinfo(
                    "Usuário Criado", 
                    f"Usuário de teste criado com sucesso!\n\n"
                    f"Email: {test_email}\n"
                    f"Senha: {test_password}"
                )
                self.update_status("Usuário de teste criado", "green")
            else:
                messagebox.showwarning(
                    "Aviso", 
                    f"Usuário já existe ou erro ao criar.\n\n"
                    f"Se já existe, use:\n"
                    f"Email: {test_email}\n"
                    f"Senha: {test_password}"
                )
                self.update_status("Usuário já existe", "orange")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar usuário: {str(e)}")
            self.update_status("Erro ao criar usuário", "red")

    def show_database_tokens(self):
        """Show tokens in database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT email, token, created_at, expires_at, used 
                    FROM password_reset_tokens 
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''')
                tokens = cursor.fetchall()
            
            if not tokens:
                messagebox.showinfo("Tokens", "Nenhum token encontrado no banco de dados")
                self.update_status("Nenhum token no banco", "orange")
                return
            
            # Create window to show tokens
            tokens_window = tk.Toplevel(self.root)
            tokens_window.title("Tokens no Banco de Dados")
            tokens_window.geometry("700x350")
            
            # Create frame
            frame = ttk.Frame(tokens_window, padding=10)
            frame.pack(expand=True, fill='both')
            
            # Create treeview
            columns = ("Email", "Token", "Criado", "Expira", "Usado")
            tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
            
            # Configure columns
            tree.column("Email", width=150)
            tree.column("Token", width=180)
            tree.column("Criado", width=120)
            tree.column("Expira", width=120)
            tree.column("Usado", width=80)
            
            for col in columns:
                tree.heading(col, text=col)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            tree.pack(side='left', expand=True, fill='both')
            scrollbar.pack(side='right', fill='y')
            
            # Add data
            for token_data in tokens:
                email, token, created, expires, used = token_data
                used_text = "Sim" if used else "Não"
                token_short = token[:25] + "..." if len(token) > 25 else token
                tree.insert("", "end", values=(
                    email, 
                    token_short,
                    created[:19], 
                    expires[:19], 
                    used_text
                ))
            
            self.update_status(f"{len(tokens)} token(s) exibido(s)", "green")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao buscar tokens: {str(e)}")
            self.update_status("Erro ao buscar tokens", "red")

    def clean_expired_tokens(self):
        """Clean expired tokens from database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                
                # Count expired tokens
                cursor.execute('''
                    SELECT COUNT(*) FROM password_reset_tokens 
                    WHERE datetime(expires_at) < datetime('now')
                ''')
                expired_count = cursor.fetchone()[0]
                
                if expired_count == 0:
                    messagebox.showinfo("Limpeza", "Nenhum token expirado encontrado")
                    self.update_status("Nenhum token expirado", "green")
                    return
                
                # Delete expired tokens
                cursor.execute('''
                    DELETE FROM password_reset_tokens 
                    WHERE datetime(expires_at) < datetime('now')
                ''')
                conn.commit()
                
                messagebox.showinfo(
                    "Limpeza Concluída", 
                    f"{expired_count} token(s) expirado(s) removido(s) do banco de dados"
                )
                self.update_status(f"{expired_count} token(s) limpo(s)", "green")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao limpar tokens: {str(e)}")
            self.update_status("Erro na limpeza", "red")

    def update_status(self, message, color="green"):
        """Update status label"""
        self.status_label.config(text=message, foreground=color)

    def run(self):
        """Run the test application"""
        self.root.mainloop()


# Main execution functions
def test_password_recovery():
    """Simple test for password recovery"""
    root = tk.Tk()
    root.withdraw()
    
    try:
        DatabaseManager.initialize()
        PasswordRecoveryWindow(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao iniciar: {str(e)}")


def test_token_validation():
    """Simple test for token validation"""
    try:
        DatabaseManager.initialize()
        root = tk.Tk()
        root.withdraw()
        TokenValidationWindow()
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao iniciar: {str(e)}")


def run_full_tests():
    """Run comprehensive test application"""
    try:
        app = PasswordRecoveryTestApp()
        app.run()
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar aplicação de testes:\n{str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_password_recovery()
        elif sys.argv[1] == "validate":
            test_token_validation()
        elif sys.argv[1] == "full":
            run_full_tests()
        else:
            print("Opções disponíveis:")
            print("  python password_recovery.py          - Executa aplicação completa de testes")
            print("  python password_recovery.py test     - Testa recuperação de senha")
            print("  python password_recovery.py validate - Testa validação de token")
            print("  python password_recovery.py full     - Aplicação completa de testes")
    else:
        # Run full test application by default
        run_full_tests()