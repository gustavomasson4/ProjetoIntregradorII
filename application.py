import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import os
import shutil
from database import DatabaseManager
from pdf_viewer import PDFViewer
from epub_viewer import EPUBViewer
from theme_manager import theme_manager
import fitz
import threading

# Book download imports
import requests
from urllib.parse import quote

# TTS imports
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("pyttsx3 not installed. Install with: pip install pyttsx3")

# ==================== GROUP DIALOG CLASS ====================
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
        
        ttk.Label(main_frame, text="Group Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = tk.StringVar(value=self.group_data[1] if self.group_data else "")
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky='nw', pady=5)
        self.desc_text = tk.Text(main_frame, height=4, width=30)
        self.desc_text.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5)
        if self.group_data and self.group_data[2]:
            self.desc_text.insert('1.0', self.group_data[2])
        
        ttk.Label(main_frame, text="Color:").grid(row=2, column=0, sticky='w', pady=5)
        
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=2, column=1, columnspan=2, sticky='w', pady=5)
        
        self.color_canvas = tk.Canvas(color_frame, width=30, height=20, bg=self.selected_color)
        self.color_canvas.pack(side='left', padx=(0, 10))
        
        ttk.Button(color_frame, text="Choose Color", command=self.choose_color).pack(side='left')
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self.save_group).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=10)
        
        main_frame.grid_columnconfigure(1, weight=1)
        
    def apply_theme(self):
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
        
        if self.group_data:
            if DatabaseManager.update_group(self.group_data[0], name, description, self.selected_color):
                self.result = (name, description, self.selected_color)
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update group!")
        else:
            group_id = DatabaseManager.create_group(self.user_id, name, description, self.selected_color)
            if group_id:
                self.result = (group_id, name, description, self.selected_color)
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to create group!")

# ==================== BOOK DOWNLOAD DIALOG CLASS ====================
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
        
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search Book:").pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<Return>', lambda e: self.search_books())
        
        ttk.Button(search_frame, text="Search", command=self.search_books).pack(side='left', padx=5)
        
        results_frame = ttk.LabelFrame(main_frame, text="Search Results", padding=10)
        results_frame.pack(fill='both', expand=True, pady=10)
        
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
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="Download Selected (TXT)", command=lambda: self.download_selected('txt')).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Download Selected (EPUB)", command=lambda: self.download_selected('epub')).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side='right', padx=5)
        
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
            url = f"https://gutendex.com/books/?search={quote(search_term)}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                for item in self.results_tree.get_children():
                    self.results_tree.delete(item)
                
                self.search_results = []
                
                if results:
                    for book in results[:50]:
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
            
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                user_dir = os.path.join("user_files", str(self.user_id), "downloads")
                os.makedirs(user_dir, exist_ok=True)
                
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
                safe_title = safe_title[:100]
                filename = f"{safe_title}.{format_type}"
                filepath = os.path.join(user_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
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

# ==================== ANOTACAO DIALOG CLASS ====================
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
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 600) // 2
        y = (self.dialog.winfo_screenheight() - 500) // 2
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(main_frame, text="Title:").grid(row=0, column=0, sticky='w', pady=5)
        self.titulo_var = tk.StringVar(value=self.anotacao_data[2] if self.anotacao_data else "")
        ttk.Entry(main_frame, textvariable=self.titulo_var, width=50).grid(row=0, column=1, sticky='ew', pady=5)
        
        ttk.Label(main_frame, text="Content:").grid(row=1, column=0, sticky='nw', pady=5)
        self.conteudo_text = tk.Text(main_frame, height=15, width=50)
        self.conteudo_text.grid(row=1, column=1, sticky='nsew', pady=5)
        
        if self.anotacao_data and self.anotacao_data[3]:
            self.conteudo_text.insert('1.0', self.anotacao_data[3])
        
        meta_frame = ttk.Frame(main_frame)
        meta_frame.grid(row=2, column=1, sticky='ew', pady=10)
        
        ttk.Label(meta_frame, text="Tags:").pack(side='left', padx=5)
        self.tags_var = tk.StringVar(value=self.anotacao_data[6] if self.anotacao_data else "")
        ttk.Entry(meta_frame, textvariable=self.tags_var, width=30).pack(side='left', padx=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self.salvar_anotacao).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=10)
        
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
    
    def apply_theme(self):
        theme_manager.apply_theme_to_widget(self.dialog)
        theme_manager.apply_theme_recursive(self.dialog)
    
    def salvar_anotacao(self):
        titulo = self.titulo_var.get().strip()
        if not titulo:
            messagebox.showerror("Error", "Title is required!")
            return
        
        conteudo = self.conteudo_text.get('1.0', 'end-1c').strip()
        tags = self.tags_var.get().strip()
        
        if self.anotacao_data:
            if DatabaseManager.atualizar_anotacao_geral(
                self.anotacao_data[0], titulo, conteudo, tags
            ):
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update note!")
        else:
            anotacao_id = DatabaseManager.criar_anotacao_geral(
                self.user_id, titulo, conteudo, tags=tags
            )
            if anotacao_id:
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to create note!")

