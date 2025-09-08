import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager

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
        
        # Botão para entrar sem login
        separator = ttk.Separator(form_frame, orient='horizontal')
        separator.grid(row=3, columnspan=2, sticky='ew', pady=20)
        
        anonymous_label = ttk.Label(
            form_frame,
            text="ou",
            font=('Arial', 10, 'italic')
        )
        anonymous_label.grid(row=4, columnspan=2, pady=5)
        
        ttk.Button(
            form_frame,
            text="Entrar Sem Login",
            command=self.anonymous_login
        ).grid(row=5, columnspan=2, pady=10)
        
        # Info label for anonymous access
        #info_label = ttk.Label(
           ## text="(Acesso limitado - sem salvamento de dados)",
           # font=('Arial', 8, 'italic'),
            #foreground='gray'
       # )
        #info_label.grid(row=6, columnspan=2, pady=5)

    # Entrada sem login
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

    def show_registration(self):
        """Show registration dialog"""
        register_window = tk.Toplevel(self.root)
        register_window.title("User Registration")
        register_window.grab_set()  # Make window modal
        
        # Center the window
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
