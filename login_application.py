import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager
import secrets
import string

class LoginApplication:
    def __init__(self, root):
        self.root = root
        self.configure_window()
        DatabaseManager.initialize()
        self.setup_ui()

    def configure_window(self):
        """Configure login window settings"""
        self.root.title("Login System")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.4)
        window_height = int(screen_height * 0.4)
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    def setup_ui(self):
        """Set up login interface"""
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Sistema de Login",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        form_frame = ttk.Frame(main_frame)
        form_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Login form
        ttk.Label(
            form_frame,
            text="Email:"
        ).grid(row=0, column=0, sticky="e", pady=10, padx=5)
        
        self.email_entry = ttk.Entry(form_frame, width=30)
        self.email_entry.grid(row=0, column=1, pady=10, padx=5)
        
        ttk.Label(
            form_frame,
            text="Password:"
        ).grid(row=1, column=0, sticky="e", pady=10, padx=5)
        
        self.password_entry = ttk.Entry(form_frame, width=30, show="*")
        self.password_entry.grid(row=1, column=1, pady=10, padx=5)
        
        # Buttons frame
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=2, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Login",
            command=self.attempt_login
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Register",
            command=self.show_registration
        ).pack(side='left', padx=5)
        
        # Link para recuperar senha
        forgot_link = ttk.Label(
            form_frame,
            text="Esqueci minha senha",
            foreground='blue',
            cursor='hand2',
            font=('Arial', 9, 'underline')
        )
        forgot_link.grid(row=3, columnspan=2, pady=10)
        forgot_link.bind("<Button-1>", lambda e: self.show_password_recovery())
        
        # Separador
        separator = ttk.Separator(form_frame, orient='horizontal')
        separator.grid(row=4, columnspan=2, sticky='ew', pady=20)
        
        anonymous_label = ttk.Label(
            form_frame,
            text="ou",
            font=('Arial', 10, 'italic')
        )
        anonymous_label.grid(row=5, columnspan=2, pady=5)
        
        ttk.Button(
            form_frame,
            text="Entrar Sem Login",
            command=self.anonymous_login
        ).grid(row=6, columnspan=2, pady=10)

    def attempt_login(self):
        """Attempt user login"""
        email = self.email_entry.get()
        password = self.password_entry.get()
        
        if not email or not password:
            messagebox.showerror("Error", "Please fill in all fields!")
            return
        
        if DatabaseManager.verify_login(email, password):
            messagebox.showinfo("Success", "Login successful!")
            self.launch_main_app(email, is_anonymous=False)
        else:
            messagebox.showerror("Error", "Invalid email or password!")

    def anonymous_login(self):
        """Handle anonymous login"""
        result = messagebox.askyesno(
            "Acesso Anônimo",
            "Deseja entrar anonimamente?\n\n"
            "Nota: No modo anônimo:\n"
            "• Seus dados não serão salvos\n"
            "• Algumas funcionalidades podem ser limitadas\n"
        )
        
        if result:
            self.launch_main_app("anonymous_user", is_anonymous=True)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("Copiado", "Token copiado para a área de transferência!")

    def show_password_recovery(self):
        """Show password recovery dialog"""
        recovery_window = tk.Toplevel(self.root)
        recovery_window.title("Recuperação de Senha")
        recovery_window.grab_set()
        
        window_width = 450
        window_height = 250
        position_x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        position_y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        recovery_window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        main_frame = ttk.Frame(recovery_window, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        title_label = ttk.Label(
            main_frame,
            text="Recuperar Senha",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        instruction_label = ttk.Label(
            main_frame,
            text="Digite seu email para receber instruções\nde recuperação de senha:",
            justify='center'
        )
        instruction_label.pack(pady=(0, 15))
        
        email_frame = ttk.Frame(main_frame)
        email_frame.pack(pady=10)
        
        ttk.Label(email_frame, text="Email:").pack(side='left', padx=5)
        recovery_email_entry = ttk.Entry(email_frame, width=30)
        recovery_email_entry.pack(side='left', padx=5)
        recovery_email_entry.focus()
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(
            button_frame,
            text="Enviar",
            command=lambda: self.process_password_recovery(
                recovery_email_entry.get(),
                recovery_window
            )
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="Cancelar",
            command=recovery_window.destroy
        ).pack(side='left', padx=10)
        
        recovery_email_entry.bind('<Return>', 
            lambda e: self.process_password_recovery(
                recovery_email_entry.get(), 
                recovery_window
            )
        )

    def process_password_recovery(self, email, window):
        """Process password recovery request"""
        if not email:
            messagebox.showerror("Erro", "Por favor, digite seu email!")
            return
        
        if "@" not in email or "." not in email:
            messagebox.showerror("Erro", "Por favor, digite um email válido!")
            return
        
        if not DatabaseManager.email_exists(email):
            messagebox.showerror(
                "Erro", 
                "Email não encontrado em nosso sistema!"
            )
            return
        
        reset_token = self.generate_reset_token()
        
        if DatabaseManager.save_reset_token(email, reset_token):
            self.simulate_email_sending(email, reset_token, window)
        else:
            messagebox.showerror(
                "Erro", 
                "Erro interno. Tente novamente mais tarde."
            )

    def generate_reset_token(self):
        """Generate a secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(32))

    def simulate_email_sending(self, email, token, window):
        """Simulate email sending (for demo purposes)"""
        window.destroy()
        
        result_window = tk.Toplevel(self.root)
        result_window.title("Email Enviado")
        result_window.grab_set()
        
        window_width = 550
        window_height = 400
        position_x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        position_y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        result_window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        main_frame = ttk.Frame(result_window, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        success_label = ttk.Label(
            main_frame,
            text="✅ Email enviado com sucesso!",
            font=('Arial', 14, 'bold'),
            foreground='green'
        )
        success_label.pack(pady=(0, 20))
        
        instruction_text = f"""Um email foi enviado para: {email}

DEMO - Token de recuperação:"""
        
        instruction_label = ttk.Label(
            main_frame,
            text=instruction_text,
            justify='left',
            wraplength=500
        )
        instruction_label.pack(pady=(0, 10))
        
        # Frame para o token com botão de copiar
        token_frame = ttk.Frame(main_frame)
        token_frame.pack(pady=10, fill='x')
        
        # Token em um Entry (read-only) para facilitar seleção
        token_entry = ttk.Entry(token_frame, width=40, font=('Courier', 10))
        token_entry.insert(0, token)
        token_entry.config(state='readonly')
        token_entry.pack(side='left', padx=(0, 10), expand=True, fill='x')
        
        # Botão de copiar
        copy_btn = ttk.Button(
            token_frame,
            text="📋 Copiar",
            command=lambda: self.copy_to_clipboard(token),
            width=12
        )
        copy_btn.pack(side='left')
        
        note_label = ttk.Label(
            main_frame,
            text="\nEm um sistema real, você receberia um link por email.\nPara esta demonstração, use o token acima na tela de redefinição.",
            justify='center',
            wraplength=500,
            font=('Arial', 9, 'italic')
        )
        note_label.pack(pady=(10, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Redefinir Senha Agora",
            command=lambda: self.show_reset_password_form(email, result_window)
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="Fechar",
            command=result_window.destroy
        ).pack(side='left', padx=10)

    def show_reset_password_form(self, email, parent_window):
        """Show the password reset form"""
        parent_window.destroy()
        
        reset_window = tk.Toplevel(self.root)
        reset_window.title("Redefinir Senha")
        reset_window.grab_set()
        
        window_width = 450
        window_height = 350
        position_x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        position_y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        reset_window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        main_frame = ttk.Frame(reset_window, padding=20)
        main_frame.pack(expand=True, fill='both')
        
        title_label = ttk.Label(
            main_frame,
            text="Redefinir Senha",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(pady=10)
        
        ttk.Label(form_frame, text="Token de Recuperação:").grid(row=0, column=0, sticky="e", pady=10, padx=5)
        token_entry = ttk.Entry(form_frame, width=35)
        token_entry.grid(row=0, column=1, pady=10, padx=5)
        
        ttk.Label(form_frame, text="Nova Senha:").grid(row=1, column=0, sticky="e", pady=10, padx=5)
        new_password_entry = ttk.Entry(form_frame, width=35, show="*")
        new_password_entry.grid(row=1, column=1, pady=10, padx=5)
        
        ttk.Label(form_frame, text="Confirmar Senha:").grid(row=2, column=0, sticky="e", pady=10, padx=5)
        confirm_password_entry = ttk.Entry(form_frame, width=35, show="*")
        confirm_password_entry.grid(row=2, column=1, pady=10, padx=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=30)
        
        ttk.Button(
            button_frame,
            text="Redefinir Senha",
            command=lambda: self.process_password_reset(
                email,
                token_entry.get(),
                new_password_entry.get(),
                confirm_password_entry.get(),
                reset_window
            )
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="Cancelar",
            command=reset_window.destroy
        ).pack(side='left', padx=10)
        
        token_entry.focus()

    def process_password_reset(self, email, token, new_password, confirm_password, window):
        """Process the password reset"""
        if not all([token, new_password, confirm_password]):
            messagebox.showerror("Erro", "Por favor, preencha todos os campos!")
            return
        
        if new_password != confirm_password:
            messagebox.showerror("Erro", "As senhas não coincidem!")
            return
        
        if len(new_password) < 6:
            messagebox.showerror("Erro", "A senha deve ter pelo menos 6 caracteres!")
            return
        
        if DatabaseManager.reset_password_with_token(email, token, new_password):
            messagebox.showinfo(
                "Sucesso", 
                "Senha redefinida com sucesso!\nVocê já pode fazer login com a nova senha."
            )
            window.destroy()
        else:
            messagebox.showerror(
                "Erro", 
                "Token inválido ou expirado!\nSolicite uma nova recuperação de senha."
            )

    def show_registration(self):
        """Show registration dialog"""
        register_window = tk.Toplevel(self.root)
        register_window.title("User Registration")
        register_window.grab_set()
        
        window_width = 400
        window_height = 300
        position_x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        position_y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        register_window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        form_frame = ttk.Frame(register_window, padding=20)
        form_frame.pack(expand=True, fill='both')
        
        labels = ["Email:", "Password:", "Confirm Password:"]
        entries = []
        
        for i, text in enumerate(labels):
            ttk.Label(
                form_frame,
                text=text
            ).grid(row=i, column=0, sticky="e", pady=10, padx=5)
            
            entry = ttk.Entry(
                form_frame,
                width=30,
                show="*" if i > 0 else ""
            )
            entry.grid(row=i, column=1, pady=10, padx=5)
            entries.append(entry)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=3, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Register",
            command=lambda: self.process_registration(
                entries[0].get(),
                entries[1].get(),
                entries[2].get(),
                register_window
            )
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=register_window.destroy
        ).pack(side='left', padx=5)

    def process_registration(self, email, password, confirm_password, window):
        """Process user registration"""
        if not all([email, password, confirm_password]):
            messagebox.showerror("Error", "Please fill in all fields!")
            return
        
        if "@" not in email or "." not in email:
            messagebox.showerror("Error", "Please enter a valid email address!")
            return
        
        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match!")
            return
        
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters!")
            return
        
        if DatabaseManager.register_user(email, password):
            messagebox.showinfo("Success", "Registration successful!")
            window.destroy()
        else:
            messagebox.showerror("Error", "Email already exists or registration failed!")

    def launch_main_app(self, email, is_anonymous=False):
        """Launch the main application"""
        self.root.destroy()
        root = tk.Tk()
        from application import MainApplication
        MainApplication(root, email)
        root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApplication(root)
    root.mainloop()