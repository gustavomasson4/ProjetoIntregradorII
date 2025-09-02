import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import shutil
from database import DatabaseManager
from pdf_viewer import PDFViewer
import fitz
from datetime import datetime
import re

class SearchBar:
    def __init__(self, parent, database_manager, user_id, file_list_callback):
        """
        Inicializa a barra de pesquisa
        
        Args:
            parent: Widget pai
            database_manager: Instância do DatabaseManager
            user_id: ID do usuário atual
            file_list_callback: Função callback para atualizar a lista de arquivos
        """
        self.parent = parent
        self.db = database_manager
        self.user_id = user_id
        self.file_list_callback = file_list_callback
        self.current_filter = "all"  # all, pdf, txt, image
        self.sort_by = "date"  # date, name, type
        self.sort_order = "desc"  # asc, desc
        
        self.setup_search_ui()
    
    def setup_search_ui(self):
        """Configura a interface da barra de pesquisa"""
        # Frame principal da pesquisa
        self.search_frame = ttk.Frame(self.parent)
        self.search_frame.pack(fill='x', pady=10, padx=10)
        
        # Linha 1: Pesquisa básica
        search_row1 = ttk.Frame(self.search_frame)
        search_row1.pack(fill='x', pady=(0, 5))
        
        ttk.Label(search_row1, text="Pesquisar:").pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_row1, 
            textvariable=self.search_var, 
            width=40,
            font=('Arial', 10)
        )
        self.search_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # Botões de pesquisa
        self.btn_search = ttk.Button(
            search_row1,
            text="Buscar",
            command=self.perform_search
        )
        self.btn_search.pack(side='left', padx=5)
        
        self.btn_clear = ttk.Button(
            search_row1,
            text="Limpar",
            command=self.clear_search
        )
        self.btn_clear.pack(side='left', padx=2)
        
        # Linha 2: Filtros avançados
        search_row2 = ttk.Frame(self.search_frame)
        search_row2.pack(fill='x', pady=(0, 5))
        
        # Filtro por tipo de arquivo
        ttk.Label(search_row2, text="Tipo:").pack(side='left', padx=(0, 5))
        
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            search_row2,
            textvariable=self.filter_var,
            values=["all", "pdf", "txt", "image"],
            state="readonly",
            width=10
        )
        filter_combo.pack(side='left', padx=5)
        filter_combo.bind("<<ComboboxSelected>>", self.on_filter_change)
        
        # Separador
        ttk.Separator(search_row2, orient='vertical').pack(side='left', fill='y', padx=10)
        
        # Ordenação
        ttk.Label(search_row2, text="Ordenar por:").pack(side='left', padx=(0, 5))
        
        self.sort_var = tk.StringVar(value="date")
        sort_combo = ttk.Combobox(
            search_row2,
            textvariable=self.sort_var,
            values=["date", "name", "type"],
            state="readonly",
            width=10
        )
        sort_combo.pack(side='left', padx=5)
        sort_combo.bind("<<ComboboxSelected>>", self.on_sort_change)
        
        # Ordem (crescente/decrescente)
        self.order_var = tk.StringVar(value="desc")
        order_combo = ttk.Combobox(
            search_row2,
            textvariable=self.order_var,
            values=["desc", "asc"],
            state="readonly",
            width=8
        )
        order_combo.pack(side='left', padx=5)
        order_combo.bind("<<ComboboxSelected>>", self.on_sort_change)
        
        # Linha 3: Pesquisa avançada (expansível)
        self.advanced_frame = ttk.Frame(self.search_frame)
        self.show_advanced = False
        
        self.btn_advanced = ttk.Button(
            search_row2,
            text="Avançado",
            command=self.toggle_advanced_search
        )
        self.btn_advanced.pack(side='right', padx=5)
        
        self.setup_advanced_search()
        
        # Bind eventos
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
    
    def setup_advanced_search(self):
        """Configura a pesquisa avançada"""
        # Pesquisa por data
        date_frame = ttk.LabelFrame(self.advanced_frame, text="Filtros por Data")
        date_frame.pack(fill='x', pady=5)
        
        # Data de início
        ttk.Label(date_frame, text="De:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.date_from_var = tk.StringVar()
        self.date_from_entry = ttk.Entry(date_frame, textvariable=self.date_from_var, width=12)
        self.date_from_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(date_frame, text="(YYYY-MM-DD)").grid(row=0, column=2, sticky='w', padx=2)
        
        # Data de fim
        ttk.Label(date_frame, text="Até:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.date_to_var = tk.StringVar()
        self.date_to_entry = ttk.Entry(date_frame, textvariable=self.date_to_var, width=12)
        self.date_to_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # Opções de pesquisa
        options_frame = ttk.LabelFrame(self.advanced_frame, text="Opções de Pesquisa")
        options_frame.pack(fill='x', pady=5)
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame,
            text="Diferenciar maiúsculas/minúsculas",
            variable=self.case_sensitive_var
        ).pack(anchor='w', padx=5, pady=2)
        
        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame,
            text="Usar expressões regulares",
            variable=self.regex_var
        ).pack(anchor='w', padx=5, pady=2)
    
    def toggle_advanced_search(self):
        """Alterna a exibição da pesquisa avançada"""
        self.show_advanced = not self.show_advanced
        
        if self.show_advanced:
            self.advanced_frame.pack(fill='x', pady=5)
            self.btn_advanced.config(text="Ocultar")
        else:
            self.advanced_frame.pack_forget()
            self.btn_advanced.config(text="Avançado")
    
    def on_search_change(self, event):
        """Chamado quando o texto de pesquisa muda (pesquisa em tempo real)"""
        search_term = self.search_var.get()
        if len(search_term) >= 2 or search_term == "":
            # Pesquisa automática para termos com 2+ caracteres ou quando vazio
            self.parent.after(300, self.perform_search)  # Delay de 300ms
    
    def on_filter_change(self, event):
        """Chamado quando o filtro de tipo muda"""
        self.current_filter = self.filter_var.get()
        self.perform_search()
    
    def on_sort_change(self, event):
        """Chamado quando a ordenação muda"""
        self.sort_by = self.sort_var.get()
        self.sort_order = self.order_var.get()
        self.perform_search()
    
    def perform_search(self):
        """Executa a pesquisa com todos os filtros aplicados"""
        try:
            search_term = self.search_var.get().strip()
            
            # Obter todos os arquivos do usuário
            all_files = self.db.get_user_files(self.user_id)
            
            if not all_files:
                self.file_list_callback([])
                return
            
            # Aplicar filtros
            filtered_files = self.apply_filters(all_files, search_term)
            
            # Aplicar ordenação
            sorted_files = self.apply_sorting(filtered_files)
            
            # Atualizar a lista de arquivos
            self.file_list_callback(sorted_files)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro na pesquisa: {str(e)}")
    
    def apply_filters(self, files, search_term):
        """Aplica todos os filtros aos arquivos"""
        filtered_files = files.copy()
        
        # Filtro por termo de pesquisa
        if search_term:
            filtered_files = self.filter_by_search_term(filtered_files, search_term)
        
        # Filtro por tipo de arquivo
        if self.current_filter != "all":
            filtered_files = self.filter_by_type(filtered_files, self.current_filter)
        
        # Filtros de data (se pesquisa avançada estiver ativa)
        if self.show_advanced:
            filtered_files = self.filter_by_date(filtered_files)
        
        return filtered_files
    
    def filter_by_search_term(self, files, search_term):
        """Filtra arquivos pelo termo de pesquisa"""
        if self.show_advanced and self.regex_var.get():
            # Pesquisa com expressões regulares
            try:
                flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                pattern = re.compile(search_term, flags)
                return [f for f in files if pattern.search(f[1])]  # f[1] é o nome do arquivo
            except re.error:
                messagebox.showerror("Erro", "Expressão regular inválida")
                return files
        else:
            # Pesquisa normal
            if not self.case_sensitive_var.get() if self.show_advanced else True:
                search_term = search_term.lower()
                return [
                    f for f in files 
                    if (search_term in f[1].lower() or  # nome do arquivo
                        search_term in f[2].lower())    # tipo do arquivo
                ]
            else:
                return [
                    f for f in files 
                    if (search_term in f[1] or search_term in f[2])
                ]
    
    def filter_by_type(self, files, file_type):
        """Filtra arquivos por tipo"""
        type_mapping = {
            "pdf": [".pdf"],
            "txt": [".txt", ".text"],
            "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]
        }
        
        extensions = type_mapping.get(file_type, [])
        return [
            f for f in files 
            if any(f[2].lower().endswith(ext) for ext in extensions)
        ]
    
    def filter_by_date(self, files):
        """Filtra arquivos por intervalo de datas"""
        date_from = self.date_from_var.get().strip()
        date_to = self.date_to_var.get().strip()
        
        if not date_from and not date_to:
            return files
        
        try:
            filtered = []
            for f in files:
                file_date_str = f[3]  # f[3] é a data de upload
                
                # Converter string de data para datetime
                try:
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                    except ValueError:
                        continue  # Pula arquivos com formato de data inválido
                
                # Verificar intervalo de datas
                include_file = True
                
                if date_from:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d')
                    if file_date < from_date:
                        include_file = False
                
                if date_to and include_file:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d')
                    to_date = to_date.replace(hour=23, minute=59, second=59)  # Fim do dia
                    if file_date > to_date:
                        include_file = False
                
                if include_file:
                    filtered.append(f)
            
            return filtered
            
        except ValueError:
            messagebox.showerror("Erro", "Formato de data inválido. Use YYYY-MM-DD")
            return files
    
    def apply_sorting(self, files):
        """Aplica ordenação aos arquivos"""
        reverse = self.sort_order == "desc"
        
        if self.sort_by == "name":
            return sorted(files, key=lambda f: f[1].lower(), reverse=reverse)
        elif self.sort_by == "type":
            return sorted(files, key=lambda f: f[2].lower(), reverse=reverse)
        else:  # date
            return sorted(files, key=lambda f: f[3], reverse=reverse)
    
    def clear_search(self):
        """Limpa todos os filtros de pesquisa"""
        self.search_var.set("")
        self.filter_var.set("all")
        self.sort_var.set("date")
        self.order_var.set("desc")
        
        if self.show_advanced:
            self.date_from_var.set("")
            self.date_to_var.set("")
            self.case_sensitive_var.set(False)
            self.regex_var.set(False)
        
        self.current_filter = "all"
        self.sort_by = "date"
        self.sort_order = "desc"
        
        # Recarregar todos os arquivos
        all_files = self.db.get_user_files(self.user_id)
        sorted_files = self.apply_sorting(all_files)
        self.file_list_callback(sorted_files)


