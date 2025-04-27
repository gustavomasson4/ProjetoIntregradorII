import sqlite3
import bcrypt
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import os
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import warnings
import shutil
from datetime import datetime

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="fitz")

# Database Configuration
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
            messagebox.showerror("Error", "Email already registered!")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {str(e)}")
            return False

    @staticmethod
    def verify_login(email, password):
        """Verify user credentials"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT senha_hash FROM usuarios WHERE email = ?',
                    (email,)
                )
                result = cursor.fetchone()
                
                if result:
                    stored_hash = result[0].encode('utf-8')
                    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Login verification failed: {str(e)}")
            return False

    @staticmethod
    def get_user_id(email):
        """Get user ID by email"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM usuarios WHERE email = ?',
                    (email,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get user ID: {str(e)}")
            return None

    @staticmethod
    def save_file(user_id, filename, filepath, file_type):
        """Save file information to database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO arquivos (usuario_id, nome_arquivo, caminho_arquivo, tipo_arquivo) VALUES (?, ?, ?, ?)',
                    (user_id, filename, filepath, file_type)
                )
                conn.commit()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            return False

    @staticmethod
    def get_user_files(user_id):
        """Get all files for a user"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, nome_arquivo, tipo_arquivo, data_upload FROM arquivos WHERE usuario_id = ? ORDER BY data_upload DESC',
                    (user_id,)
                )
                return cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get files: {str(e)}")
            return []

    @staticmethod
    def get_file_path(file_id):
        """Get file path by file ID"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT caminho_arquivo FROM arquivos WHERE id = ?',
                    (file_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get file path: {str(e)}")
            return None

    @staticmethod
    def delete_file(file_id):
        """Delete a file record from database"""
        try:
            with sqlite3.connect('usuarios.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM arquivos WHERE id = ?',
                    (file_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file: {str(e)}")
            return False

# Improved PDF Viewer Component
class PDFViewer:
    def __init__(self, parent):
        self.parent = parent
        self.current_page = 0
        self.pdf_doc = None
        self.zoom_level = 1.0
        self.image_cache = []
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize all UI components"""
        # Main container
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill='x', pady=5)
        
        # Navigation buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side='left')
        
        self.btn_open = ttk.Button(btn_frame, text="Open PDF", command=self.open_pdf)
        self.btn_open.pack(side='left', padx=5)
        
        self.btn_prev = ttk.Button(
            btn_frame, 
            text="◄ Previous", 
            command=self.prev_page,
            state='disabled'
        )
        self.btn_prev.pack(side='left', padx=5)
        
        self.btn_next = ttk.Button(
            btn_frame, 
            text="Next ►", 
            command=self.next_page,
            state='disabled'
        )
        self.btn_next.pack(side='left', padx=5)
        
        # Page info
        self.lbl_page = ttk.Label(control_frame, text="Page: 0/0")
        self.lbl_page.pack(side='left', padx=20)
        
        # Zoom controls
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(side='right')
        
        ttk.Label(zoom_frame, text="Zoom:").pack(side='left', padx=5)
        
        self.zoom_var = tk.StringVar(value="100%")
        zoom_menu = ttk.OptionMenu(
            zoom_frame,
            self.zoom_var,
            "100%",
            "50%", "75%", "100%", "125%", "150%", "200%",
            command=self.change_zoom
        )
        zoom_menu.pack(side='left')

        # PDF display area
        self.setup_pdf_display()

    def setup_pdf_display(self):
        """Setup the PDF display area with scrollbars"""
        # Container for canvas and scrollbars
        container = ttk.Frame(self.main_frame)
        container.pack(expand=True, fill='both')
        
        # Canvas for PDF display
        self.canvas = tk.Canvas(container, bg='white')
        self.canvas.pack(side='left', expand=True, fill='both')
        
        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(
            container, 
            orient='vertical', 
            command=self.canvas.yview
        )
        v_scroll.pack(side='right', fill='y')
        
        # Horizontal scrollbar
        h_scroll = ttk.Scrollbar(
            container, 
            orient='horizontal', 
            command=self.canvas.xview
        )
        h_scroll.pack(side='bottom', fill='x')
        
        # Configure canvas scrolling
        self.canvas.configure(
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        
        # Frame to hold PDF image
        self.pdf_frame = ttk.Frame(self.canvas)
        self.canvas.create_window(
            (0, 0), 
            window=self.pdf_frame, 
            anchor='nw',
            tags="pdf_frame"
        )
        
        # Bind canvas resize event
        self.canvas.bind("<Configure>", self.center_content)

    def open_pdf(self):
        """Open a PDF file dialog and load the selected file"""
        filepath = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf")]
        )
        
        if filepath:
            try:
                # Close previous PDF if open
                if self.pdf_doc:
                    self.pdf_doc.close()
                    self.image_cache.clear()
                
                # Open new PDF
                self.pdf_doc = fitz.open(filepath)
                self.current_page = 0
                self.render_page()
                self.update_controls()
                
            except Exception as e:
                messagebox.showerror(
                    "Error", 
                    f"Failed to open PDF:\n{str(e)}"
                )

    def render_page(self):
        """Render the current PDF page"""
        # Clear previous page
        for widget in self.pdf_frame.winfo_children():
            widget.destroy()
        
        if not self.pdf_doc or not 0 <= self.current_page < len(self.pdf_doc):
            return
            
        try:
            # Get PDF page
            page = self.pdf_doc.load_page(self.current_page)
            
            # Create image from PDF page
            zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert to PhotoImage and cache it
            photo = ImageTk.PhotoImage(image=img)
            self.image_cache = [photo]  # Keep reference
            
            # Display image
            label = ttk.Label(self.pdf_frame, image=photo)
            label.image = photo  # Keep reference
            label.pack()
            
            # Update canvas scroll region
            self.update_scroll_region()
            
        except Exception as e:
            messagebox.showerror(
                "Error", 
                f"Failed to render page:\n{str(e)}"
            )

    def update_scroll_region(self):
        """Update the scrollable region of the canvas"""
        self.pdf_frame.update_idletasks()
        bbox = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=bbox)
        self.center_content()

    def center_content(self, event=None):
        """Center the PDF content in the canvas"""
        if not hasattr(self, 'pdf_frame') or not self.pdf_frame.winfo_children():
            return
            
        # Get canvas and content dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        content_width = self.pdf_frame.winfo_reqwidth()
        content_height = self.pdf_frame.winfo_reqheight()
        
        # Calculate new position
        x = max((canvas_width - content_width) / 2, 0)
        y = max((canvas_height - content_height) / 2, 0)
        
        # Update position
        self.canvas.coords("pdf_frame", x, y)

    def prev_page(self):
        """Go to previous page"""
        if self.pdf_doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            self.update_controls()

    def next_page(self):
        """Go to next page"""
        if self.pdf_doc and self.current_page < len(self.pdf_doc) - 1:
            self.current_page += 1
            self.render_page()
            self.update_controls()

    def change_zoom(self, value):
        """Change the zoom level"""
        self.zoom_level = float(value.replace("%", "")) / 100
        if self.pdf_doc:
            self.render_page()

    def update_controls(self):
        """Update the state of navigation controls"""
        if self.pdf_doc:
            total_pages = len(self.pdf_doc)
            self.btn_prev.config(state='normal' if self.current_page > 0 else 'disabled')
            self.btn_next.config(state='normal' if self.current_page < total_pages - 1 else 'disabled')
            self.lbl_page.config(text=f"Page: {self.current_page + 1}/{total_pages}")
        else:
            self.btn_prev.config(state='disabled')
            self.btn_next.config(state='disabled')
            self.lbl_page.config(text="Page: 0/0")

