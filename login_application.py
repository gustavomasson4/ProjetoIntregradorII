import tkinter as tk
from tkinter import ttk, messagebox
from database_manager import DatabaseManager
from main_application import MainApplication

class LoginApplication:
    def __init__(self, root):
        self.root = root
        DatabaseManager.initialize()
        self.setup_ui()

    def setup_ui(self):
        """Setup UI components for login"""
        self.root.title("Login System")
        self.root.geometry("400x300")
        self.root.resizable(False, False)

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill='both')

        # Email and Password Fields
        ttk.Label(main_frame, text="Email:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.email_entry = ttk.Entry(main_frame, width=30)
        self.email_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(main_frame, text="Password:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.password_entry = ttk.Entry(main_frame, width=30, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        # Login and Register Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Login", command=self.attempt_login).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Register", command=self.show_registration).pack(side='left', padx=10)

    def attempt_login(self):
        """Attempt to log the user in"""
        email = self.email_entry.get()
        password = self.password_entry.get()

        if not email or not password:
            messagebox.showerror("Error", "Please fill in all fields!")
            return

        if DatabaseManager.verify_login(email, password):
            messagebox.showinfo("Success", "Login successful!")
            self.launch_main_app(email)
        else:
            messagebox.showerror("Error", "Invalid email or password!")

    def show_registration(self):
        """Show the registration dialog"""
        register_window = tk.Toplevel(self.root)
        register_window.title("Register")
        register_window.geometry("400x250")

        ttk.Label(register_window, text="Email:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        email_entry = ttk.Entry(register_window, width=30)
        email_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(register_window, text="Password:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        password_entry = ttk.Entry(register_window, width=30, show="*")
        password_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(register_window, text="Confirm Password:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        confirm_password_entry = ttk.Entry(register_window, width=30, show="*")
        confirm_password_entry.grid(row=2, column=1, padx=5, pady=5)

        def process_registration():
            email = email_entry.get()
            password = password_entry.get()
            confirm_password = confirm_password_entry.get()

            if not email or not password or not confirm_password:
                messagebox.showerror("Error", "Please fill in all fields!")
                return

            if password != confirm_password:
                messagebox.showerror("Error", "Passwords do not match!")
                return

            if DatabaseManager.register_user(email, password):
                messagebox.showinfo("Success", "Registration successful!")
                register_window.destroy()
            else:
                messagebox.showerror("Error", "Email already in use!")

        ttk.Button(register_window, text="Register", command=process_registration).grid(row=3, columnspan=2, pady=20)

    def launch_main_app(self, email):
        """Launch the main application"""
        self.root.destroy()  # Close the login window
        root = tk.Tk()
        app = MainApplication(root, email)  # Pass the logged-in user's email to the MainApplication
        root.mainloop()