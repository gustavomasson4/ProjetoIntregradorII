import tkinter as tk
from tkinter import ttk, messagebox
import requests
from urllib.parse import quote
from database import DatabaseManager
import threading

class BookRecommendationsWindow:
    def __init__(self, parent, user_id):
        self.parent = parent
        self.user_id = user_id
        self.recommendations = []
        self.preferences = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("📚 Recomendações de Livros")
        self.window.geometry("1000x700")
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 1000) // 2
        y = (self.window.winfo_screenheight() - 700) // 2
        self.window.geometry(f"1000x700+{x}+{y}")
        
        self.setup_ui()
        self.load_user_preferences()
        
    def setup_ui(self):
        """Setup the complete UI"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="📚 Sistema de Recomendações de Livros",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab 1: Preferences
        prefs_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(prefs_tab, text="Minhas Preferências")
        self.setup_preferences_tab(prefs_tab)
        
        # Tab 2: Recommendations
        recs_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(recs_tab, text="Recomendações")
        self.setup_recommendations_tab(recs_tab)
        
        # Tab 3: My Ratings
        ratings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(ratings_tab, text="Minhas Avaliações")
        self.setup_ratings_tab(ratings_tab)
        
    def setup_preferences_tab(self, tab):
        """Setup preferences configuration tab"""
        # Instructions
        instructions = ttk.Label(
            tab,
            text="Configure suas preferências de leitura para receber recomendações personalizadas:",
            font=('Arial', 10),
            wraplength=900
        )
        instructions.pack(pady=(0, 20))
        
        # Form frame
        form_frame = ttk.Frame(tab)
        form_frame.pack(fill='both', expand=True, padx=20)
        
        # Genres
        ttk.Label(
            form_frame,
            text="Gêneros Favoritos:",
            font=('Arial', 10, 'bold')
        ).grid(row=0, column=0, sticky='nw', pady=10, padx=5)
        
        genres_info = ttk.Label(
            form_frame,
            text="(Separe por vírgulas: ficção, fantasia, romance, etc.)",
            font=('Arial', 9, 'italic')
        )
        genres_info.grid(row=0, column=1, sticky='w', pady=10)
        
        self.genres_entry = ttk.Entry(form_frame, width=60, font=('Arial', 10))
        self.genres_entry.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 20), padx=5)
        
        # Authors
        ttk.Label(
            form_frame,
            text="Autores Favoritos:",
            font=('Arial', 10, 'bold')
        ).grid(row=2, column=0, sticky='nw', pady=10, padx=5)
        
        authors_info = ttk.Label(
            form_frame,
            text="(Separe por vírgulas: Machado de Assis, Clarice Lispector, etc.)",
            font=('Arial', 9, 'italic')
        )
        authors_info.grid(row=2, column=1, sticky='w', pady=10)
        
        self.authors_entry = ttk.Entry(form_frame, width=60, font=('Arial', 10))
        self.authors_entry.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0, 20), padx=5)
        
        # Keywords
        ttk.Label(
            form_frame,
            text="Palavras-chave / Temas:",
            font=('Arial', 10, 'bold')
        ).grid(row=4, column=0, sticky='nw', pady=10, padx=5)
        
        keywords_info = ttk.Label(
            form_frame,
            text="(Separe por vírgulas: aventura, mistério, história, ciência, etc.)",
            font=('Arial', 9, 'italic')
        )
        keywords_info.grid(row=4, column=1, sticky='w', pady=10)
        
        self.keywords_text = tk.Text(form_frame, height=4, width=60, font=('Arial', 10))
        self.keywords_text.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(0, 20), padx=5)
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="💾 Salvar Preferências",
            command=self.save_preferences
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="🔄 Resetar",
            command=self.reset_preferences
        ).pack(side='left', padx=10)
        
        form_frame.grid_columnconfigure(1, weight=1)
        
    def setup_recommendations_tab(self, tab):
        """Setup recommendations display tab"""
        # Control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(
            control_frame,
            text="Buscar por:",
            font=('Arial', 10)
        ).pack(side='left', padx=5)
        
        self.search_type_var = tk.StringVar(value="preferences")
        
        ttk.Radiobutton(
            control_frame,
            text="Minhas Preferências",
            variable=self.search_type_var,
            value="preferences"
        ).pack(side='left', padx=10)
        
        ttk.Radiobutton(
            control_frame,
            text="Termo Personalizado",
            variable=self.search_type_var,
            value="custom"
        ).pack(side='left', padx=10)
        
        self.custom_search_entry = ttk.Entry(control_frame, width=30)
        self.custom_search_entry.pack(side='left', padx=10)
        
        ttk.Button(
            control_frame,
            text="🔍 Buscar Recomendações",
            command=self.search_recommendations
        ).pack(side='left', padx=10)
        
        # Results frame
        results_frame = ttk.LabelFrame(tab, text="Livros Recomendados", padding=10)
        results_frame.pack(fill='both', expand=True, pady=10)
        
        # Treeview for results
        columns = ("Título", "Autor", "Idioma", "Downloads")
        self.recs_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15
        )
        
        self.recs_tree.column("Título", width=350)
        self.recs_tree.column("Autor", width=200)
        self.recs_tree.column("Idioma", width=80)
        self.recs_tree.column("Downloads", width=100)
        
        for col in columns:
            self.recs_tree.heading(col, text=col)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.recs_tree.yview)
        h_scroll = ttk.Scrollbar(results_frame, orient="horizontal", command=self.recs_tree.xview)
        self.recs_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.recs_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        # Action buttons
        action_frame = ttk.Frame(tab)
        action_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            action_frame,
            text="📖 Ver Detalhes",
            command=self.show_book_details
        ).pack(side='left', padx=5)
        
        ttk.Button(
            action_frame,
            text="⬇️ Baixar Livro",
            command=self.download_selected_book
        ).pack(side='left', padx=5)
        
        ttk.Button(
            action_frame,
            text="⭐ Avaliar Livro",
            command=self.rate_selected_book
        ).pack(side='left', padx=5)
        
        # Status label
        self.status_label = ttk.Label(
            tab,
            text="Configure suas preferências e clique em 'Buscar Recomendações'",
            font=('Arial', 9, 'italic')
        )
        self.status_label.pack(pady=5)
        
    def setup_ratings_tab(self, tab):
        """Setup user ratings display tab"""
        # Info
        info_label = ttk.Label(
            tab,
            text="Seus livros avaliados:",
            font=('Arial', 11, 'bold')
        )
        info_label.pack(pady=(0, 10))
        
        # Ratings list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill='both', expand=True)
        
        columns = ("Livro", "Avaliação", "Resenha", "Data")
        self.ratings_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15
        )
        
        self.ratings_tree.column("Livro", width=300)
        self.ratings_tree.column("Avaliação", width=100)
        self.ratings_tree.column("Resenha", width=300)
        self.ratings_tree.column("Data", width=150)
        
        for col in columns:
            self.ratings_tree.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.ratings_tree.yview)
        self.ratings_tree.configure(yscrollcommand=scrollbar.set)
        
        self.ratings_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            button_frame,
            text="🔄 Atualizar Lista",
            command=self.load_user_ratings
        ).pack(side='left', padx=5)
        
        # Load ratings
        self.load_user_ratings()
        
    def load_user_preferences(self):
        """Load user preferences from database"""
        self.preferences = DatabaseManager.get_user_preferences(self.user_id)
        
        if self.preferences:
            self.genres_entry.insert(0, self.preferences['genres'])
            self.authors_entry.insert(0, self.preferences['authors'])
            self.keywords_text.insert('1.0', self.preferences['keywords'])
        
    def save_preferences(self):
        """Save user preferences"""
        genres = self.genres_entry.get().strip()
        authors = self.authors_entry.get().strip()
        keywords = self.keywords_text.get('1.0', 'end-1c').strip()
        
        if not genres and not authors and not keywords:
            messagebox.showwarning(
                "Aviso",
                "Preencha pelo menos um campo para salvar suas preferências!"
            )
            return
        
        if DatabaseManager.save_user_preferences(self.user_id, genres, authors, keywords):
            messagebox.showinfo("Sucesso", "Preferências salvas com sucesso!")
            self.preferences = {
                'genres': genres,
                'authors': authors,
                'keywords': keywords
            }
        else:
            messagebox.showerror("Erro", "Falha ao salvar preferências!")
            
    def reset_preferences(self):
        """Reset preference fields"""
        self.genres_entry.delete(0, 'end')
        self.authors_entry.delete(0, 'end')
        self.keywords_text.delete('1.0', 'end')
        
    def search_recommendations(self):
        """Search for book recommendations"""
        search_type = self.search_type_var.get()
        
        if search_type == "preferences":
            if not self.preferences:
                messagebox.showwarning(
                    "Aviso",
                    "Configure suas preferências primeiro!"
                )
                self.notebook.select(0)  # Go to preferences tab
                return
            
            # Build search query from preferences
            search_terms = []
            if self.preferences['genres']:
                search_terms.extend(self.preferences['genres'].split(','))
            if self.preferences['keywords']:
                search_terms.extend(self.preferences['keywords'].split(','))
            
            search_query = ' '.join([term.strip() for term in search_terms[:3]])  # Limit to 3 terms
            
        else:  # custom
            search_query = self.custom_search_entry.get().strip()
            if not search_query:
                messagebox.showwarning("Aviso", "Digite um termo de busca!")
                return
        
        # Search in background thread
        self.status_label.config(text="🔍 Buscando recomendações...")
        self.window.update()
        
        thread = threading.Thread(
            target=self._search_books_thread,
            args=(search_query,),
            daemon=True
        )
        thread.start()
        
    def _search_books_thread(self, search_query):
        """Search for books in background thread"""
        try:
            url = f"https://gutendex.com/books/?search={quote(search_query)}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.recommendations = data.get('results', [])
                
                # Update UI in main thread
                self.window.after(0, self._display_recommendations)
            else:
                self.window.after(0, lambda: self.status_label.config(
                    text="❌ Erro ao buscar recomendações"
                ))
                
        except Exception as e:
            print(f"Search error: {e}")
            self.window.after(0, lambda: self.status_label.config(
                text=f"❌ Erro: {str(e)}"
            ))
            
    def _display_recommendations(self):
        """Display recommendations in treeview"""
        # Clear existing items
        for item in self.recs_tree.get_children():
            self.recs_tree.delete(item)
        
        if not self.recommendations:
            self.status_label.config(text="😕 Nenhuma recomendação encontrada")
            return
        
        # Add recommendations
        for book in self.recommendations[:50]:  # Limit to 50
            title = book.get('title', 'Unknown')
            authors = ', '.join([a.get('name', 'Unknown') for a in book.get('authors', [])])
            languages = ', '.join(book.get('languages', []))
            downloads = book.get('download_count', 0)
            
            self.recs_tree.insert("", "end", values=(title, authors, languages, downloads))
        
        self.status_label.config(text=f"✅ {len(self.recommendations)} livros encontrados")
        
    def show_book_details(self):
        """Show details of selected book"""
        selection = self.recs_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um livro primeiro!")
            return
        
        item_index = self.recs_tree.index(selection[0])
        if item_index < len(self.recommendations):
            book = self.recommendations[item_index]
            
            details = f"""