# Main Application Window
class MainApplication:
    def __init__(self, root, user_email):
        self.root = root
        self.user_email = user_email
        self.user_id = DatabaseManager.get_user_id(user_email)
        self.notebook = None
        self.pdf_viewer = None
        
        self.configure_window()
        self.create_menu()
        self.setup_interface()

    def configure_window(self):
        """Configure main window settings"""
        self.root.title("PDF Viewer Application")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    def create_menu(self):
        """Create the main menu bar"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Home", command=self.show_home)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # User menu
        user_menu = tk.Menu(menubar, tearoff=0)
        user_menu.add_command(label="Profile", command=self.show_profile)
        user_menu.add_command(label="Settings", command=self.show_settings)
        menubar.add_cascade(label="User", menu=user_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def setup_interface(self):
        """Set up the main interface"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill='both')
        
        # Home tab
        home_tab = ttk.Frame(self.notebook)
        self.notebook.add(home_tab, text="Home")
        
        # PDF Viewer tab
        pdf_tab = ttk.Frame(self.notebook)
        self.notebook.add(pdf_tab, text="PDF Viewer")
        
        # Library tab
        library_tab = ttk.Frame(self.notebook)
        self.notebook.add(library_tab, text="My Library")
        
        self.pdf_viewer = PDFViewer(pdf_tab)
        self.setup_library_tab(library_tab)
        self.show_home()

    def setup_library_tab(self, tab):
        """Set up the library tab interface"""
        # Upload button
        upload_frame = ttk.Frame(tab)
        upload_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            upload_frame,
            text="Upload File",
            command=self.upload_file
        ).pack(side='left', padx=10)
        
        # File list
        self.file_list_frame = ttk.Frame(tab)
        self.file_list_frame.pack(expand=True, fill='both', pady=10)
        
        # Refresh button
        ttk.Button(
            tab,
            text="Refresh List",
            command=self.refresh_file_list
        ).pack(pady=10)
        
        # Load initial file list
        self.refresh_file_list()

    def upload_file(self):
        """Handle file upload"""
        filetypes = [
            ("PDF Files", "*.pdf"),
            ("Text Files", "*.txt"),
            ("Image Files", "*.png *.jpg *.jpeg"),
            ("All Files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Select File to Upload",
            filetypes=filetypes
        )
        
        if filepath:
            filename = os.path.basename(filepath)
            file_type = os.path.splitext(filename)[1].lower()
            
            # Create a directory for user files if it doesn't exist
            user_dir = os.path.join("user_files", str(self.user_id))
            os.makedirs(user_dir, exist_ok=True)
            
            # Copy file to user directory
            dest_path = os.path.join(user_dir, filename)
            try:
                shutil.copy2(filepath, dest_path)
                
                # Save to database
                if DatabaseManager.save_file(self.user_id, filename, dest_path, file_type):
                    messagebox.showinfo("Success", f"File '{filename}' uploaded successfully!")
                    self.refresh_file_list()
                else:
                    os.remove(dest_path)  # Remove the file if database save failed
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload file: {str(e)}")

    def refresh_file_list(self):
        """Refresh the list of files in the library"""
        # Clear current list
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        # Get files from database
        files = DatabaseManager.get_user_files(self.user_id)
        
        if not files:
            ttk.Label(
                self.file_list_frame,
                text="No files found in your library.",
                font=('Arial', 12)
            ).pack(expand=True, pady=50)
            return
        
        # Create a treeview to display files
        columns = ("ID", "Filename", "Type", "Date")
        tree = ttk.Treeview(
            self.file_list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # Configure columns
        tree.column("ID", width=50, anchor='center')
        tree.column("Filename", width=300, anchor='w')
        tree.column("Type", width=100, anchor='center')
        tree.column("Date", width=150, anchor='center')
        
        # Add headings
        for col in columns:
            tree.heading(col, text=col)
        
        # Add files to treeview
        for file in files:
            tree.insert("", "end", values=file)
        
        tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Add buttons for file actions
        button_frame = ttk.Frame(self.file_list_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Open File",
            command=lambda: self.open_selected_file(tree)
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="Delete File",
            command=lambda: self.delete_selected_file(tree)
        ).pack(side='left', padx=10)

    def open_selected_file(self, tree):
        """Open the selected file"""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file first!")
            return
        
        file_id = tree.item(selected_item)['values'][0]
        file_path = DatabaseManager.get_file_path(file_id)
        
        if not file_path:
            messagebox.showerror("Error", "File not found!")
            return
        
        try:
            if file_path.lower().endswith('.pdf'):
                # Open in PDF viewer tab
                self.notebook.select(1)  # Switch to PDF viewer tab
                self.pdf_viewer.pdf_doc = fitz.open(file_path)
                self.pdf_viewer.current_page = 0
                self.pdf_viewer.render_page()
                self.pdf_viewer.update_controls()
            else:
                # Open with default application
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def delete_selected_file(self, tree):
        """Delete the selected file"""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file first!")
            return
        
        file_id = tree.item(selected_item)['values'][0]
        file_path = DatabaseManager.get_file_path(file_id)
        
        if not file_path:
            messagebox.showerror("Error", "File not found!")
            return
        
        if messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this file? This action cannot be undone."
        ):
            try:
                # Delete from filesystem
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete from database
                if DatabaseManager.delete_file(file_id):
                    messagebox.showinfo("Success", "File deleted successfully!")
                    self.refresh_file_list()
                else:
                    messagebox.showerror("Error", "Failed to delete file record!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {str(e)}")

    def show_home(self):
        """Show the home screen"""
        if self.notebook:
            self.notebook.select(0)
            
            # Clear existing widgets
            for child in self.notebook.winfo_children()[0].winfo_children():
                child.destroy()
            
            # Create home screen content
            label = ttk.Label(
                self.notebook.winfo_children()[0],
                text=f"Welcome, {self.user_email}!\nThis is the home screen.", 
                font=('Arial', 16),
                justify='center'
            )
            label.pack(expand=True)
            
            button_frame = ttk.Frame(self.notebook.winfo_children()[0])
            button_frame.pack(pady=20)
            
            ttk.Button(
                button_frame,
                text="Open Profile",
                command=self.show_profile
            ).pack(side='left', padx=10)
            
            ttk.Button(
                button_frame,
                text="Open Settings",
                command=self.show_settings
            ).pack(side='left', padx=10)
            
            ttk.Button(
                button_frame,
                text="Open PDF Viewer",
                command=lambda: self.notebook.select(1)
            ).pack(side='left', padx=10)
            
            ttk.Button(
                button_frame,
                text="Open My Library",
                command=lambda: self.notebook.select(2)
            ).pack(side='left', padx=10)

    def show_profile(self):
        """Show user profile"""
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            # Clear existing widgets
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(
                home_tab,
                text="User Profile",
                font=('Arial', 16)
            )
            label.pack(pady=20)
            
            info_frame = ttk.Frame(home_tab)
            info_frame.pack(pady=10)
            
            ttk.Label(
                info_frame,
                text=f"Email: {self.user_email}"
            ).grid(row=0, column=0, sticky='w', pady=5)
            
            ttk.Label(
                info_frame,
                text="Registration Date: 01/01/2023"
            ).grid(row=1, column=0, sticky='w', pady=5)
            
            ttk.Label(
                info_frame,
                text="Last Login: Today"
            ).grid(row=2, column=0, sticky='w', pady=5)
            
            ttk.Button(
                home_tab,
                text="Back to Home",
                command=self.show_home
            ).pack(pady=20)

    def show_settings(self):
        """Show application settings"""
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            # Clear existing widgets
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(
                home_tab,
                text="Application Settings",
                font=('Arial', 16)
            )
            label.pack(pady=20)
            
            settings_frame = ttk.Frame(home_tab)
            settings_frame.pack(pady=10)
            
            ttk.Checkbutton(
                settings_frame,
                text="Email Notifications"
            ).grid(row=0, column=0, sticky='w', pady=5)
            
            ttk.Checkbutton(
                settings_frame,
                text="Dark Mode"
            ).grid(row=1, column=0, sticky='w', pady=5)
            
            ttk.Label(
                settings_frame,
                text="Theme:"
            ).grid(row=2, column=0, sticky='w', pady=5)
            
            ttk.Combobox(
                settings_frame,
                values=["Light", "Dark", "System"]
            ).grid(row=2, column=1, sticky='w', pady=5)
            
            ttk.Button(
                home_tab,
                text="Back to Home",
                command=self.show_home
            ).pack(pady=20)

    def show_about(self):
        """Show about information"""
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            # Clear existing widgets
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(
                home_tab,
                text="About This Application",
                font=('Arial', 16)
            )
            label.pack(pady=20)
            
            about_text = """PDF Viewer Application
Version 1.0.0
Developed with Python and Tkinter

© 2025 All rights reserved"""
            
            ttk.Label(
                home_tab,
                text=about_text,
                justify='left'
            ).pack(pady=10)
            
            ttk.Button(
                home_tab,
                text="Back to Home",
                command=self.show_home
            ).pack(pady=20)

# Login Window
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
        
        form_frame = ttk.Frame(main_frame)
        form_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        ttk.Label(
            form_frame,
            text="Email:"
        ).grid(row=0, column=0, sticky="e", pady=10, padx=5)
        
        email_entry = ttk.Entry(form_frame, width=30)
        email_entry.grid(row=0, column=1, pady=10, padx=5)
        
        ttk.Label(
            form_frame,
            text="Password:"
        ).grid(row=1, column=0, sticky="e", pady=10, padx=5)
        
        password_entry = ttk.Entry(form_frame, width=30, show="*")
        password_entry.grid(row=1, column=1, pady=10, padx=5)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=2, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Login",
            command=lambda: self.attempt_login(
                email_entry.get(),
                password_entry.get()
            )
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="Register",
            command=lambda: self.show_registration()
        ).pack(side='left', padx=10)

    def attempt_login(self, email, password):
        """Attempt user login"""
        if not email or not password:
            messagebox.showerror("Error", "Please fill in all fields!")
            return
        
        if DatabaseManager.verify_login(email, password):
            messagebox.showinfo("Success", "Login successful!")
            self.launch_main_app(email)
        else:
            messagebox.showerror("Error", "Invalid email or password!")

    def show_registration(self):
        """Show registration dialog"""
        register_window = tk.Toplevel(self.root)
        register_window.title("User Registration")
        
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
        
        ttk.Button(
            form_frame,
            text="Register",
            command=lambda: self.process_registration(
                entries[0].get(),
                entries[1].get(),
                entries[2].get(),
                register_window
            )
        ).grid(row=3, columnspan=2, pady=20)

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

    def launch_main_app(self, email):
        """Launch the main application"""
        self.root.destroy()
        root = tk.Tk()
        MainApplication(root, email)
        root.mainloop()

def main():
    """Application entry point"""
    root = tk.Tk()
    LoginApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()
