import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import os
import shutil
from database import DatabaseManager
from pdf_viewer import PDFViewer
import fitz

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

class MainApplication:
    def __init__(self, root, user_email):
        self.root = root
        self.user_email = user_email
        self.user_id = DatabaseManager.get_user_id(user_email)
        self.notebook = None
        self.pdf_viewer = None
        self.show_favorites_only = False
        self.selected_group_id = None
        
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
            group_options.append(group[1])  # group name
        
        self.upload_group_combo['values'] = group_options
        if group_options:
            self.upload_group_combo.set(group_options[0])

    def on_group_select(self, event=None):
        """Handle group selection"""
        selection = self.groups_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if index == 0:  # All Files
            self.selected_group_id = None
        elif index == 1:  # Ungrouped Files
            self.selected_group_id = -1
        else:  # Specific group
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
        if not selection or selection[0] < 2:  # Can't edit "All Files" or "Ungrouped"
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
        
        # Get all files from database
        all_files = DatabaseManager.get_user_files(
            self.user_id, 
            favorites_only=self.show_favorites_only, 
            group_id=self.selected_group_id
        )
        
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
            
            # Get selected group for upload
            selected_group_name = self.upload_group_var.get()
            group_id = None
            
            if selected_group_name != "No Group":
                groups = DatabaseManager.get_user_groups(self.user_id)
                for group in groups:
                    if group[1] == selected_group_name:
                        group_id = group[0]
                        break
            
            # Create a directory for user files if it doesn't exist
            user_dir = os.path.join("user_files", str(self.user_id))
            os.makedirs(user_dir, exist_ok=True)
            
            # Copy file to user directory
            dest_path = os.path.join(user_dir, filename)
            try:
                shutil.copy2(filepath, dest_path)
                
                # Save to database
                if DatabaseManager.save_file(self.user_id, filename, dest_path, file_type, group_id):
                    messagebox.showinfo("Success", f"File '{filename}' uploaded successfully!")
                    self.refresh_groups_list()
                    self.refresh_file_list()
                else:
                    os.remove(dest_path)  # Remove the file if database save failed
                    
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
        
        # Configure columns
        tree.column("ID", width=50, anchor='center')
        tree.column("Filename", width=250, anchor='w')
        tree.column("Type", width=80, anchor='center')
        tree.column("Date", width=120, anchor='center')
        tree.column("Favorite", width=70, anchor='center')
        tree.column("Group", width=120, anchor='w')
        
        # Add headings
        for col in columns:
            tree.heading(col, text=col)
        
        # Add files to treeview
        for file in files:
            file_id, filename, file_type, date, is_favorite, group_id, group_name, group_color = file
            favorite_status = "⭐" if is_favorite else "☆"
            group_display = group_name if group_name else "Ungrouped"
            tree.insert("", "end", values=(file_id, filename, file_type, date, favorite_status, group_display))
        
        tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Add buttons for file actions
        button_frame = ttk.Frame(self.file_list_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Open File",
            command=lambda: self.open_selected_file(tree)
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Toggle Favorite",
            command=lambda: self.toggle_file_favorite(tree)
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Move to Group",
            command=lambda: self.move_file_to_group(tree)
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Delete File",
            command=lambda: self.delete_selected_file(tree)
        ).pack(side='left', padx=5)

    def move_file_to_group(self, tree):
        """Move selected file to a different group"""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file first!")
            return
        
        file_info = tree.item(selected_item)['values']
        file_id = file_info[0]
        filename = file_info[1]
        
        # Create group selection dialog
        groups = DatabaseManager.get_user_groups(self.user_id)
        group_options = ["Ungrouped"]
        group_ids = [None]
        
        for group in groups:
            group_options.append(group[1])
            group_ids.append(group[0])
        
        # Simple dialog for group selection
        dialog = tk.Toplevel(self.root)
        dialog.title("Move File to Group")
        dialog.grab_set()
        dialog.geometry("300x150")
        
        # Center dialog
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
        
        # Create treeview to display files
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
        
        # Toggle favorite status in database
        new_status = DatabaseManager.toggle_favorite(file_id)
        
        if new_status is not None:
            status_text = "added to" if new_status == 1 else "removed from"
            messagebox.showinfo(
                "Success", 
                f"File '{filename}' has been {status_text} favorites!"
            )
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
        
        file_info = tree.item(selected_item)['values']
        file_id = file_info[0]
        filename = file_info[1]
        file_path = DatabaseManager.get_file_path(file_id)
        
        if not file_path:
            messagebox.showerror("Error", "File not found!")
            return
        
        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{filename}'?\n\nThis will also delete all annotations and highlights.\nThis action cannot be undone."
        ):
            try:
                # Delete from filesystem
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete from database (this will also delete related annotations and highlights)
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
            
            # Show statistics
            favorite_count = len(DatabaseManager.get_user_files(self.user_id, favorites_only=True))
            ttk.Label(
                info_frame,
                text=f"Favorite Files: {favorite_count}"
            ).grid(row=3, column=0, sticky='w', pady=5)
            
            total_files = len(DatabaseManager.get_user_files(self.user_id))
            ttk.Label(
                info_frame,
                text=f"Total Files: {total_files}"
            ).grid(row=4, column=0, sticky='w', pady=5)
            
            group_count = len(DatabaseManager.get_user_groups(self.user_id))
            ttk.Label(
                info_frame,
                text=f"Groups Created: {group_count}"
            ).grid(row=5, column=0, sticky='w', pady=5)
            
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
            
            about_text = """PDF Viewer Application with Groups & Favorites
Version 1.2.0
Developed with Python and Tkinter

Features:
• PDF viewing and annotation
• File organization with groups
• File management with favorites
• Search functionality
• Highlight and annotation tools
• Color-coded group system

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