# ==================== MAIN APPLICATION CLASS ====================
class MainApplication:
    def __init__(self, root, user_email):
        self.root = root
        self.user_email = user_email
        self.user_id = DatabaseManager.get_user_id(user_email)
        self.notebook = None
        self.pdf_viewer = None
        self.epub_viewer = None
        self.show_favorites_only = False
        self.selected_group_id = None
        
        theme_manager.register_callback(self.on_theme_change)
        
        self.configure_window()
        self.create_menu()
        self.setup_interface()
        self.apply_theme()

    def configure_window(self):
        self.root.title("PDF Viewer Application with TTS")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Home", command=self.show_home)
        file_menu.add_separator()
        file_menu.add_command(label="Download Books", command=self.show_book_download)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        user_menu = tk.Menu(menubar, tearoff=0)
        user_menu.add_command(label="Profile", command=self.show_profile)
        user_menu.add_command(label="Settings", command=self.show_settings)
        menubar.add_cascade(label="User", menu=user_menu)
        
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
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def show_book_download(self):
        dialog = BookDownloadDialog(self.root, self.user_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_file_list()
            self.refresh_groups_list()

    def toggle_theme(self):
        theme_manager.toggle_theme()

    def set_theme(self, theme_name):
        theme_manager.set_theme(theme_name)

    def on_theme_change(self, theme_name):
        self.apply_theme()

    def apply_theme(self):
        try:
            theme_manager.apply_ttk_theme(self.root)
            theme_manager.apply_theme_to_widget(self.root)
            theme_manager.apply_theme_recursive(self.root)
            
            if self.pdf_viewer and hasattr(self.pdf_viewer, 'canvas'):
                theme = theme_manager.get_theme()
                self.pdf_viewer.canvas.configure(bg=theme['canvas_bg'])
                
        except Exception as e:
            print(f"Error applying theme: {e}")

    def setup_interface(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill='both')
        
        home_tab = ttk.Frame(self.notebook)
        self.notebook.add(home_tab, text="Home")
        
        pdf_tab = ttk.Frame(self.notebook)
        self.notebook.add(pdf_tab, text="PDF Viewer")
        
        epub_tab = ttk.Frame(self.notebook)
        self.notebook.add(epub_tab, text="EPUB Viewer")
        
        library_tab = ttk.Frame(self.notebook)
        self.notebook.add(library_tab, text="My Library")
        
        notes_tab = ttk.Frame(self.notebook)
        self.notebook.add(notes_tab, text="My Notes")
        
        # Setup PDF Viewer - TTS já é criado automaticamente dentro do PDFViewer
        self.pdf_viewer = PDFViewer(pdf_tab)
        
        # Setup EPUB Viewer
        self.epub_viewer = EPUBViewer(epub_tab)
        
        self.setup_library_tab(library_tab)
        self.setup_notes_tab(notes_tab)
        self.show_home()

    def setup_notes_tab(self, tab):
        main_container = ttk.Frame(tab)
        main_container.pack(expand=True, fill='both', padx=10, pady=10)
        
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(
            controls_frame, 
            text="+ New Note", 
            command=self.criar_nova_anotacao
        ).pack(side='left', padx=5)
        
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
        
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side='right', padx=20)
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        
        self.busca_anotacoes_var = tk.StringVar()
        busca_entry = ttk.Entry(search_frame, textvariable=self.busca_anotacoes_var, width=20)
        busca_entry.pack(side='left', padx=5)
        busca_entry.bind('<Return>', lambda e: self.buscar_anotacoes())
        
        ttk.Button(search_frame, text="Search", command=self.buscar_anotacoes).pack(side='left', padx=5)
        
        list_frame = ttk.Frame(main_container)
        list_frame.pack(fill='both', expand=True)
        
        columns = ("ID", "Title", "File", "Group", "Date", "Favorite")
        self.anotacoes_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15
        )
        
        self.anotacoes_tree.column("ID", width=40, anchor='center')
        self.anotacoes_tree.column("Title", width=200, anchor='w')
        self.anotacoes_tree.column("File", width=150, anchor='w')
        self.anotacoes_tree.column("Group", width=100, anchor='w')
        self.anotacoes_tree.column("Date", width=120, anchor='center')
        self.anotacoes_tree.column("Favorite", width=60, anchor='center')
        
        for col in columns:
            self.anotacoes_tree.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.anotacoes_tree.yview)
        self.anotacoes_tree.configure(yscrollcommand=scrollbar.set)
        
        self.anotacoes_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(action_frame, text="View/Edit", command=self.ver_editar_anotacao).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Delete", command=self.deletar_anotacao).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Toggle Favorite", command=self.toggle_favorito_anotacao).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Refresh", command=self.carregar_anotacoes).pack(side='right', padx=5)
        
        self.carregar_anotacoes()

    def carregar_anotacoes(self):
        for item in self.anotacoes_tree.get_children():
            self.anotacoes_tree.delete(item)
        
        anotacoes = DatabaseManager.get_anotacoes_gerais(self.user_id)
        
        for anotacao in anotacoes:
            anotacao_id, _, titulo, _, arquivo_id, grupo_id, _, data_criacao, _, _, favorito, nome_arquivo, nome_grupo = anotacao
            
            favorito_str = "★" if favorito == 1 else "☆"
            nome_arquivo = nome_arquivo if nome_arquivo else "No file"
            nome_grupo = nome_grupo if nome_grupo else "No group"
            
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
        dialog = AnotacaoDialog(self.root, self.user_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.carregar_anotacoes()
            messagebox.showinfo("Success", "Note created successfully!")

    def ver_editar_anotacao(self):
        selection = self.anotacoes_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a note first!")
            return
        
        item = selection[0]
        anotacao_id = self.anotacoes_tree.item(item)['values'][0]
        
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
        self.carregar_anotacoes()

    def buscar_anotacoes(self):
        termo = self.busca_anotacoes_var.get().lower()
        if not termo:
            self.carregar_anotacoes()
            return
        
        for item in self.anotacoes_tree.get_children():
            valores = self.anotacoes_tree.item(item)['values']
            titulo = valores[1].lower()
            
            if termo in titulo:
                self.anotacoes_tree.selection_set(item)
                self.anotacoes_tree.focus(item)
                break

    def setup_library_tab(self, tab):
        paned_window = ttk.PanedWindow(tab, orient='horizontal')
        paned_window.pack(fill='both', expand=True, padx=10, pady=10)
        
        groups_frame = ttk.Frame(paned_window, width=250)
        paned_window.add(groups_frame, weight=0)
        
        groups_header = ttk.Frame(groups_frame)
        groups_header.pack(fill='x', pady=(0, 10))
        
        ttk.Label(groups_header, text="Groups", font=('Arial', 12, 'bold')).pack(side='left')
        ttk.Button(groups_header, text="+", width=3, command=self.create_group).pack(side='right')
        
        self.groups_listbox = tk.Listbox(groups_frame, height=15)
        self.groups_listbox.pack(fill='both', expand=True)
        self.groups_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        self.groups_listbox.bind('<Double-Button-1>', self.edit_selected_group)
        self.groups_listbox.bind('<Button-3>', self.show_group_context_menu)
        
        groups_buttons = ttk.Frame(groups_frame)
        groups_buttons.pack(fill='x', pady=(5, 0))
        
        ttk.Button(groups_buttons, text="Edit", command=self.edit_selected_group).pack(side='left', padx=(0, 5))
        ttk.Button(groups_buttons, text="Delete", command=self.delete_selected_group).pack(side='left')
        
        files_frame = ttk.Frame(paned_window)
        paned_window.add(files_frame, weight=1)
        
        search_frame = ttk.Frame(files_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side='left', padx=5)
        
        ttk.Button(search_frame, text="Search", command=self.search_files).pack(side='left', padx=5)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side='left', padx=5)
        
        filter_frame = ttk.Frame(files_frame)
        filter_frame.pack(fill='x', pady=(0, 10))
        
        self.show_favorites_var = tk.BooleanVar()
        ttk.Checkbutton(
            filter_frame,
            text="Show Only Favorites",
            variable=self.show_favorites_var,
            command=self.toggle_favorites_filter
        ).pack(side='left', padx=5)
        
        upload_frame = ttk.Frame(files_frame)
        upload_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(upload_frame, text="Upload File", command=self.upload_file).pack(side='left', padx=5)
        
        ttk.Label(upload_frame, text="To Group:").pack(side='left', padx=(20, 5))
        self.upload_group_var = tk.StringVar()
        self.upload_group_combo = ttk.Combobox(upload_frame, textvariable=self.upload_group_var, width=15, state='readonly')
        self.upload_group_combo.pack(side='left', padx=5)
        
        self.file_list_frame = ttk.Frame(files_frame)
        self.file_list_frame.pack(expand=True, fill='both')
        
        refresh_frame = ttk.Frame(files_frame)
        refresh_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(refresh_frame, text="Refresh List", command=self.refresh_file_list).pack(side='left', padx=5)
        
        search_entry.bind('<Return>', lambda event: self.search_files())
        
        self.refresh_groups_list()
        self.refresh_file_list()

    def refresh_groups_list(self):
        self.groups_listbox.delete(0, tk.END)
        
        self.groups_listbox.insert(tk.END, "📚 All Files")
        self.groups_listbox.insert(tk.END, "📂 Ungrouped Files")
        
        groups = DatabaseManager.get_user_groups(self.user_id)
        for group in groups:
            group_id, name, desc, color, date = group
            file_count = DatabaseManager.get_group_file_count(group_id)
            display_name = f"🏷️ {name} ({file_count})"
            self.groups_listbox.insert(tk.END, display_name)
        
        group_options = ["No Group"]
        for group in groups:
            group_options.append(group[1])
        
        self.upload_group_combo['values'] = group_options
        if group_options:
            self.upload_group_combo.set(group_options[0])

    def on_group_select(self, event=None):
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
        dialog = GroupDialog(self.root, self.user_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_groups_list()
            messagebox.showinfo("Success", "Group created successfully!")

    def edit_selected_group(self, event=None):
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
        self.show_favorites_only = self.show_favorites_var.get()
        self.refresh_file_list()

    def search_files(self):
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
        self.search_var.set("")
        self.refresh_file_list()

    def upload_file(self):
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
                self.notebook.select(1)  # PDF Viewer tab
                self.pdf_viewer.pdf_doc = fitz.open(file_path)
                self.pdf_viewer.file_id = file_id
                self.pdf_viewer.current_page = 0
                self.pdf_viewer.render_page()
                self.pdf_viewer.update_controls()
            elif file_path.lower().endswith('.epub'):
                self.notebook.select(2)  # EPUB Viewer tab
                self.epub_viewer.open_epub_file(file_path)
            else:
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def delete_selected_file(self, tree):
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
        if self.notebook:
            self.notebook.select(0)
            
            for child in self.notebook.winfo_children()[0].winfo_children():
                child.destroy()
            
            label = ttk.Label(
                self.notebook.winfo_children()[0],
                text=f"Welcome, {self.user_email}!\n\nPDF Viewer Application with Text-to-Speech", 
                font=('Arial', 16),
                justify='center'
            )
            label.pack(expand=True, pady=20)
            
            info_frame = ttk.LabelFrame(self.notebook.winfo_children()[0], text="Quick Stats", padding=20)
            info_frame.pack(pady=20)
            
            total_files = len(DatabaseManager.get_user_files(self.user_id))
            favorite_files = len(DatabaseManager.get_user_files(self.user_id, favorites_only=True))
            total_groups = len(DatabaseManager.get_user_groups(self.user_id))
            
            ttk.Label(info_frame, text=f"📚 Total Files: {total_files}", font=('Arial', 12)).pack(pady=5)
            ttk.Label(info_frame, text=f"⭐ Favorite Files: {favorite_files}", font=('Arial', 12)).pack(pady=5)
            ttk.Label(info_frame, text=f"🏷️  Groups: {total_groups}", font=('Arial', 12)).pack(pady=5)
            
            if TTS_AVAILABLE:
                ttk.Label(info_frame, text="🔊 Text-to-Speech: Enabled", font=('Arial', 12), foreground='green').pack(pady=5)
            else:
                ttk.Label(info_frame, text="⚠️  Text-to-Speech: Disabled (install pyttsx3)", font=('Arial', 12), foreground='orange').pack(pady=5)
            
            button_frame = ttk.Frame(self.notebook.winfo_children()[0])
            button_frame.pack(pady=20)
            
            ttk.Button(button_frame, text="📊 Open Profile", command=self.show_profile, width=20).pack(side='left', padx=10)
            ttk.Button(button_frame, text="⚙️  Open Settings", command=self.show_settings, width=20).pack(side='left', padx=10)
            ttk.Button(button_frame, text="📄 Open PDF Viewer", command=lambda: self.notebook.select(1), width=20).pack(side='left', padx=10)
            ttk.Button(button_frame, text="📖 Open EPUB Viewer", command=lambda: self.notebook.select(2), width=20).pack(side='left', padx=10)
            ttk.Button(button_frame, text="📚 Open My Library", command=lambda: self.notebook.select(3), width=20).pack(side='left', padx=10)

    def show_profile(self):
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(home_tab, text="👤 User Profile", font=('Arial', 18, 'bold'))
            label.pack(pady=20)
            
            info_frame = ttk.Frame(home_tab)
            info_frame.pack(pady=10, padx=50, fill='both', expand=True)
            
            profile_data = [
                ("Email:", self.user_email),
                ("User ID:", str(self.user_id)),
                ("Registration Date:", "01/01/2023"),
                ("Last Login:", "Today"),
                ("", ""),
                ("📊 Statistics:", ""),
                ("Total Files:", str(len(DatabaseManager.get_user_files(self.user_id)))),
                ("Favorite Files:", str(len(DatabaseManager.get_user_files(self.user_id, favorites_only=True)))),
                ("Groups Created:", str(len(DatabaseManager.get_user_groups(self.user_id)))),
                ("Current Theme:", theme_manager.current_theme.title()),
                ("TTS Status:", "Enabled ✓" if TTS_AVAILABLE else "Disabled ✗"),
            ]
            
            for i, (label_text, value_text) in enumerate(profile_data):
                if label_text == "":
                    ttk.Separator(info_frame, orient='horizontal').grid(row=i, column=0, columnspan=2, sticky='ew', pady=10)
                elif label_text.startswith("📊"):
                    ttk.Label(info_frame, text=label_text, font=('Arial', 12, 'bold')).grid(row=i, column=0, columnspan=2, sticky='w', pady=(10, 5))
                else:
                    ttk.Label(info_frame, text=label_text, font=('Arial', 11, 'bold')).grid(row=i, column=0, sticky='w', pady=5, padx=(0, 20))
                    ttk.Label(info_frame, text=value_text, font=('Arial', 11)).grid(row=i, column=1, sticky='w', pady=5)
            
            ttk.Button(home_tab, text="← Back to Home", command=self.show_home).pack(pady=20)

    def show_settings(self):
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(home_tab, text="⚙️  Application Settings", font=('Arial', 18, 'bold'))
            label.pack(pady=20)
            
            settings_frame = ttk.Frame(home_tab)
            settings_frame.pack(pady=10, padx=20, fill='both', expand=True)
            
            theme_frame = ttk.LabelFrame(settings_frame, text="🎨 Theme Settings", padding=15)
            theme_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=10, padx=10)
            
            ttk.Label(theme_frame, text="Current Theme:", font=('Arial', 10)).grid(row=0, column=0, sticky='w', pady=5)
            
            theme_var = tk.StringVar(value=theme_manager.current_theme)
            theme_combo = ttk.Combobox(theme_frame, textvariable=theme_var, values=list(theme_manager.THEMES.keys()), state="readonly", width=15)
            theme_combo.grid(row=0, column=1, sticky='w', pady=5, padx=(10, 0))
            
            def change_theme(event=None):
                selected_theme = theme_var.get()
                theme_manager.set_theme(selected_theme)
                
            theme_combo.bind('<<ComboboxSelected>>', change_theme)
            
            ttk.Button(theme_frame, text="Toggle Dark/Light", command=self.toggle_theme).grid(row=0, column=2, padx=10)
            
            tts_frame = ttk.LabelFrame(settings_frame, text="🔊 Text-to-Speech Settings", padding=15)
            tts_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=10, padx=10)
            
            if TTS_AVAILABLE:
                ttk.Label(tts_frame, text="Status: Enabled ✓", foreground='green', font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
                ttk.Label(tts_frame, text="Default Speed: 150 WPM", font=('Arial', 9)).grid(row=1, column=0, sticky='w', pady=5)
                ttk.Label(tts_frame, text="Default Volume: 90%", font=('Arial', 9)).grid(row=2, column=0, sticky='w', pady=5)
            else:
                ttk.Label(tts_frame, text="Status: Disabled ✗", foreground='red', font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
                ttk.Label(tts_frame, text="Install pyttsx3 to enable TTS:", font=('Arial', 9)).grid(row=1, column=0, sticky='w', pady=5)
                ttk.Label(tts_frame, text="pip install pyttsx3", font=('Courier', 9)).grid(row=2, column=0, sticky='w', pady=5)
            
            other_frame = ttk.LabelFrame(settings_frame, text="📝 Other Settings", padding=15)
            other_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=10, padx=10)
            
            ttk.Checkbutton(other_frame, text="Enable notifications").grid(row=0, column=0, sticky='w', pady=5)
            ttk.Checkbutton(other_frame, text="Auto-save annotations").grid(row=1, column=0, sticky='w', pady=5)
            ttk.Checkbutton(other_frame, text="Remember last opened file").grid(row=2, column=0, sticky='w', pady=5)
            
            ttk.Button(home_tab, text="← Back to Home", command=self.show_home).pack(pady=20)

    def show_about(self):
        if self.notebook:
            self.notebook.select(0)
            home_tab = self.notebook.winfo_children()[0]
            
            for child in home_tab.winfo_children():
                child.destroy()
            
            label = ttk.Label(home_tab, text="ℹ️  About This Application", font=('Arial', 18, 'bold'))
            label.pack(pady=20)
            
            about_text = """PDF Viewer Application with Text-to-Speech
Version 2.0.0
Developed with Python and Tkinter

✨ Features:
• PDF viewing and annotation
• EPUB viewing with TTS
• Text-to-Speech (TTS) for reading PDFs and EPUBs aloud
• File organization with groups
• File management with favorites
• Search functionality
• Highlight and annotation tools
• Color-coded group system
• Dark/Light theme support
• Note-taking system
• Book download from Project Gutenberg

🔊 TTS Features:
• Read current page/chapter
• Read from current page to end
• Adjustable speed (50-300 WPM)
• Volume control
• Pause/Resume functionality

📚 Libraries Used:
• PyMuPDF (fitz) - PDF processing
• EbookLib - EPUB processing
• BeautifulSoup - HTML parsing
• pyttsx3 - Text-to-Speech
• gTTS - Google Text-to-Speech
• tkinter - GUI framework
• requests - HTTP requests

© 2025 All rights reserved"""
            
            text_widget = tk.Text(home_tab, wrap='word', height=25, width=60, font=('Arial', 10))
            text_widget.pack(pady=10, padx=20)
            text_widget.insert('1.0', about_text)
            text_widget.config(state='disabled')
            
            ttk.Button(home_tab, text="← Back to Home", command=self.show_home).pack(pady=20)