class MainApplication:
    def __init__(self, root, user_email):
        self.root = root
        self.user_email = user_email
        self.user_id = DatabaseManager.get_user_id(user_email)
        self.notebook = None
        self.pdf_viewer = None
        self.current_files = []
        
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
        """Set up the library tab interface with enhanced search"""
        # Barra de pesquisa melhorada
        self.search_bar = SearchBar(
            tab, 
            DatabaseManager, 
            self.user_id, 
            self.update_file_list
        )
        
        # Botões de ação (upload, etc.)
        action_frame = ttk.Frame(tab)
        action_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Button(
            action_frame,
            text="Upload File",
            command=self.upload_file
        ).pack(side='left', padx=5)
        
        ttk.Button(
            action_frame,
            text="Refresh List",
            command=self.refresh_file_list
        ).pack(side='left', padx=5)
        
        # Label de estatísticas
        self.stats_label = ttk.Label(action_frame, text="")
        self.stats_label.pack(side='right', padx=5)
        
        # Frame para lista de arquivos
        self.file_list_frame = ttk.Frame(tab)
        self.file_list_frame.pack(expand=True, fill='both', pady=10, padx=10)
        
        # Carregar arquivos iniciais
        self.refresh_file_list()
    
    def update_file_list(self, files):
        """Atualiza a lista de arquivos exibida (callback da SearchBar)"""
        self.current_files = files
        
        # Limpar lista atual
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        if not files:
            ttk.Label(
                self.file_list_frame,
                text="No files found matching your search.",
                font=('Arial', 12)
            ).pack(expand=True, pady=50)
            self.stats_label.config(text="0 files")
            return
        
        # Criar treeview para exibir arquivos
        columns = ("ID", "Filename", "Type", "Date")
        tree = ttk.Treeview(
            self.file_list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # Configurar colunas
        tree.column("ID", width=50, anchor='center')
        tree.column("Filename", width=300, anchor='w')
        tree.column("Type", width=100, anchor='center')
        tree.column("Date", width=150, anchor='center')
        
        # Adicionar cabeçalhos
        for col in columns:
            tree.heading(col, text=col)
        
        # Adicionar arquivos
        for file in files:
            tree.insert("", "end", values=file)
        
        tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=v_scroll.set)
        
        # Botões de ação para arquivos selecionados
        file_actions = ttk.Frame(self.file_list_frame)
        file_actions.pack(pady=10)
        
        ttk.Button(
            file_actions,
            text="Open File",
            command=lambda: self.open_selected_file(tree)
        ).pack(side='left', padx=10)
        
        ttk.Button(
            file_actions,
            text="Delete File",
            command=lambda: self.delete_selected_file(tree)
        ).pack(side='left', padx=10)
        
        # Atualizar estatísticas
        total_files = len(DatabaseManager.get_user_files(self.user_id))
        self.stats_label.config(text=f"{len(files)} of {total_files} files")

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
        # Use a SearchBar para recarregar todos os arquivos
        if hasattr(self, 'search_bar'):
            self.search_bar.clear_search()
        else:
            # Fallback se a SearchBar ainda não foi criada
            all_files = DatabaseManager.get_user_files(self.user_id)
            self.update_file_list(all_files)

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

Features:
- Advanced file search with filters
- PDF viewing with annotations
- File upload and management
- User authentication

© 2025 All rights reserved"""
            
            ttk.Label(
                home_tab,
                text=about_text,
                justify='center'
            ).pack(pady=10)
            
            ttk.Button(
                home_tab,
                text="Back to Home",
                command=self.show_home
            ).pack(pady=20)
