import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, font as tkfont
import os
import re
import tempfile
import threading
from database import DatabaseManager
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

# TTS imports - Usando gTTS
try:
    from gtts import gTTS
    import pygame
    pygame.mixer.init()
    TTS_AVAILABLE = True
    print("✓ gTTS disponível!")
except ImportError:
    TTS_AVAILABLE = False
    print("✗ gTTS não disponível. Instale: pip install gTTS pygame")

class EPUBViewer:
    def __init__(self, parent):
        self.parent = parent
        self.current_chapter = 0
        self.epub_book = None
        self.chapters = []
        self.chapter_titles = []
        self.file_id = None
        self.epub_path = None
        
        # Font settings
        self.font_size = 12
        self.font_family = "Arial"
        self.line_spacing = 1.5
        self.bg_color = "#FFFFFF"
        self.fg_color = "#000000"
        
        # TTS attributes - gTTS
        self.is_reading = False
        self.is_paused = False
        self.reading_thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.current_text = ""
        self.current_sentence_index = 0
        self.sentences = []
        self.temp_audio_files = []
        self.tts_language = 'pt'
        self.tts_speed = 1.0
        self.tts_controls_created = False
        
        # Search
        self.search_results = []
        self.current_search_index = -1
        
        # Bookmarks
        self.bookmarks = []
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the complete UI"""
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # TTS controls at TOP
        if not self.tts_controls_created:
            self.setup_tts_controls()
            self.tts_controls_created = True

        # Control frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill='x', pady=5)

        # Left buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side='left')

        self.btn_open = ttk.Button(btn_frame, text="📖 Open EPUB", command=self.open_epub)
        self.btn_open.pack(side='left', padx=5)

        self.btn_prev = ttk.Button(btn_frame, text="◄ Previous", command=self.prev_chapter, state='disabled')
        self.btn_prev.pack(side='left', padx=5)

        self.btn_next = ttk.Button(btn_frame, text="Next ►", command=self.next_chapter, state='disabled')
        self.btn_next.pack(side='left', padx=5)

        self.lbl_chapter = ttk.Label(control_frame, text="Chapter: 0/0")
        self.lbl_chapter.pack(side='left', padx=20)

        # Chapter selector
        ttk.Label(control_frame, text="Go to:").pack(side='left', padx=5)
        self.chapter_var = tk.StringVar()
        self.chapter_combo = ttk.Combobox(
            control_frame,
            textvariable=self.chapter_var,
            width=30,
            state='readonly'
        )
        self.chapter_combo.pack(side='left', padx=5)
        self.chapter_combo.bind('<<ComboboxSelected>>', self.on_chapter_select)

        # Right controls
        right_frame = ttk.Frame(control_frame)
        right_frame.pack(side='right')

        # Font controls
        ttk.Button(right_frame, text="A-", command=self.decrease_font).pack(side='left', padx=2)
        ttk.Button(right_frame, text="A+", command=self.increase_font).pack(side='left', padx=2)
        
        # Theme toggle
        ttk.Button(right_frame, text="🌙 Theme", command=self.toggle_theme).pack(side='left', padx=5)
        
        # Bookmark
        ttk.Button(right_frame, text="🔖 Bookmark", command=self.add_bookmark).pack(side='left', padx=5)

        # Search controls
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side='right', padx=20)

        ttk.Label(search_frame, text="Search:").pack(side='left')
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<Return>', lambda e: self.search_text())

        ttk.Button(search_frame, text="Find", command=self.search_text).pack(side='left', padx=2)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side='left', padx=2)

        # Content display
        self.setup_content_display()

    def setup_tts_controls(self):
        """Setup TTS control panel"""
        tts_frame = ttk.LabelFrame(self.main_frame, text="📖 Text Reader (Google TTS)", padding=10)
        tts_frame.pack(side='top', fill='x', pady=(0, 5))
        
        # Button frame
        button_frame = ttk.Frame(tts_frame)
        button_frame.pack(fill='x', pady=5)
        
        self.read_chapter_btn = ttk.Button(
            button_frame,
            text="▶ Read Chapter",
            command=self.read_current_chapter
        )
        self.read_chapter_btn.pack(side='left', padx=2)
        
        self.read_from_btn = ttk.Button(
            button_frame,
            text="▶▶ Read From Here",
            command=self.read_from_chapter
        )
        self.read_from_btn.pack(side='left', padx=2)
        
        self.pause_btn = ttk.Button(
            button_frame,
            text="⏸ Pause",
            command=self.toggle_pause_reading,
            state='disabled'
        )
        self.pause_btn.pack(side='left', padx=2)
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop",
            command=self.stop_reading,
            state='disabled'
        )
        self.stop_btn.pack(side='left', padx=2)
        
        ttk.Button(button_frame, text="🔊 Test", command=self.test_tts).pack(side='left', padx=10)
        
        # Settings frame
        settings_frame = ttk.Frame(tts_frame)
        settings_frame.pack(fill='x', pady=5)
        
        ttk.Label(settings_frame, text="Language:").pack(side='left', padx=5)
        
        self.language_var = tk.StringVar(value="pt")
        language_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.language_var,
            values=["pt", "en", "es", "fr", "de", "it"],
            state='readonly',
            width=5
        )
        language_combo.pack(side='left', padx=5)
        language_combo.bind('<<ComboboxSelected>>', self.on_language_change)
        
        ttk.Label(settings_frame, text="Speed:").pack(side='left', padx=15)
        
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(
            settings_frame,
            from_=0.5,
            to=2.0,
            variable=self.speed_var,
            orient='horizontal',
            length=150,
            command=self.on_speed_change
        )
        speed_scale.pack(side='left', padx=5)
        
        self.speed_label = ttk.Label(settings_frame, text="1.0x")
        self.speed_label.pack(side='left', padx=5)
        
        self.tts_status_label = ttk.Label(tts_frame, text="Ready", font=('Arial', 9, 'italic'))
        self.tts_status_label.pack(pady=5)
        
        if not TTS_AVAILABLE:
            self.tts_status_label.config(text="⚠️ gTTS not available. Install: pip install gTTS pygame")
            self.read_chapter_btn.config(state='disabled')
            self.read_from_btn.config(state='disabled')
        
        self.update_tts_status()

    def setup_content_display(self):
        """Setup content display area"""
        container = ttk.Frame(self.main_frame)
        container.pack(expand=True, fill='both')

        # Text widget with scrollbar
        self.text_widget = tk.Text(
            container,
            wrap='word',
            font=(self.font_family, self.font_size),
            bg=self.bg_color,
            fg=self.fg_color,
            padx=50,
            pady=20,
            spacing1=5,
            spacing2=2,
            spacing3=5
        )
        self.text_widget.pack(side='left', expand=True, fill='both')

        scrollbar = ttk.Scrollbar(container, orient='vertical', command=self.text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        # Configure text tags
        self.text_widget.tag_configure("highlight", background="yellow", foreground="black")
        self.text_widget.tag_configure("title", font=(self.font_family, self.font_size + 8, "bold"))
        self.text_widget.tag_configure("heading", font=(self.font_family, self.font_size + 4, "bold"))

    # ============= EPUB METHODS =============
    
    def open_epub(self):
        """Open an EPUB file"""
        filepath = filedialog.askopenfilename(
            title="Select EPUB File",
            filetypes=[("EPUB Files", "*.epub"), ("All Files", "*.*")]
        )
        
        if filepath:
            try:
                self.epub_book = epub.read_epub(filepath)
                self.epub_path = filepath
                self.extract_chapters()
                
                if self.chapters:
                    self.current_chapter = 0
                    self.render_chapter()
                    self.update_controls()
                    messagebox.showinfo("Success", f"Loaded {len(self.chapters)} chapters!")
                else:
                    messagebox.showerror("Error", "No readable chapters found in this EPUB!")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open EPUB:\n{str(e)}")

    def extract_chapters(self):
        """Extract chapters from EPUB"""
        self.chapters = []
        self.chapter_titles = []
        
        try:
            # Get all HTML documents
            items = list(self.epub_book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            
            for idx, item in enumerate(items):
                content = item.get_content().decode('utf-8', errors='ignore')
                
                # Parse HTML
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                if text.strip():
                    self.chapters.append(text)
                    
                    # Try to get chapter title
                    title = soup.find(['h1', 'h2', 'h3', 'title'])
                    if title:
                        chapter_title = title.get_text().strip()
                    else:
                        chapter_title = f"Chapter {idx + 1}"
                    
                    self.chapter_titles.append(chapter_title)
            
            # Update chapter combo
            self.chapter_combo['values'] = self.chapter_titles
            
        except Exception as e:
            print(f"Error extracting chapters: {e}")
            messagebox.showerror("Error", f"Failed to extract chapters:\n{str(e)}")

    def render_chapter(self):
        """Render current chapter"""
        if not self.chapters or self.current_chapter >= len(self.chapters):
            return
        
        self.text_widget.config(state='normal')
        self.text_widget.delete('1.0', 'end')
        
        # Get chapter content
        content = self.chapters[self.current_chapter]
        
        # Insert chapter title
        title = self.chapter_titles[self.current_chapter]
        self.text_widget.insert('1.0', f"{title}\n\n", "title")
        
        # Insert content
        self.text_widget.insert('end', content)
        
        self.text_widget.config(state='disabled')
        self.text_widget.see('1.0')

    def prev_chapter(self):
        """Go to previous chapter"""
        if self.current_chapter > 0:
            self.current_chapter -= 1
            self.render_chapter()
            self.update_controls()

    def next_chapter(self):
        """Go to next chapter"""
        if self.current_chapter < len(self.chapters) - 1:
            self.current_chapter += 1
            self.render_chapter()
            self.update_controls()

    def on_chapter_select(self, event=None):
        """Handle chapter selection from combo"""
        selected = self.chapter_combo.current()
        if selected >= 0:
            self.current_chapter = selected
            self.render_chapter()
            self.update_controls()

    def update_controls(self):
        """Update navigation controls"""
        if self.chapters:
            total = len(self.chapters)
            self.btn_prev.config(state='normal' if self.current_chapter > 0 else 'disabled')
            self.btn_next.config(state='normal' if self.current_chapter < total - 1 else 'disabled')
            self.lbl_chapter.config(text=f"Chapter: {self.current_chapter + 1}/{total}")
            self.chapter_combo.current(self.current_chapter)
        else:
            self.btn_prev.config(state='disabled')
            self.btn_next.config(state='disabled')
            self.lbl_chapter.config(text="Chapter: 0/0")

    # ============= FONT AND THEME =============
    
    def increase_font(self):
        """Increase font size"""
        self.font_size = min(self.font_size + 2, 32)
        self.update_font()

    def decrease_font(self):
        """Decrease font size"""
        self.font_size = max(self.font_size - 2, 8)
        self.update_font()

    def update_font(self):
        """Update text widget font"""
        self.text_widget.config(font=(self.font_family, self.font_size))
        self.text_widget.tag_configure("title", font=(self.font_family, self.font_size + 8, "bold"))
        self.text_widget.tag_configure("heading", font=(self.font_family, self.font_size + 4, "bold"))

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        if self.bg_color == "#FFFFFF":
            # Dark theme
            self.bg_color = "#2b2b2b"
            self.fg_color = "#e0e0e0"
        else:
            # Light theme
            self.bg_color = "#FFFFFF"
            self.fg_color = "#000000"
        
        self.text_widget.config(bg=self.bg_color, fg=self.fg_color)

    # ============= BOOKMARKS =============
    
    def add_bookmark(self):
        """Add bookmark at current position"""
        if not self.chapters:
            return
        
        bookmark_name = simpledialog.askstring(
            "Bookmark",
            "Enter bookmark name:",
            parent=self.parent
        )
        
        if bookmark_name:
            bookmark = {
                'name': bookmark_name,
                'chapter': self.current_chapter,
                'position': self.text_widget.index('insert')
            }
            self.bookmarks.append(bookmark)
            messagebox.showinfo("Success", "Bookmark added!")

    # ============= SEARCH =============
    
    def search_text(self):
        """Search for text in current chapter"""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
        
        # Remove previous highlights
        self.text_widget.tag_remove("highlight", "1.0", "end")
        
        # Search and highlight
        start_pos = "1.0"
        count = 0
        
        while True:
            start_pos = self.text_widget.search(search_term, start_pos, "end", nocase=True)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(search_term)}c"
            self.text_widget.tag_add("highlight", start_pos, end_pos)
            start_pos = end_pos
            count += 1
        
        if count > 0:
            # Scroll to first occurrence
            first_pos = self.text_widget.search(search_term, "1.0", "end", nocase=True)
            if first_pos:
                self.text_widget.see(first_pos)
            messagebox.showinfo("Search", f"Found {count} occurrence(s)")
        else:
            messagebox.showinfo("Search", "Text not found in current chapter")

    def clear_search(self):
        """Clear search highlights"""
        self.search_var.set("")
        self.text_widget.tag_remove("highlight", "1.0", "end")

    # ============= TTS METHODS =============
    
    def test_tts(self):
        """Test TTS"""
        if not TTS_AVAILABLE:
            messagebox.showerror("Error", "gTTS not available.")
            return
        
        test_text = "Olá! Este é um teste do leitor de livros digitais. O sistema está funcionando perfeitamente."
        self.start_reading(test_text)

    def extract_chapter_text(self, chapter_number=None):
        """Extract text from chapter"""
        if not self.chapters:
            return ""
        
        if chapter_number is None:
            chapter_number = self.current_chapter
        
        if 0 <= chapter_number < len(self.chapters):
            return self.chapters[chapter_number]
        return ""

    def read_current_chapter(self):
        """Read current chapter"""
        if not TTS_AVAILABLE:
            messagebox.showerror("Error", "gTTS not available.")
            return
        
        if not self.chapters:
            messagebox.showwarning("Warning", "No book loaded!")
            return
        
        text = self.extract_chapter_text()
        if not text:
            messagebox.showwarning("Warning", "No text found!")
            return
        
        self.start_reading(text)

    def read_from_chapter(self):
        """Read from current chapter to end"""
        if not TTS_AVAILABLE:
            messagebox.showerror("Error", "gTTS not available.")
            return
        
        if not self.chapters:
            messagebox.showwarning("Warning", "No book loaded!")
            return
        
        all_text = []
        for chapter_num in range(self.current_chapter, len(self.chapters)):
            text = self.extract_chapter_text(chapter_num)
            if text:
                title = self.chapter_titles[chapter_num]
                all_text.append(f"{title}. {text}")
        
        if not all_text:
            messagebox.showwarning("Warning", "No text found!")
            return
        
        combined_text = " ".join(all_text)
        self.start_reading(combined_text)

    def start_reading(self, text):
        """Start reading text"""
        print("\n" + "="*60)
        print("=== START READING (EPUB) ===")
        
        if self.is_reading:
            print("Stopping previous reading...")
            self.stop_reading()
            import time
            time.sleep(0.5)
        
        self.cleanup_temp_files()
        
        self.current_text = text
        sentences = re.split(r'(?<=[.!?])\s+', text)
        self.sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]
        
        if not self.sentences:
            messagebox.showwarning("Warning", "No valid text to read!")
            return
        
        self.current_sentence_index = 0
        self.is_reading = True
        self.is_paused = False
        self.stop_event.clear()
        self.pause_event.set()
        
        self.tts_language = self.language_var.get()
        self.tts_speed = self.speed_var.get()
        
        print(f"Reading {len(self.sentences)} sentences")
        
        self.reading_thread = threading.Thread(target=self._read_text_gtts, daemon=True)
        self.reading_thread.start()
        print("="*60 + "\n")

    def _read_text_gtts(self):
        """Read text using gTTS"""
        print("=== gTTS Thread started ===")
        
        try:
            language = self.tts_language
            speed = self.tts_speed
            use_slow = (speed < 0.8)
            
            for idx in range(len(self.sentences)):
                if self.stop_event.is_set():
                    break
                
                while not self.pause_event.is_set():
                    if self.stop_event.is_set():
                        break
                    threading.Event().wait(0.1)
                
                if self.stop_event.is_set():
                    break
                
                self.current_sentence_index = idx
                sentence = self.sentences[idx]
                
                if sentence:
                    print(f"[{idx+1}/{len(self.sentences)}] Speaking...")
                    
                    try:
                        tts = gTTS(text=sentence, lang=language, slow=use_slow)
                        
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        temp_file.close()
                        tts.save(temp_file.name)
                        self.temp_audio_files.append(temp_file.name)
                        
                        pygame.mixer.music.load(temp_file.name)
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy():
                            if self.stop_event.is_set():
                                pygame.mixer.music.stop()
                                break
                            
                            if not self.pause_event.is_set():
                                pygame.mixer.music.pause()
                                while not self.pause_event.is_set():
                                    if self.stop_event.is_set():
                                        break
                                    threading.Event().wait(0.1)
                                if not self.stop_event.is_set():
                                    pygame.mixer.music.unpause()
                            
                            threading.Event().wait(0.1)
                        
                        print(f"Sentence {idx+1} completed")
                        
                    except Exception as e:
                        print(f"Error: {e}")
                        break
            
            print("=== gTTS Thread finished ===")
            
        except Exception as e:
            print(f"ERROR: {e}")
        
        finally:
            self.cleanup_temp_files()
            self.is_reading = False
            self.is_paused = False
            self.current_sentence_index = 0

    def cleanup_temp_files(self):
        """Clean up temporary audio files"""
        for temp_file in self.temp_audio_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        self.temp_audio_files = []

    def toggle_pause_reading(self):
        """Toggle pause/resume"""
        if not self.is_reading:
            return
        
        if self.is_paused:
            self.is_paused = False
            self.pause_event.set()
            self.pause_btn.config(text="⏸ Pause")
        else:
            self.is_paused = True
            self.pause_event.clear()
            self.pause_btn.config(text="▶ Resume")

    def stop_reading(self):
        """Stop reading"""
        print("=== STOP READING ===")
        
        if self.is_reading:
            self.stop_event.set()
            self.pause_event.set()
            
            try:
                pygame.mixer.music.stop()
            except:
                pass
            
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=2.0)
            
            self.is_reading = False
            self.is_paused = False
            self.current_sentence_index = 0
            self.stop_event.clear()
            
            self.cleanup_temp_files()

    def on_language_change(self, event=None):
        """Handle language change"""
        self.tts_language = self.language_var.get()

    def on_speed_change(self, value):
        """Handle speed change"""
        speed = float(value)
        self.speed_label.config(text=f"{speed:.1f}x")

    def update_tts_status(self):
        """Update TTS status"""
        try:
            if self.is_reading:
                total = len(self.sentences)
                current = self.current_sentence_index + 1
                progress = f"({current}/{total})"
                
                if self.is_paused:
                    self.tts_status_label.config(text=f"⏸ Paused {progress}")
                else:
                    percent = int((current / total) * 100) if total > 0 else 0
                    self.tts_status_label.config(text=f"🔊 Reading... {progress} - {percent}%")
                
                self.pause_btn.config(state='normal')
                self.stop_btn.config(state='normal')
                self.read_chapter_btn.config(state='disabled')
                self.read_from_btn.config(state='disabled')
            else:
                self.tts_status_label.config(text="Ready")
                self.pause_btn.config(text="⏸ Pause", state='disabled')
                self.stop_btn.config(state='disabled')
                if TTS_AVAILABLE:
                    self.read_chapter_btn.config(state='normal')
                    self.read_from_btn.config(state='normal')
        except:
            pass
        
        self.parent.after(200, self.update_tts_status)