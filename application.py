import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import os
import shutil
from database import DatabaseManager
from pdf_viewer import PDFViewer
from theme_manager import theme_manager
import fitz

# Book download imports
import requests
from urllib.parse import quote

class GroupDialog:
    def __init__(self, parent, user_id, group_data=None):
        self.parent = parent
        self.user_id = user_id
        self.group_data = group_data
        self.result = None
        self.selected_color = group_data[3] if group_data else '#007acc'
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Group" if group_data else "Create New Group")
        self.dialog.grab_set()
        self.dialog.transient(parent)
        
        # Center dialog
        self.dialog.geometry("400x250")
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 400) // 2
        y = (self.dialog.winfo_screenheight() - 250) // 2
        self.dialog.geometry(f"400x250+{x}+{y}")
        
        self.setup_ui()
        self.apply_theme()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Group name
        ttk.Label(main_frame, text="Group Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = tk.StringVar(value=self.group_data[1] if self.group_data else "")
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, columnspan=2, sticky='ew', pady=5)
        
        # Description
        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky='nw', pady=5)
        self.desc_text = tk.Text(main_frame, height=4, width=30)
        self.desc_text.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5)
        if self.group_data and self.group_data[2]:
            self.desc_text.insert('1.0', self.group_data[2])
        
        # Color selection
        ttk.Label(main_frame, text="Color:").grid(row=2, column=0, sticky='w', pady=5)
        
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=2, column=1, columnspan=2, sticky='w', pady=5)
        
        self.color_canvas = tk.Canvas(color_frame, width=30, height=20, bg=self.selected_color)
        self.color_canvas.pack(side='left', padx=(0, 10))
        
        ttk.Button(color_frame, text="Choose Color", command=self.choose_color).pack(side='left')
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self.save_group).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=10)
        
        main_frame.grid_columnconfigure(1, weight=1)
        
    def apply_theme(self):
        """Apply current theme to dialog"""
        theme_manager.apply_theme_to_widget(self.dialog)
        theme_manager.apply_theme_recursive(self.dialog)
        
    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color)[1]
        if color:
            self.selected_color = color
            self.color_canvas.config(bg=color)
            
    def save_group(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Group name is required!")
            return
            
        description = self.desc_text.get('1.0', 'end-1c').strip()
        
        if self.group_data:  # Edit existing group
            if DatabaseManager.update_group(self.group_data[0], name, description, self.selected_color):
                self.result = (name, description, self.selected_color)
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update group!")
        else:  # Create new group
            group_id = DatabaseManager.create_group(self.user_id, name, description, self.selected_color)
            if group_id:
                self.result = (group_id, name, description, self.selected_color)
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to create group!")

class BookDownloadDialog:
    def __init__(self, parent, user_id):
        self.parent = parent
        self.user_id = user_id
        self.result = None
        self.search_results = []
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Download Books from Project Gutenberg")
        self.dialog.grab_set()
        self.dialog.transient(parent)
        
        # Set size
        self.dialog.geometry("800x600")
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 800) // 2
        y = (self.dialog.winfo_screenheight() - 600) // 2
        self.dialog.geometry(f"800x600+{x}+{y}")
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search Book:").pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<Return>', lambda e: self.search_books())
        
        ttk.Button(search_frame, text="Search", command=self.search_books).pack(side='left', padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Search Results", padding=10)
        results_frame.pack(fill='both', expand=True, pady=10)
        
        # Treeview for results
        columns = ("Title", "Author", "Language", "ID")
        self.results_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        self.results_tree.column("Title", width=300)
        self.results_tree.column("Author", width=200)
        self.results_tree.column("Language", width=80)
        self.results_tree.column("ID", width=80)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="Download Selected (TXT)", command=lambda: self.download_selected('txt')).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Download Selected (EPUB)", command=lambda: self.download_selected('epub')).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side='right', padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Enter a search term and click Search")
        self.status_label.pack(pady=5)
    
    def apply_theme(self):
        theme_manager.apply_theme_to_widget(self.dialog)
        theme_manager.apply_theme_recursive(self.dialog)
    
    def search_books(self):
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term!")
            return
        
        self.status_label.config(text="Searching...")
        self.dialog.update()
        
        try:
            # Project Gutenberg API
            url = f"https://gutendex.com/books/?search={quote(search_term)}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Clear previous results
                for item in self.results_tree.get_children():
                    self.results_tree.delete(item)
                
                self.search_results = []
                
                if results:
                    for book in results[:50]:  # Limit to 50 results
                        title = book.get('title', 'Unknown')
                        authors = ', '.join([a.get('name', 'Unknown') for a in book.get('authors', [])])
                        languages = ', '.join(book.get('languages', []))
                        book_id = book.get('id', '')
                        
                        self.results_tree.insert("", "end", values=(title, authors, languages, book_id))
                        self.search_results.append(book)
                    
                    self.status_label.config(text=f"Found {len(results)} books")
                else:
                    self.status_label.config(text="No books found")
            else:
                self.status_label.config(text="Search failed")
                messagebox.showerror("Error", "Failed to search books. Please try again.")
        
        except requests.exceptions.RequestException as e:
            self.status_label.config(text="Network error")
            messagebox.showerror("Error", f"Network error: {str(e)}")
        except Exception as e:
            self.status_label.config(text="Error occurred")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def download_selected(self, format_type):
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a book to download!")
            return
        
        item_values = self.results_tree.item(selection[0])['values']
        book_id = item_values[3]
        title = item_values[0]
        
        # Find the book in search results
        book = None
        for b in self.search_results:
            if b.get('id') == book_id:
                book = b
                break
        
        if not book:
            messagebox.showerror("Error", "Book information not found!")
            return
        
        self.status_label.config(text=f"Downloading {title}...")
        self.dialog.update()
        
        try:
            # Get download URL from formats
            formats = book.get('formats', {})
            download_url = None
            
            if format_type == 'txt':
                download_url = formats.get('text/plain; charset=utf-8') or formats.get('text/plain')
            elif format_type == 'epub':
                download_url = formats.get('application/epub+zip')
            
            if not download_url:
                messagebox.showerror("Error", f"Format {format_type.upper()} not available for this book!")
                self.status_label.config(text="Download failed")
                return
            
            # Download the file
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                # Create directory for downloads
                user_dir = os.path.join("user_files", str(self.user_id), "downloads")
                os.makedirs(user_dir, exist_ok=True)
                
                # Clean filename
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
                safe_title = safe_title[:100]  # Limit filename length
                filename = f"{safe_title}.{format_type}"
                filepath = os.path.join(user_dir, filename)
                
                # Save file
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Save to database
                if DatabaseManager.save_file(self.user_id, filename, filepath, f'.{format_type}'):
                    self.status_label.config(text="Download complete!")
                    messagebox.showinfo("Success", f"Book '{title}' downloaded successfully!")
                    self.result = True
                else:
                    os.remove(filepath)
                    messagebox.showerror("Error", "Failed to save book to database!")
            else:
                messagebox.showerror("Error", "Failed to download book!")
                self.status_label.config(text="Download failed")
        
        except Exception as e:
            messagebox.showerror("Error", f"Download error: {str(e)}")
            self.status_label.config(text="Download failed")