📖 Título: {book.get('title', 'N/A')}

✍️ Autores: {', '.join([a.get('name', 'Unknown') for a in book.get('authors', [])])}

🌐 Idiomas: {', '.join(book.get('languages', []))}

⬇️ Downloads: {book.get('download_count', 0)}

🆔 ID Gutenberg: {book.get('id', 'N/A')}

📚 Assuntos: {', '.join(book.get('subjects', [])[:5])}

🔗 Formatos disponíveis: {', '.join(book.get('formats', {}).keys())}
            """
            
            messagebox.showinfo("Detalhes do Livro", details)
            
    def download_selected_book(self):
        """Download selected book"""
        selection = self.recs_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um livro primeiro!")
            return
        
        item_index = self.recs_tree.index(selection[0])
        if item_index < len(self.recommendations):
            book = self.recommendations[item_index]
            
            # Show format selection dialog
            formats = book.get('formats', {})
            available_formats = []
            
            if 'application/epub+zip' in formats:
                available_formats.append(('EPUB', 'application/epub+zip'))
            if 'text/plain; charset=utf-8' in formats or 'text/plain' in formats:
                available_formats.append(('TXT', 'text/plain; charset=utf-8'))
            
            if not available_formats:
                messagebox.showwarning(
                    "Aviso",
                    "Nenhum formato compatível disponível para este livro!"
                )
                return
            
            # Simple format selection
            format_choice = messagebox.askquestion(
                "Escolher Formato",
                f"Deseja baixar em formato EPUB?\n\n(Não = TXT)"
            )
            
            if format_choice == 'yes':
                format_type = 'epub'
                format_key = 'application/epub+zip'
            else:
                format_type = 'txt'
                format_key = 'text/plain; charset=utf-8'
            
            if format_key not in formats:
                format_key = 'text/plain'
            
            download_url = formats.get(format_key)
            if not download_url:
                messagebox.showerror("Erro", "URL de download não encontrada!")
                return
            
            # Download logic would go here
            # For now, just show a message
            messagebox.showinfo(
                "Download",
                f"Funcionalidade de download será implementada!\n\nURL: {download_url}"
            )
            
    def rate_selected_book(self):
        """Rate selected book"""
        selection = self.recs_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um livro primeiro!")
            return
        
        item_values = self.recs_tree.item(selection[0])['values']
        book_title = item_values[0]
        
        # Create rating dialog
        rating_dialog = tk.Toplevel(self.window)
        rating_dialog.title("Avaliar Livro")
        rating_dialog.geometry("400x300")
        rating_dialog.grab_set()
        
        # Center dialog
        x = self.window.winfo_x() + (self.window.winfo_width() - 400) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 300) // 2
        rating_dialog.geometry(f"400x300+{x}+{y}")
        
        frame = ttk.Frame(rating_dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        ttk.Label(
            frame,
            text=f"Avaliar: {book_title}",
            font=('Arial', 11, 'bold'),
            wraplength=350
        ).pack(pady=(0, 20))
        
        # Rating scale
        ttk.Label(frame, text="Avaliação (1-5 estrelas):").pack(pady=5)
        rating_var = tk.IntVar(value=3)
        
        rating_frame = ttk.Frame(frame)
        rating_frame.pack(pady=10)
        
        for i in range(1, 6):
            ttk.Radiobutton(
                rating_frame,
                text=f"{'⭐' * i}",
                variable=rating_var,
                value=i
            ).pack(side='left', padx=5)
        
        # Review
        ttk.Label(frame, text="Resenha (opcional):").pack(pady=5)
        review_text = tk.Text(frame, height=5, width=40)
        review_text.pack(pady=5)
        
        # Buttons
        def save_rating():
            rating = rating_var.get()
            review = review_text.get('1.0', 'end-1c').strip()
            
            if DatabaseManager.save_book_rating(self.user_id, book_title, rating, review):
                messagebox.showinfo("Sucesso", "Avaliação salva com sucesso!")
                rating_dialog.destroy()
                self.load_user_ratings()
            else:
                messagebox.showerror("Erro", "Falha ao salvar avaliação!")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Salvar", command=save_rating).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancelar", command=rating_dialog.destroy).pack(side='left', padx=10)
        
    def load_user_ratings(self):
        """Load and display user ratings"""
        for item in self.ratings_tree.get_children():
            self.ratings_tree.delete(item)
        
        ratings = DatabaseManager.get_user_ratings(self.user_id)
        
        for rating in ratings:
            titulo, avaliacao, resenha, data = rating
            stars = '⭐' * avaliacao
            resenha_short = (resenha[:50] + '...') if resenha and len(resenha) > 50 else (resenha or '')
            
            self.ratings_tree.insert("", "end", values=(titulo, stars, resenha_short, data))