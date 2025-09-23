import tkinter as tk
from tkinter import ttk
import json
import os

class ThemeManager:
    """Theme Manager for the PDF Viewer Application"""
    
    THEMES = {
        'light': {
            'bg': '#ffffff',
            'fg': '#000000',
            'select_bg': '#0078d4',
            'select_fg': '#ffffff',
            'entry_bg': '#ffffff',
            'entry_fg': '#000000',
            'button_bg': '#f0f0f0',
            'button_fg': '#000000',
            'frame_bg': '#ffffff',
            'canvas_bg': '#ffffff',
            'text_bg': '#ffffff',
            'text_fg': '#000000',
            'menu_bg': '#ffffff',
            'menu_fg': '#000000',
            'highlight_bg': '#e3f2fd',
            'border_color': '#cccccc',
            'notebook_bg': '#ffffff',
            'treeview_bg': '#ffffff',
            'treeview_fg': '#000000',
            'treeview_selected_bg': '#0078d4',
            'treeview_selected_fg': '#ffffff'
        },
        'dark': {
            'bg': '#2d2d2d',
            'fg': '#ffffff',
            'select_bg': '#0078d4',
            'select_fg': '#ffffff',
            'entry_bg': '#404040',
            'entry_fg': '#ffffff',
            'button_bg': '#404040',
            'button_fg': '#ffffff',
            'frame_bg': '#2d2d2d',
            'canvas_bg': '#404040',
            'text_bg': '#404040',
            'text_fg': '#ffffff',
            'menu_bg': '#2d2d2d',
            'menu_fg': '#ffffff',
            'highlight_bg': '#404040',
            'border_color': '#555555',
            'notebook_bg': '#2d2d2d',
            'treeview_bg': '#404040',
            'treeview_fg': '#ffffff',
            'treeview_selected_bg': '#0078d4',
            'treeview_selected_fg': '#ffffff'
        }
    }
    
    def __init__(self):
        self.current_theme = 'light'
        self.theme_callbacks = []
        self.load_theme_preference()
        
    def load_theme_preference(self):
        """Load theme preference from config file"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.current_theme = config.get('theme', 'light')
        except Exception as e:
            print(f"Failed to load theme preference: {e}")
            self.current_theme = 'light'
    
    def save_theme_preference(self):
        """Save theme preference to config file"""
        try:
            config = {}
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
            
            config['theme'] = self.current_theme
            
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save theme preference: {e}")
    
    def get_theme(self, theme_name=None):
        """Get theme colors"""
        theme_name = theme_name or self.current_theme
        return self.THEMES.get(theme_name, self.THEMES['light'])
    
    def set_theme(self, theme_name):
        """Set current theme and notify callbacks"""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.save_theme_preference()
            self.notify_theme_change()
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.set_theme(new_theme)
    
    def register_callback(self, callback):
        """Register a callback to be notified when theme changes"""
        self.theme_callbacks.append(callback)
    
    def notify_theme_change(self):
        """Notify all registered callbacks of theme change"""
        for callback in self.theme_callbacks:
            try:
                callback(self.current_theme)
            except Exception as e:
                print(f"Theme callback error: {e}")
    
    def apply_theme_to_widget(self, widget, widget_type='frame'):
        """Apply current theme to a specific widget"""
        theme = self.get_theme()
        
        try:
            if isinstance(widget, tk.Tk) or isinstance(widget, tk.Toplevel):
                widget.configure(bg=theme['bg'])
            elif isinstance(widget, ttk.Frame) or isinstance(widget, ttk.LabelFrame):
                # TTK widgets use styles
                pass
            elif isinstance(widget, tk.Frame) or isinstance(widget, tk.LabelFrame):
                widget.configure(bg=theme['frame_bg'])
            elif isinstance(widget, tk.Label):
                widget.configure(bg=theme['bg'], fg=theme['fg'])
            elif isinstance(widget, tk.Button):
                widget.configure(
                    bg=theme['button_bg'], 
                    fg=theme['button_fg'],
                    activebackground=theme['select_bg'],
                    activeforeground=theme['select_fg']
                )
            elif isinstance(widget, tk.Entry):
                widget.configure(
                    bg=theme['entry_bg'], 
                    fg=theme['entry_fg'],
                    insertbackground=theme['fg']
                )
            elif isinstance(widget, tk.Text):
                widget.configure(
                    bg=theme['text_bg'], 
                    fg=theme['text_fg'],
                    insertbackground=theme['fg']
                )
            elif isinstance(widget, tk.Canvas):
                widget.configure(bg=theme['canvas_bg'])
            elif isinstance(widget, tk.Listbox):
                widget.configure(
                    bg=theme['treeview_bg'], 
                    fg=theme['treeview_fg'],
                    selectbackground=theme['treeview_selected_bg'],
                    selectforeground=theme['treeview_selected_fg']
                )
        except Exception as e:
            print(f"Error applying theme to widget: {e}")
    
    def apply_ttk_theme(self, root):
        """Apply theme to TTK widgets using styles"""
        theme = self.get_theme()
        style = ttk.Style(root)
        
        # Configure TTK styles
        style.theme_use('clam')  # Use clam theme as base
        
        # Configure styles for different widgets
        style.configure('TFrame', background=theme['frame_bg'])
        style.configure('TLabel', background=theme['frame_bg'], foreground=theme['fg'])
        style.configure('TButton', 
                       background=theme['button_bg'], 
                       foreground=theme['button_fg'])
        style.map('TButton',
                 background=[('active', theme['select_bg']),
                            ('pressed', theme['select_bg'])])
        
        style.configure('TEntry', 
                       fieldbackground=theme['entry_bg'], 
                       foreground=theme['entry_fg'],
                       bordercolor=theme['border_color'])
        
        style.configure('TCombobox', 
                       fieldbackground=theme['entry_bg'], 
                       foreground=theme['entry_fg'])
        
        style.configure('TNotebook', background=theme['notebook_bg'])
        style.configure('TNotebook.Tab', 
                       background=theme['button_bg'],
                       foreground=theme['fg'])
        style.map('TNotebook.Tab',
                 background=[('selected', theme['select_bg'])])
        
        # Treeview styles
        style.configure('Treeview', 
                       background=theme['treeview_bg'],
                       foreground=theme['treeview_fg'],
                       fieldbackground=theme['treeview_bg'])
        style.map('Treeview',
                 background=[('selected', theme['treeview_selected_bg'])],
                 foreground=[('selected', theme['treeview_selected_fg'])])
        
        style.configure('Treeview.Heading',
                       background=theme['button_bg'],
                       foreground=theme['fg'])
    
    def apply_theme_recursive(self, widget):
        """Recursively apply theme to all child widgets"""
        self.apply_theme_to_widget(widget)
        
        try:
            for child in widget.winfo_children():
                self.apply_theme_recursive(child)
        except Exception as e:
            print(f"Error in recursive theme application: {e}")

theme_manager = ThemeManager()