class AnotacaoDialog:
    def __init__(self, parent, user_id, anotacao_data=None):
        self.parent = parent
        self.user_id = user_id
        self.anotacao_data = anotacao_data
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Note" if anotacao_data else "Create New Note")
        self.dialog.geometry("600x500")
        self.dialog.grab_set()
        self.dialog.transient(parent)
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 600) // 2
        y = (self.dialog.winfo_screenheight() - 500) // 2
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        ttk.Label(main_frame, text="Title:").grid(row=0, column=0, sticky='w', pady=5)
        self.titulo_var = tk.StringVar(value=self.anotacao_data[2] if self.anotacao_data else "")
        ttk.Entry(main_frame, textvariable=self.titulo_var, width=50).grid(row=0, column=1, sticky='ew', pady=5)
        
        # Content
        ttk.Label(main_frame, text="Content:").grid(row=1, column=0, sticky='nw', pady=5)
        self.conteudo_text = tk.Text(main_frame, height=15, width=50)
        self.conteudo_text.grid(row=1, column=1, sticky='nsew', pady=5)
        
        if self.anotacao_data and self.anotacao_data[3]:
            self.conteudo_text.insert('1.0', self.anotacao_data[3])
        
        # Metadata
        meta_frame = ttk.Frame(main_frame)
        meta_frame.grid(row=2, column=1, sticky='ew', pady=10)
        
        ttk.Label(meta_frame, text="Tags:").pack(side='left', padx=5)
        self.tags_var = tk.StringVar(value=self.anotacao_data[6] if self.anotacao_data else "")
        ttk.Entry(meta_frame, textvariable=self.tags_var, width=30).pack(side='left', padx=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self.salvar_anotacao).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=10)
        
        # Configure weights
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
    
    def apply_theme(self):
        """Apply current theme to dialog"""
        theme_manager.apply_theme_to_widget(self.dialog)
        theme_manager.apply_theme_recursive(self.dialog)
    
    def salvar_anotacao(self):
        titulo = self.titulo_var.get().strip()
        if not titulo:
            messagebox.showerror("Error", "Title is required!")
            return
        
        conteudo = self.conteudo_text.get('1.0', 'end-1c').strip()
        tags = self.tags_var.get().strip()
        
        if self.anotacao_data:  # Edit
            if DatabaseManager.atualizar_anotacao_geral(
                self.anotacao_data[0], titulo, conteudo, tags
            ):
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update note!")
        else:  # Create new
            anotacao_id = DatabaseManager.criar_anotacao_geral(
                self.user_id, titulo, conteudo, tags=tags
            )
            if anotacao_id:
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to create note!")

