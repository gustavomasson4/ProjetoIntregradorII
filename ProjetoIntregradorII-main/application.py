import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import shutil
from database import DatabaseManager
from pdf_viewer import PDFViewer
import fitz

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
        # Search frame
        search_frame = ttk.Frame(tab)
        search_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side='left', padx=5)
        
        ttk.Button(
            search_frame,
            text="Search",
            command=self.search_files
        ).pack(side='left', padx=5)
        
        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side='left', padx=5)
        
        # Upload button
        upload_frame = ttk.Frame(tab)
        upload_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Button(
            upload_frame,
            text="Upload File",
            command=self.upload_file
        ).pack(side='left', padx=5)
        
        # File list
        self.file_list_frame = ttk.Frame(tab)
        self.file_list_frame.pack(expand=True, fill='both', pady=10, padx=10)
        
        # Refresh button
        refresh_frame = ttk.Frame(tab)
        refresh_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Button(
            refresh_frame,
            text="Refresh List",
            command=self.refresh_file_list
        ).pack(side='left', padx=5)
        
        # Bind Enter key to search
        search_entry.bind('<Return>', lambda event: self.search_files())
        
        # Load initial file list
        self.refresh_file_list()

    def search_files(self):
        """Search files based on the search term"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.refresh_file_list()
            return
        
        # Get all files from database
        all_files = DatabaseManager.get_user_files(self.user_id)
        
        if not all_files:
            return
        
        # Filter files based on search term
        filtered_files = [
            file for file in all_files 
            if (search_term in file[1].lower() or  # filename
                search_term in file[2].lower())    # file type
        ]
        
        # Clear current list
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        if not filtered_files:
            ttk.Label(
                self.file_list_frame,
                text="No files found matching your search.",
                font=('Arial', 12)
            ).pack(expand=True, pady=50)
            return
        
        # Create a treeview to display filtered files
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
        
        # Add filtered files to treeview
        for file in filtered_files:
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

    def clear_search(self):
        """Clear the search and show all files"""
        self.search_var.set("")
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
        search_term = self.search_var.get().lower()
        
        if search_term:
            self.search_files()
            return
        
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
        
        file_info = tree.item(selected_item)['values']
        file_id = file_info[0]
        file_path = DatabaseManager.get_file_path(file_id)
        
        if not file_path:
            messagebox.showerror("Error", "File not found!")
            return
        
        try:
            if file_path.lower().endswith('.pdf'):
                # Open in PDF viewer tab
                self.notebook.select(1)  # Switch to PDF viewer tab
                self.pdf_viewer.pdf_doc = fitz.open(file_path)
                self.pdf_viewer.file_id = file_id  # Set the file ID for annotations
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