class MainApplication:
    def __init__(self, root, user_email):
        self.root = root
        self.user_email = user_email
        self.user_id = DatabaseManager.get_user_id(user_email)
        self.notebook = None
        self.pdf_viewer = None
        self.show_favorites_only = False
        self.selected_group_id = None
        
        # Initialize theme
        theme_manager.register_callback(self.on_theme_change)
        
        self.configure_window()
        self.create_menu()
        self.setup_interface()
        self.apply_theme()

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
        file_menu.add_command(label="Download Books", command=self.show_book_download)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # User menu
        user_menu = tk.Menu(menubar, tearoff=0)
        user_menu.add_command(label="Profile", command=self.show_profile)
        user_menu.add_command(label="Settings", command=self.show_settings)
        menubar.add_cascade(label="User", menu=user_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Dark/Light Theme", command=self.toggle_theme)
        view_menu.add_separator()
        view_menu.add_radiobutton(
            label="Light Theme", 
            command=lambda: self.set_theme('light'),
            variable=tk.StringVar(),
            value='light'
        )
        view_menu.add_radiobutton(
            label="Dark Theme", 
            command=lambda: self.set_theme('dark'),
            variable=tk.StringVar(),
            value='dark'
        )
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def show_book_download(self):
        """Show book download dialog"""
        dialog = BookDownloadDialog(self.root, self.user_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            # Refresh file list after download
            self.refresh_file_list()
            self.refresh_groups_list()

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        theme_manager.toggle_theme()

    def set_theme(self, theme_name):
        """Set specific theme"""
        theme_manager.set_theme(theme_name)

    def on_theme_change(self, theme_name):
        """Callback for when theme changes"""
        self.apply_theme()

    def apply_theme(self):
        """Apply current theme to all widgets"""
        try:
            # Apply TTK theme first
            theme_manager.apply_ttk_theme(self.root)
            
            # Apply to root window
            theme_manager.apply_theme_to_widget(self.root)
            
            # Apply to all child widgets recursively
            theme_manager.apply_theme_recursive(self.root)
            
            # Special handling for PDF viewer canvas
            if self.pdf_viewer and hasattr(self.pdf_viewer, 'canvas'):
                theme = theme_manager.get_theme()
                self.pdf_viewer.canvas.configure(bg=theme['canvas_bg'])
                
        except Exception as e:
            print(f"Error applying theme: {e}")

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
        
        # Notes tab
        notes_tab = ttk.Frame(self.notebook)
        self.notebook.add(notes_tab, text="My Notes")
        
        self.pdf_viewer = PDFViewer(pdf_tab)
        self.setup_library_tab(library_tab)
        self.setup_notes_tab(notes_tab)
        self.show_home()

    def setup_notes_tab(self, tab):
        """Set up the notes tab interface"""
        # Main container
        main_container = ttk.Frame(tab)
        main_container.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Top controls
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill='x', pady=(0, 10))
        
        # New note button
        ttk.Button(
            controls_frame, 
            text="+ New Note", 
            command=self.criar_nova_anotacao
        ).pack(side='left', padx=5)
        
        # Filters
        filter_frame = ttk.Frame(controls_frame)
        filter_frame.pack(side='right')
        
        ttk.Label(filter_frame, text="Filter:").pack(side='left', padx=5)
        
        self.filtro_anotacoes_var = tk.StringVar(value="All")
        filtro_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.filtro_anotacoes_var,
            values=["All", "Favorites", "By File", "By Group"],
            state="readonly",
            width=12
        )
        filtro_combo.pack(side='left', padx=5)
        filtro_combo.bind('<<ComboboxSelected>>', self.filtrar_anotacoes)
        
        # Search
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side='right', padx=20)
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        
        self.busca_anotacoes_var = tk.StringVar()
        busca_entry = ttk.Entry(search_frame, textvariable=self.busca_anotacoes_var, width=20)
        busca_entry.pack(side='left', padx=5)
        busca_entry.bind('<Return>', lambda e: self.buscar_anotacoes())
        
        ttk.Button(search_frame, text="Search", command=self.buscar_anotacoes).pack(side='left', padx=5)
        
        # Notes listing area
        list_frame = ttk.Frame(main_container)
        list_frame.pack(fill='both', expand=True)
        
        # Treeview for notes
        columns = ("ID", "Title", "File", "Group", "Date", "Favorite")
        self.anotacoes_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15
        )
        
        # Configure columns
        self.anotacoes_tree.column("ID", width=40, anchor='center')
        self.anotacoes_tree.column("Title", width=200, anchor='w')
        self.anotacoes_tree.column("File", width=150, anchor='w')
        self.anotacoes_tree.column("Group", width=100, anchor='w')
        self.anotacoes_tree.column("Date", width=120, anchor='center')
        self.anotacoes_tree.column("Favorite", width=60, anchor='center')
        
        # Configure headings
        for col in columns:
            self.anotacoes_tree.heading(col, text=col)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.anotacoes_tree.yview)
        self.anotacoes_tree.configure(yscrollcommand=scrollbar.set)
        
        self.anotacoes_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Action buttons
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(action_frame, text="View/Edit", command=self.ver_editar_anotacao).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Delete", command=self.deletar_anotacao).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Toggle Favorite", command=self.toggle_favorito_anotacao).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Refresh", command=self.carregar_anotacoes).pack(side='right', padx=5)
        
        # Load notes initially
        self.carregar_anotacoes()

    # Notes control methods
    def carregar_anotacoes(self):
        """Load user notes"""
        # Clear treeview
        for item in self.anotacoes_tree.get_children():
            self.anotacoes_tree.delete(item)
        
        # Get notes from database
        anotacoes = DatabaseManager.get_anotacoes_gerais(self.user_id)
        
        for anotacao in anotacoes:
            anotacao_id, _, titulo, _, arquivo_id, grupo_id, _, data_criacao, _, _, favorito, nome_arquivo, nome_grupo = anotacao
            
            favorito_str = "★" if favorito == 1 else "☆"
            nome_arquivo = nome_arquivo if nome_arquivo else "No file"
            nome_grupo = nome_grupo if nome_grupo else "No group"
            
            # Format date
            from datetime import datetime
            try:
                data_obj = datetime.strptime(data_criacao, '%Y-%m-%d %H:%M:%S')
                data_formatada = data_obj.strftime('%d/%m/%Y')
            except:
                data_formatada = data_criacao
            
            self.anotacoes_tree.insert("", "end", values=(
                anotacao_id, titulo, nome_arquivo, nome_grupo, data_formatada, favorito_str
            ))

    def criar_nova_anotacao(self):
        """Open dialog to create new note"""
        dialog = AnotacaoDialog(self.root, self.user_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.carregar_anotacoes()
            messagebox.showinfo("Success", "Note created successfully!")

    def ver_editar_anotacao(self):
        """View/edit selected note"""
        selection = self.anotacoes_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a note first!")
            return
        
        item = selection[0]
        anotacao_id = self.anotacoes_tree.item(item)['values'][0]
        
        # Get complete note data
        anotacoes = DatabaseManager.get_anotacoes_gerais(self.user_id)
        anotacao_data = None
        for anot in anotacoes:
            if anot[0] == anotacao_id:
                anotacao_data = anot
                break
        
        if anotacao_data:
            dialog = AnotacaoDialog(self.root, self.user_id, anotacao_data)
            self.root.wait_window(dialog.dialog)
            
            if dialog.result:
                self.carregar_anotacoes()
                messagebox.showinfo("Success", "Note updated successfully!")

    def deletar_anotacao(self):
        """Delete selected note"""
        selection = self.anotacoes_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a note first!")
            return
        
        item = selection[0]
        anotacao_id = self.anotacoes_tree.item(item)['values'][0]
        titulo = self.anotacoes_tree.item(item)['values'][1]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the note '{titulo}'?"):
            if DatabaseManager.deletar_anotacao_geral(anotacao_id):
                self.carregar_anotacoes()
                messagebox.showinfo("Success", "Note deleted successfully!")
            else:
                messagebox.showerror("Error", "Failed to delete note!")

    def toggle_favorito_anotacao(self):
        """Toggle note favorite status"""
        selection = self.anotacoes_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a note first!")
            return
        
        item = selection[0]
        anotacao_id = self.anotacoes_tree.item(item)['values'][0]
        titulo = self.anotacoes_tree.item(item)['values'][1]
        
        novo_status = DatabaseManager.toggle_favorito_anotacao(anotacao_id)
        if novo_status is not None:
            status_text = "added to" if novo_status == 1 else "removed from"
            messagebox.showinfo("Success", f"Note '{titulo}' has been {status_text} favorites!")
            self.carregar_anotacoes()
        else:
            messagebox.showerror("Error", "Failed to update favorite status!")

    def filtrar_anotacoes(self, event=None):
        """Filter notes based on selected criteria"""
        self.carregar_anotacoes()

    def buscar_anotacoes(self):
        """Search notes by text"""
        termo = self.busca_anotacoes_var.get().lower()
        if not termo:
            self.carregar_anotacoes()
            return
        
        # Simple search implementation
        for item in self.anotacoes_tree.get_children():
            valores = self.anotacoes_tree.item(item)['values']
            titulo = valores[1].lower()
            
            if termo in titulo:
                self.anotacoes_tree.selection_set(item)
                self.anotacoes_tree.focus(item)
                break

    def setup_library_tab(self, tab):
        """Set up the library tab interface"""
        # Main container with paned window for groups sidebar
        paned_window = ttk.PanedWindow(tab, orient='horizontal')
        paned_window.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel for groups
        groups_frame = ttk.Frame(paned_window, width=250)
        paned_window.add(groups_frame, weight=0)
        
        # Groups header
        groups_header = ttk.Frame(groups_frame)
        groups_header.pack(fill='x', pady=(0, 10))
        
        ttk.Label(groups_header, text="Groups", font=('Arial', 12, 'bold')).pack(side='left')
        ttk.Button(groups_header, text="+", width=3, command=self.create_group).pack(side='right')
        
        # Groups list
        self.groups_listbox = tk.Listbox(groups_frame, height=15)
        self.groups_listbox.pack(fill='both', expand=True)
        self.groups_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        self.groups_listbox.bind('<Double-Button-1>', self.edit_selected_group)
        self.groups_listbox.bind('<Button-3>', self.show_group_context_menu)
        
        # Groups buttons
        groups_buttons = ttk.Frame(groups_frame)
        groups_buttons.pack(fill='x', pady=(5, 0))
        
        ttk.Button(groups_buttons, text="Edit", command=self.edit_selected_group).pack(side='left', padx=(0, 5))
        ttk.Button(groups_buttons, text="Delete", command=self.delete_selected_group).pack(side='left')
        
        # Right panel for files
        files_frame = ttk.Frame(paned_window)
        paned_window.add(files_frame, weight=1)
        
        # Search frame
        search_frame = ttk.Frame(files_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side='left', padx=5)
        
        ttk.Button(search_frame, text="Search", command=self.search_files).pack(side='left', padx=5)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side='left', padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(files_frame)
        filter_frame.pack(fill='x', pady=(0, 10))
        
        self.show_favorites_var = tk.BooleanVar()
        ttk.Checkbutton(
            filter_frame,
            text="Show Only Favorites",
            variable=self.show_favorites_var,
            command=self.toggle_favorites_filter
        ).pack(side='left', padx=5)
        
        # Upload and group selection frame
        upload_frame = ttk.Frame(files_frame)
        upload_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(upload_frame, text="Upload File", command=self.upload_file).pack(side='left', padx=5)
        
        # Group selection for upload
        ttk.Label(upload_frame, text="To Group:").pack(side='left', padx=(20, 5))
        self.upload_group_var = tk.StringVar()
        self.upload_group_combo = ttk.Combobox(upload_frame, textvariable=self.upload_group_var, width=15, state='readonly')
        self.upload_group_combo.pack(side='left', padx=5)
        
        # File list
        self.file_list_frame = ttk.Frame(files_frame)
        self.file_list_frame.pack(expand=True, fill='both')
        
        # Refresh button
        refresh_frame = ttk.Frame(files_frame)
        refresh_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(refresh_frame, text="Refresh List", command=self.refresh_file_list).pack(side='left', padx=5)
        
        # Bind Enter key to search
        search_entry.bind('<Return>', lambda event: self.search_files())
        
        # Load initial data
        self.refresh_groups_list()
        self.refresh_file_list()

    def refresh_groups_list(self):
        """Refresh the groups list"""
        self.groups_listbox.delete(0, tk.END)
        
        # Add "All Files" option
        self.groups_listbox.insert(tk.END, "📁 All Files")
        self.groups_listbox.insert(tk.END, "📂 Ungrouped Files")
        
        groups = DatabaseManager.get_user_groups(self.user_id)
        for group in groups:
            group_id, name, desc, color, date = group
            file_count = DatabaseManager.get_group_file_count(group_id)
            display_name = f"🏷️ {name} ({file_count})"
            self.groups_listbox.insert(tk.END, display_name)
        
        # Update upload group combo
        group_options = ["No Group"]
        for group in groups:
            group_options.append(group[1])
        
        self.upload_group_combo['values'] = group_options
        if group_options:
            self.upload_group_combo.set(group_options[0])

    def on_group_select(self, event=None):
        """Handle group selection"""
        selection = self.groups_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if index == 0:
            self.selected_group_id = None
        elif index == 1:
            self.selected_group_id = -1
        else:
            groups = DatabaseManager.get_user_groups(self.user_id)
            if index - 2 < len(groups):
                self.selected_group_id = groups[index - 2][0]
        
        self.refresh_file_list()

    def create_group(self):
        """Create a new group"""
        dialog = GroupDialog(self.root, self.user_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_groups_list()
            messagebox.showinfo("Success", "Group created successfully!")

    def edit_selected_group(self, event=None):
        """Edit the selected group"""
        selection = self.groups_listbox.curselection()
        if not selection or selection[0] < 2:
            return
            
        index = selection[0]
        groups = DatabaseManager.get_user_groups(self.user_id)
        if index - 2 < len(groups):
            group_data = groups[index - 2]
            dialog = GroupDialog(self.root, self.user_id, group_data)
            self.root.wait_window(dialog.dialog)
            
            if dialog.result:
                self.refresh_groups_list()
                messagebox.showinfo("Success", "Group updated successfully!")

    def delete_selected_group(self):
        """Delete the selected group"""
        selection = self.groups_listbox.curselection()
        if not selection or selection[0] < 2:
            return
            
        index = selection[0]
        groups = DatabaseManager.get_user_groups(self.user_id)
        if index - 2 < len(groups):
            group_data = groups[index - 2]
            group_id, group_name = group_data[0], group_data[1]
            
            file_count = DatabaseManager.get_group_file_count(group_id)
            
            message = f"Are you sure you want to delete the group '{group_name}'?"
            if file_count > 0:
                message += f"\n\nThis group contains {file_count} file(s). Files will be moved to 'Ungrouped'."
            
            if messagebox.askyesno("Confirm Delete", message):
                if DatabaseManager.delete_group(group_id):
                    self.refresh_groups_list()
                    self.refresh_file_list()
                    messagebox.showinfo("Success", "Group deleted successfully!")
                else:
                    messagebox.showerror("Error", "Failed to delete group!")

    def show_group_context_menu(self, event):
        """Show context menu for groups"""
        selection = self.groups_listbox.curselection()
        if not selection or selection[0] < 2:
            return
            
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Edit Group", command=self.edit_selected_group)
        context_menu.add_command(label="Delete Group", command=self.delete_selected_group)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def toggle_favorites_filter(self):
        """Toggle between showing all files and only favorites"""
        self.show_favorites_only = self.show_favorites_var.get()
        self.refresh_file_list()

    def search_files(self):
        """Search files based on the search term"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.refresh_file_list()
            return
        
        all_files = DatabaseManager.get_user_files(
            self.user_id, 
            favorites_only=self.show_favorites_only, 
            group_id=self.selected_group_id
        )
        
        if not all_files:
            return
        
        filtered_files = [
            file for file in all_files 
            if (search_term in file[1].lower() or search_term in file[2].lower())
        ]
        
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        if not filtered_files:
            ttk.Label(
                self.file_list_frame,
                text="No files found matching your search.",
                font=('Arial', 12)
            ).pack(expand=True, pady=50)
            return
        
        self.create_file_treeview(filtered_files)

    def clear_search(self):
        """Clear the search and show all files"""
        self.search_var.set("")
        self.refresh_file_list()

    def upload_file(self):
        """Handle file upload"""
        filetypes = [
            ("PDF Files", "*.pdf"),
            ("Text Files", "*.txt"),
            ("EPUB Files", "*.epub"),
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
            
            selected_group_name = self.upload_group_var.get()
            group_id = None
            
            if selected_group_name != "No Group":
                groups = DatabaseManager.get_user_groups(self.user_id)
                for group in groups:
                    if group[1] == selected_group_name:
                        group_id = group[0]
                        break
            
            user_dir = os.path.join("user_files", str(self.user_id))
            os.makedirs(user_dir, exist_ok=True)
            
            dest_path = os.path.join(user_dir, filename)
            try:
                shutil.copy2(filepath, dest_path)
                
                if DatabaseManager.save_file(self.user_id, filename, dest_path, file_type, group_id):
                    messagebox.showinfo("Success", f"File '{filename}' uploaded successfully!")
                    self.refresh_groups_list()
                    self.refresh_file_list()
                else:
                    os.remove(dest_path)
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload file: {str(e)}")

    def create_file_treeview(self, files):
        """Create treeview to display files"""
        columns = ("ID", "Filename", "Type", "Date", "Favorite", "Group")
        tree = ttk.Treeview(
            self.file_list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        tree.column("ID", width=50, anchor='center')
        tree.column("Filename", width=250, anchor='w')
        tree.column("Type", width=80, anchor='center')
        tree.column("Date", width=120, anchor='center')
        tree.column("Favorite", width=70, anchor='center')
        tree.column("Group", width=120, anchor='w')
        
        for col in columns:
            tree.heading(col, text=col)
        
        for file in files:
            file_id, filename, file_type, date, is_favorite, group_id, group_name, group_color = file
            favorite_status = "★" if is_favorite else "☆"
            group_display = group_name if group_name else "Ungrouped"
            tree.insert("", "end", values=(file_id, filename, file_type, date, favorite_status, group_display))
        
        tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        button_frame = ttk.Frame(self.file_list_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Open File", command=lambda: self.open_selected_file(tree)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Toggle Favorite", command=lambda: self.toggle_file_favorite(tree)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Move to Group", command=lambda: self.move_file_to_group(tree)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete File", command=lambda: self.delete_selected_file(tree)).pack(side='left', padx=5)

    def move_file_to_group(self, tree):
        """Move selected file to a different group"""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file first!")
            return
        
        file_info = tree.item(selected_item)['values']
        file_id = file_info[0]
        filename = file_info[1]
        
        groups = DatabaseManager.get_user_groups(self.user_id)
        group_options = ["Ungrouped"]
        group_ids = [None]
        
        for group in groups:
            group_options.append(group[1])
            group_ids.append(group[0])
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Move File to Group")
        dialog.grab_set()
        dialog.geometry("300x150")
        
        x = (dialog.winfo_screenwidth() - 300) // 2
        y = (dialog.winfo_screenheight() - 150) // 2
        dialog.geometry(f"300x150+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text=f"Move '{filename}' to:").pack(pady=10)
        
        selected_group = tk.StringVar()
        combo = ttk.Combobox(frame, textvariable=selected_group, values=group_options, state='readonly')
        combo.pack(pady=10)
        combo.set(group_options[0])
        
        def move_file():
            selection = selected_group.get()
            if selection in group_options:
                index = group_options.index(selection)
                new_group_id = group_ids[index]
                
                if DatabaseManager.move_file_to_group(file_id, new_group_id):
                    dialog.destroy()
                    self.refresh_groups_list()
                    self.refresh_file_list()
                    messagebox.showinfo("Success", f"File moved to '{selection}' successfully!")
                else:
                    messagebox.showerror("Error", "Failed to move file!")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Move", command=move_file).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
        
        theme_manager.apply_theme_to_widget(dialog)
        theme_manager.apply_theme_recursive(dialog)

    def refresh_file_list(self):
        """Refresh the list of files in the library"""
        search_term = self.search_var.get().lower()
        
        if search_term:
            self.search_files()
            return
        
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        files = DatabaseManager.get_user_files(
            self.user_id, 
            favorites_only=self.show_favorites_only, 
            group_id=self.selected_group_id
        )
        
        if not files:
            filter_text = " favorites" if self.show_favorites_only else ""
            group_text = ""
            if self.selected_group_id == -1:
                group_text = " in ungrouped files"
            elif self.selected_group_id:
                groups = DatabaseManager.get_user_groups(self.user_id)
                for group in groups:
                    if group[0] == self.selected_group_id:
                        group_text = f" in group '{group[1]}'"
                        break
            
            ttk.Label(
                self.file_list_frame,
                text=f"No{filter_text} files found{group_text}.",
                font=('Arial', 12)
            ).pack(expand=True, pady=50)
            return
        
        self.create_file_treeview(files)

    def toggle_file_favorite(self, tree):
        """Toggle favorite status of the selected file"""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file first!")
            return
        
        file_info = tree.item(selected_item)['values']
        file_id = file_info[0]
        filename = file_info[1]
        
        new_status = DatabaseManager.toggle_favorite(file_id)
        
        if new_status is not None:
            status_text = "added to" if new_status == 1 else "removed from"
            messagebox.showinfo("Success", f"File '{filename}' has been {status_text} favorites!")
            self.refresh_file_list()
        else:
            messagebox.showerror("Error", "Failed to update favorite status!")

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
                self.notebook.select(1)
                self.pdf_viewer.pdf_doc = fitz.open(file_path)
                self.pdf_viewer.file_id = file_id
                self.pdf_viewer.current_page = 0
                self.pdf_viewer.render_page()
                self.pdf_viewer.update_controls()
            else:
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def delete_selected_file(self, tree):
        """Delete the selected file"""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file first!")
            return
        
        file_info = tree.item(selected_item)['values']
        file_id = file_info[0]
        filename = file_info[1]
        file_path = DatabaseManager.get_file_path(file_id)
        
        if not file_path:
            messagebox.showerror("Error", "File not found!")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{filename}'?\n\nThis will also delete all annotations and highlights.\nThis action cannot be undone."):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                if DatabaseManager.delete_file(file_id):
                    messagebox.showinfo("Success", "File deleted successfully!")
                    self.refresh_groups_list()
                    self.refresh_file_list()
                else:
                    messagebox.showerror("Error", "Failed to delete file record!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {str(e)}")

    def show_home(self):
        """Show the home screen"""
        if self.notebook:
            self.notebook.select(0)
            
            for child in self.notebook.winfo_children()[0].winfo_children():
                child.destroy()
            
            label = ttk.Label(
                self.notebook.winfo_children()[0],
                text=f"Welcome, {self.user_email}!\nThis is the home screen.", 
                font=('Arial', 16),
                justify='center'
            )
            label.pack(expand=True)
            
            button_frame = ttk.Frame(self.notebook.winfo_children()[0])
            button_frame.pack(pady=20)
            
            ttk.Button(button_frame, text="Open Profile", command=self.show_profile).pack(side='left', padx=10)
            ttk.Button(button_frame, text="Open Settings", command=self.show_settings).pack(side='left', padx=10)
            ttk.Button(button_frame, text="Open PDF Viewer", command=lambda: self.notebook.select(1)).pack(side='left', padx=10)
            ttk.Button(button_frame, text="Open My Library", command=lambda: self.notebook.select(2)).pack(side='left', padx=10)

    def show_profile(self):
        """Show user profile"""
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(home_tab, text="User Profile", font=('Arial', 16))
            label.pack(pady=20)
            
            info_frame = ttk.Frame(home_tab)
            info_frame.pack(pady=10)
            
            ttk.Label(info_frame, text=f"Email: {self.user_email}").grid(row=0, column=0, sticky='w', pady=5)
            ttk.Label(info_frame, text="Registration Date: 01/01/2023").grid(row=1, column=0, sticky='w', pady=5)
            ttk.Label(info_frame, text="Last Login: Today").grid(row=2, column=0, sticky='w', pady=5)
            
            favorite_count = len(DatabaseManager.get_user_files(self.user_id, favorites_only=True))
            ttk.Label(info_frame, text=f"Favorite Files: {favorite_count}").grid(row=3, column=0, sticky='w', pady=5)
            
            total_files = len(DatabaseManager.get_user_files(self.user_id))
            ttk.Label(info_frame, text=f"Total Files: {total_files}").grid(row=4, column=0, sticky='w', pady=5)
            
            group_count = len(DatabaseManager.get_user_groups(self.user_id))
            ttk.Label(info_frame, text=f"Groups Created: {group_count}").grid(row=5, column=0, sticky='w', pady=5)
            
            ttk.Label(info_frame, text=f"Current Theme: {theme_manager.current_theme.title()}").grid(row=6, column=0, sticky='w', pady=5)
            
            ttk.Button(home_tab, text="Back to Home", command=self.show_home).pack(pady=20)

    def show_settings(self):
        """Show application settings"""
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(home_tab, text="Application Settings", font=('Arial', 16))
            label.pack(pady=20)
            
            settings_frame = ttk.Frame(home_tab)
            settings_frame.pack(pady=10, padx=20, fill='both', expand=True)
            
            # Theme settings
            theme_frame = ttk.LabelFrame(settings_frame, text="Theme Settings", padding=10)
            theme_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=10)
            
            ttk.Label(theme_frame, text="Current Theme:").grid(row=0, column=0, sticky='w', pady=5)
            
            theme_var = tk.StringVar(value=theme_manager.current_theme)
            theme_combo = ttk.Combobox(theme_frame, textvariable=theme_var, values=list(theme_manager.THEMES.keys()), state="readonly")
            theme_combo.grid(row=0, column=1, sticky='w', pady=5, padx=(10, 0))
            
            def change_theme(event=None):
                selected_theme = theme_var.get()
                theme_manager.set_theme(selected_theme)
                if hasattr(self, 'show_vim_info'):
                    self.show_vim_info()
                
            theme_combo.bind('<<ComboboxSelected>>', change_theme)
            
            ttk.Button(theme_frame, text="Toggle Theme", command=lambda: [self.toggle_theme(), self.show_vim_info() if hasattr(self, 'show_vim_info') else None]).grid(row=0, column=2, padx=10)
            
            # Vim theme settings
            vim_frame = ttk.LabelFrame(settings_frame, text="Vim Theme Integration", padding=10)
            vim_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=10)
            
            ttk.Label(vim_frame, text="Generate matching Vim color scheme:").grid(row=0, column=0, sticky='w', pady=5)
            
            ttk.Button(vim_frame, text="Generate Vim Theme", command=self.generate_vim_theme).grid(row=0, column=1, padx=10)
            ttk.Button(vim_frame, text="Show Vim Instructions", command=self.show_vim_instructions).grid(row=0, column=2, padx=5)
            
            # Vim info display
            self.vim_info_frame = ttk.Frame(vim_frame)
            self.vim_info_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=10)
            
            # Other settings
            other_frame = ttk.LabelFrame(settings_frame, text="Other Settings", padding=10)
            other_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
            
            ttk.Checkbutton(other_frame, text="Email Notifications").grid(row=0, column=0, sticky='w', pady=5)
            ttk.Checkbutton(other_frame, text="Auto-save annotations").grid(row=1, column=0, sticky='w', pady=5)
            
            ttk.Button(home_tab, text="Back to Home", command=self.show_home).pack(pady=20)
            
            # Show initial Vim info
            self.show_vim_info()

    def generate_vim_theme(self):
        """Generate Vim theme and show confirmation"""
        theme_manager.generate_vim_theme()
        messagebox.showinfo(
            "Vim Theme Generated", 
            f"Vim theme generated successfully!\n\nTheme: {theme_manager.VIM_THEMES[theme_manager.current_theme]['name']}\nLocation: ~/.vim/colors/\n\nUse ':colorscheme {theme_manager.VIM_THEMES[theme_manager.current_theme]['name']}' in Vim"
        )
        self.show_vim_info()

    def show_vim_instructions(self):
        """Show Vim theme usage instructions"""
        instructions = theme_manager.get_vim_instructions()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Vim Theme Instructions")
        dialog.geometry("600x400")
        dialog.grab_set()
        
        x = (dialog.winfo_screenwidth() - 600) // 2
        y = (dialog.winfo_screenheight() - 400) // 2
        dialog.geometry(f"600x400+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        text_widget = tk.Text(frame, wrap='word', height=15, width=70)
        text_widget.pack(fill='both', expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        
        text_widget.insert('1.0', instructions)
        text_widget.config(state='disabled')
        
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(pady=10)
        
        theme_manager.apply_theme_to_widget(dialog)
        theme_manager.apply_theme_recursive(dialog)

    def show_vim_info(self):
        """Show current Vim theme information in settings"""
        for widget in self.vim_info_frame.winfo_children():
            widget.destroy()
        
        vim_theme = theme_manager.VIM_THEMES.get(theme_manager.current_theme)
        if vim_theme:
            info_text = f"Current Vim theme: {vim_theme['name']}"
            theme_path = theme_manager.get_vim_theme_path()
            
            if theme_path and os.path.exists(theme_path):
                info_text += " ✓ (Generated)"
            else:
                info_text += " (Not generated)"
            
            ttk.Label(self.vim_info_frame, text=info_text).pack(anchor='w')
            
            if theme_path and os.path.exists(theme_path):
                ttk.Label(self.vim_info_frame, text=f"Location: {theme_path}", font=('Arial', 8)).pack(anchor='w')

    def show_about(self):
        """Show about information"""
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(home_tab, text="About This Application", font=('Arial', 16))
            label.pack(pady=20)
            
            about_text = """PDF Viewer Application with Groups & Favorites
Version 1.4.0
Developed with Python and Tkinter

Features:
• PDF viewing and annotation
• File organization with groups
• File management with favorites
• Search functionality
• Highlight and annotation tools
• Color-coded group system
• Dark/Light theme support
• Note-taking system
• Book download from Project Gutenberg
• Vim theme integration

© 2025 All rights reserved"""
            
            ttk.Label(home_tab, text=about_text, justify='left').pack(pady=10)
            
            ttk.Button(home_tab, text="Back to Home", command=self.show_home).pack(pady=20)