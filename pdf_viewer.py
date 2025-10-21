import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import warnings
from database import DatabaseManager
import threading
import re
import os
import tempfile

warnings.filterwarnings("ignore", category=UserWarning, module="fitz")

# TTS imports - Usando gTTS
try:
    from gtts import gTTS
    import pygame
    pygame.mixer.init()
    TTS_AVAILABLE = True
    print("✓ gTTS disponível e carregado!")
except ImportError as e:
    TTS_AVAILABLE = False
    print(f"✗ gTTS não disponível: {e}")
    print("Instale com: pip install gTTS pygame")

class PDFViewer:
    def __init__(self, parent):
        self.parent = parent
        self.current_page = 0
        self.pdf_doc = None
        self.zoom_level = 1.0
        self.image_cache = []
        self.file_id = None
        self.annotation_mode = False
        self.current_annotation = None
        self.annotation_start = None
        self.annotation_color = "red"
        self.temp_annotation = None
        self.temp_highlight = None
        self.annotations_on_canvas = []
        self.pdf_path = None
        
        # Highlight (brush) mode
        self.highlight_brush_mode = False
        self.highlight_brush_color = "yellow"
        
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
        self.tts_language = 'pt'  # Idioma padrão: português
        self.tts_speed = 1.0  # Velocidade normal
        self.tts_controls_created = False

        # Search variables
        self.search_results = []
        self.current_search_index = -1
        self.search_highlights = []

        self.setup_ui()

    def setup_ui(self):
        """Setup the complete UI"""
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # TTS controls at TOP - APENAS UMA VEZ
        if not self.tts_controls_created:
            self.setup_tts_controls()
            self.tts_controls_created = True

        # Main control frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill='x', pady=5)

        # Left buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side='left')

        self.btn_open = ttk.Button(btn_frame, text="Open PDF", command=self.open_pdf)
        self.btn_open.pack(side='left', padx=5)

        self.btn_prev = ttk.Button(btn_frame, text="◄ Previous", command=self.prev_page, state='disabled')
        self.btn_prev.pack(side='left', padx=5)

        self.btn_next = ttk.Button(btn_frame, text="Next ►", command=self.next_page, state='disabled')
        self.btn_next.pack(side='left', padx=5)

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

        # Annotation controls
        annot_frame = ttk.Frame(control_frame)
        annot_frame.pack(side='right', padx=20)

        self.btn_highlight_brush = ttk.Button(
            annot_frame,
            text="Highlight (Brush)",
            command=self.toggle_highlight_brush_mode
        )
        self.btn_highlight_brush.pack(side='left', padx=5)

        self.btn_annotate = ttk.Button(
            annot_frame,
            text="Add Annotation",
            command=self.toggle_annotation_mode
        )
        self.btn_annotate.pack(side='left', padx=5)

        color_frame = ttk.Frame(annot_frame)
        color_frame.pack(side='left', padx=5)

        ttk.Label(color_frame, text="Color:").pack(side='left')

        self.color_var = tk.StringVar(value="red")
        color_menu = ttk.OptionMenu(
            color_frame,
            self.color_var,
            "red",
            "red", "blue", "green", "yellow", "black",
            command=self.change_annotation_color
        )
        color_menu.pack(side='left')

        # Search controls
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side='right', padx=20)

        ttk.Label(search_frame, text="Search:").pack(side='left')

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=5)

        ttk.Button(search_frame, text="Find", command=self.search_text).pack(side='left', padx=5)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side='left', padx=5)

        # Search navigation
        nav_frame = ttk.Frame(search_frame)
        nav_frame.pack(side='left', padx=5)

        ttk.Button(nav_frame, text="◄ Prev", command=self.prev_search_result).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="Next ►", command=self.next_search_result).pack(side='left', padx=2)

        # Bind keyboard shortcuts
        self.parent.bind('<Control-f>', lambda e: search_entry.focus())
        search_entry.bind('<Return>', lambda e: self.search_text())

        # PDF Display
        self.setup_pdf_display()

    def setup_tts_controls(self):
        """Setup TTS control panel with gTTS"""
        tts_frame = ttk.LabelFrame(self.main_frame, text="📖 Text Reader (Google TTS)", padding=10)
        tts_frame.pack(side='top', fill='x', pady=(0, 5))
        
        # Button frame
        button_frame = ttk.Frame(tts_frame)
        button_frame.pack(fill='x', pady=5)
        
        self.read_page_btn = ttk.Button(
            button_frame,
            text="▶ Read Page",
            command=self.read_current_page
        )
        self.read_page_btn.pack(side='left', padx=2)
        
        self.read_from_btn = ttk.Button(
            button_frame,
            text="▶▶ Read From Here",
            command=self.read_from_page
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
        
        # Test button
        ttk.Button(
            button_frame,
            text="🔊 Test",
            command=self.test_tts
        ).pack(side='left', padx=10)
        
        # Settings frame
        settings_frame = ttk.Frame(tts_frame)
        settings_frame.pack(fill='x', pady=5)
        
        # Language selection
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
        
        # Speed control
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
            self.read_page_btn.config(state='disabled')
            self.read_from_btn.config(state='disabled')
        
        # Start status update loop
        self.update_tts_status()

    def setup_pdf_display(self):
        """Setup PDF display area with canvas and scrollbars"""
        container = ttk.Frame(self.main_frame)
        container.pack(expand=True, fill='both')

        self.canvas = tk.Canvas(container, bg='white')
        self.canvas.pack(side='left', expand=True, fill='both')

        v_scroll = ttk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        v_scroll.pack(side='right', fill='y')

        h_scroll = ttk.Scrollbar(container, orient='horizontal', command=self.canvas.xview)
        h_scroll.pack(side='bottom', fill='x')

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.pdf_frame = ttk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window(
            (0, 0),
            window=self.pdf_frame,
            anchor='nw',
            tags="pdf_frame"
        )

        self.pdf_label = ttk.Label(self.pdf_frame)
        self.pdf_label.pack()

        # Bind events
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<Button-1>", self.start_annotation)
        self.canvas.bind("<B1-Motion>", self.draw_annotation)
        self.canvas.bind("<ButtonRelease-1>", self.end_annotation)

    # ============= TTS METHODS - gTTS =============
    
    def test_tts(self):
        """Test TTS with a simple phrase"""
        print("\n" + "="*60)
        print("=== TTS TEST STARTED (gTTS) ===")
        print(f"TTS_AVAILABLE: {TTS_AVAILABLE}")
        print(f"is_reading: {self.is_reading}")
        print(f"is_paused: {self.is_paused}")
        print(f"Language: {self.tts_language}")
        print("="*60 + "\n")
        
        if not TTS_AVAILABLE:
            messagebox.showerror("Error", "gTTS not available. Install: pip install gTTS pygame")
            return
        
        test_text = "Olá! Este é um teste do sistema de conversão de texto em fala usando Google TTS. O áudio deve ser claro e completo."
        self.start_reading(test_text)

    def extract_page_text(self, page_number=None):
        """Extract text from current or specified page"""
        if not self.pdf_doc:
            return ""
        
        if page_number is None:
            page_number = self.current_page
        
        try:
            page = self.pdf_doc[page_number]
            text = page.get_text()
            text = text.strip()
            text = re.sub(r'\s+', ' ', text)
            return text
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def read_current_page(self):
        """Read the current page"""
        if not TTS_AVAILABLE:
            messagebox.showerror("Error", "gTTS not available.")
            return
        
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF document loaded!")
            return
        
        text = self.extract_page_text()
        
        if not text:
            messagebox.showwarning("Warning", "No text found on current page!")
            return
        
        self.start_reading(text)

    def read_from_page(self, start_page=None):
        """Read from specified page to end of document"""
        if not TTS_AVAILABLE:
            messagebox.showerror("Error", "gTTS not available.")
            return
        
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF document loaded!")
            return
        
        if start_page is None:
            start_page = self.current_page
        
        all_text = []
        for page_num in range(start_page, len(self.pdf_doc)):
            text = self.extract_page_text(page_num)
            if text:
                all_text.append(f"Página {page_num + 1}. {text}")
        
        if not all_text:
            messagebox.showwarning("Warning", "No text found!")
            return
        
        combined_text = " ".join(all_text)
        self.start_reading(combined_text)

    def start_reading(self, text):
        """Start reading text with gTTS"""
        print("\n" + "="*60)
        print("=== START READING (gTTS) ===")
        
        # Stop previous reading
        if self.is_reading:
            print("Stopping previous reading...")
            self.stop_reading()
            import time
            time.sleep(0.5)
        
        # Clean up any remaining temp files
        self.cleanup_temp_files()
        
        self.current_text = text
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        self.sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]
        
        if not self.sentences:
            messagebox.showwarning("Warning", "No valid text to read!")
            return
        
        # Reset state
        self.current_sentence_index = 0
        self.is_reading = True
        self.is_paused = False
        self.stop_event.clear()
        self.pause_event.set()
        
        # IMPORTANTE: Capturar valores ANTES de iniciar a thread
        self.tts_language = self.language_var.get()
        self.tts_speed = self.speed_var.get()
        
        print(f"Starting to read {len(self.sentences)} sentences")
        print(f"Language: {self.tts_language}, Speed: {self.tts_speed}x")
        
        # Start reading thread
        self.reading_thread = threading.Thread(target=self._read_text_gtts, daemon=True)
        self.reading_thread.start()
        print("="*60 + "\n")

    def _read_text_gtts(self):
        """Read text using gTTS in separate thread"""
        print("=== gTTS Thread started ===")
        
        try:
            # Usar valores já capturados (não acessar Tkinter vars)
            language = self.tts_language
            speed = self.tts_speed
            use_slow = (speed < 0.8)
            
            print(f"Thread settings - Language: {language}, Speed: {speed}, Slow: {use_slow}")
            
            for idx in range(len(self.sentences)):
                # Check stop
                if self.stop_event.is_set():
                    print(f"Stop detected at sentence {idx}")
                    break
                
                # Wait while paused
                while not self.pause_event.is_set():
                    if self.stop_event.is_set():
                        break
                    threading.Event().wait(0.1)
                
                if self.stop_event.is_set():
                    break
                
                self.current_sentence_index = idx
                sentence = self.sentences[idx]
                
                if sentence:
                    print(f"[{idx+1}/{len(self.sentences)}] Speaking: {sentence[:60]}...")
                    
                    try:
                        # Generate audio with gTTS
                        tts = gTTS(text=sentence, lang=language, slow=use_slow)
                        
                        # Save to temp file
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        temp_file.close()
                        tts.save(temp_file.name)
                        self.temp_audio_files.append(temp_file.name)
                        
                        # Play with pygame
                        pygame.mixer.music.load(temp_file.name)
                        pygame.mixer.music.play()
                        
                        # Wait for playback to finish
                        while pygame.mixer.music.get_busy():
                            if self.stop_event.is_set():
                                pygame.mixer.music.stop()
                                break
                            
                            # Handle pause
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
                        print(f"Error speaking sentence {idx+1}: {e}")
                        import traceback
                        traceback.print_exc()
                        break
            
            print("=== gTTS Thread finished ===")
            
        except Exception as e:
            print(f"ERROR in gTTS thread: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print("=== gTTS cleanup starting ===")
            self.cleanup_temp_files()
            self.is_reading = False
            self.is_paused = False
            self.current_sentence_index = 0
            print("=== gTTS cleanup complete ===")

    def cleanup_temp_files(self):
        """Clean up temporary audio files"""
        for temp_file in self.temp_audio_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Error removing temp file: {e}")
        self.temp_audio_files = []

    def toggle_pause_reading(self):
        """Toggle pause/resume"""
        if not self.is_reading:
            return
        
        if self.is_paused:
            print("Resuming...")
            self.is_paused = False
            self.pause_event.set()
            self.pause_btn.config(text="⏸ Pause")
        else:
            print("Pausing...")
            self.is_paused = True
            self.pause_event.clear()
            self.pause_btn.config(text="▶ Resume")

    def stop_reading(self):
        """Stop reading"""
        print("=== STOP READING ===")
        
        if self.is_reading:
            self.stop_event.set()
            self.pause_event.set()
            
            # Stop pygame mixer
            try:
                pygame.mixer.music.stop()
            except:
                pass
            
            # Wait for thread
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=2.0)
            
            self.is_reading = False
            self.is_paused = False
            self.current_sentence_index = 0
            self.stop_event.clear()
            
            # Clean up temp files
            self.cleanup_temp_files()
        
        print("=== STOP complete ===")

    def on_language_change(self, event=None):
        """Handle language change"""
        self.tts_language = self.language_var.get()
        print(f"Language changed to: {self.tts_language}")

    def on_speed_change(self, value):
        """Handle speed change"""
        speed = float(value)
        self.speed_label.config(text=f"{speed:.1f}x")

    def update_tts_status(self):
        """Update TTS status display"""
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
                self.read_page_btn.config(state='disabled')
                self.read_from_btn.config(state='disabled')
            else:
                self.tts_status_label.config(text="Ready")
                self.pause_btn.config(text="⏸ Pause", state='disabled')
                self.stop_btn.config(state='disabled')
                if TTS_AVAILABLE:
                    self.read_page_btn.config(state='normal')
                    self.read_from_btn.config(state='normal')
        except Exception as e:
            print(f"Error updating TTS status: {e}")
        
        # Schedule next update
        self.parent.after(200, self.update_tts_status)

    # ============= PDF VIEWING METHODS =============
    
    def open_pdf(self):
        """Open a PDF file"""
        filepath = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if filepath:
            try:
                if self.pdf_doc:
                    self.pdf_doc.close()
                    self.image_cache.clear()
                self.pdf_doc = fitz.open(filepath)
                self.pdf_path = filepath
                self.current_page = 0
                self.file_id = 1
                self.render_page()
                self.update_controls()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open PDF:\n{str(e)}")

    def render_page(self):
        """Render the current PDF page"""
        self.canvas.delete("annotation")
        self.canvas.delete("search_highlight")
        self.annotations_on_canvas = []

        if not self.pdf_doc or not 0 <= self.current_page < len(self.pdf_doc):
            return

        try:
            page = self.pdf_doc.load_page(self.current_page)
            zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Add highlights overlay
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)

            if self.file_id:
                db_highlights = DatabaseManager.get_highlights(self.file_id, self.current_page)
                for texto_destacado, cor, bbox, _ in db_highlights:
                    if bbox:
                        x1, y1, x2, y2 = map(float, bbox.split(","))
                        x1, y1 = x1 * self.zoom_level, y1 * self.zoom_level
                        x2, y2 = x2 * self.zoom_level, y2 * self.zoom_level
                        color_rgba = (255, 255, 0, 80) if cor == "yellow" else (255, 0, 0, 80)
                        overlay_draw.rectangle([x1, y1, x2, y2], fill=color_rgba)

            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")

            photo = ImageTk.PhotoImage(image=img)
            self.image_cache = [photo]

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            x = max((canvas_width - pix.width) // 2, 0)
            y = max((canvas_height - pix.height) // 2, 0)

            self.canvas.delete("pdf_image")
            self.canvas_image = self.canvas.create_image(x, y, anchor='nw', image=photo, tags="pdf_image")
            self.image_origin = (x, y)
            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))

            # Render annotations
            if self.file_id:
                db_annotations = DatabaseManager.get_annotations(self.file_id, self.current_page)
                for annot in db_annotations:
                    x1, y1, x2, y2, text, color = annot
                    x1, y1 = x1 * self.zoom_level, y1 * self.zoom_level
                    x2, y2 = x2 * self.zoom_level, y2 * self.zoom_level
                    rect = self.canvas.create_rectangle(
                        x + x1, y + y1,
                        x + x2, y + y2,
                        outline=color,
                        width=2,
                        tags="annotation"
                    )
                    self.annotations_on_canvas.append(rect)
                    if text:
                        text_item = self.canvas.create_text(
                            x + x1, y + y1 - 15,
                            text=text,
                            fill=color,
                            anchor='nw',
                            tags="annotation"
                        )
                        self.annotations_on_canvas.append(text_item)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to render page:\n{str(e)}")

    def on_canvas_configure(self, event=None):
        """Handle canvas resize"""
        self.render_page()

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
        """Change zoom level"""
        self.zoom_level = float(value.replace("%", "")) / 100
        if self.pdf_doc:
            self.render_page()

    def update_controls(self):
        """Update navigation controls"""
        if self.pdf_doc:
            total_pages = len(self.pdf_doc)
            self.btn_prev.config(state='normal' if self.current_page > 0 else 'disabled')
            self.btn_next.config(state='normal' if self.current_page < total_pages - 1 else 'disabled')
            self.lbl_page.config(text=f"Page: {self.current_page + 1}/{total_pages}")
        else:
            self.btn_prev.config(state='disabled')
            self.btn_next.config(state='disabled')
            self.lbl_page.config(text="Page: 0/0")

    # ============= ANNOTATION METHODS =============
    
    def toggle_annotation_mode(self):
        """Toggle annotation mode"""
        self.annotation_mode = not self.annotation_mode
        if self.annotation_mode:
            self.btn_annotate.config(text="Cancel Annotation")
            self.canvas.config(cursor="cross")
            self.highlight_brush_mode = False
            self.btn_highlight_brush.config(text="Highlight (Brush)")
        else:
            self.btn_annotate.config(text="Add Annotation")
            self.canvas.config(cursor="")
            self.reset_annotation_state()

    def toggle_highlight_brush_mode(self):
        """Toggle highlight brush mode"""
        self.highlight_brush_mode = not self.highlight_brush_mode
        if self.highlight_brush_mode:
            self.btn_highlight_brush.config(text="Cancel Highlight")
            self.canvas.config(cursor="spraycan")
            self.annotation_mode = False
            self.btn_annotate.config(text="Add Annotation")
        else:
            self.btn_highlight_brush.config(text="Highlight (Brush)")
            self.canvas.config(cursor="")
            self.reset_annotation_state()

    def change_annotation_color(self, color):
        """Change annotation color"""
        self.annotation_color = color

    def start_annotation(self, event):
        """Start creating an annotation or highlight"""
        if not self.pdf_doc or not self.file_id:
            return
            
        if not self.annotation_mode and not self.highlight_brush_mode:
            return

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if hasattr(self, 'image_origin'):
            frame_x, frame_y = self.image_origin
            x -= frame_x
            y -= frame_y
            
            if x >= 0 and y >= 0:
                self.annotation_start = (x, y)
                color = self.highlight_brush_color if self.highlight_brush_mode else self.annotation_color
                self.current_annotation = {
                    'x1': x,
                    'y1': y,
                    'x2': x,
                    'y2': y,
                    'color': color
                }
                
                if self.temp_annotation:
                    self.canvas.delete(self.temp_annotation)
                    
                self.temp_annotation = self.canvas.create_rectangle(
                    frame_x + x, frame_y + y,
                    frame_x + x, frame_y + y,
                    outline=color,
                    width=2,
                    tags="temp_annotation"
                )

    def draw_annotation(self, event):
        """Update annotation while dragging"""
        if not self.annotation_start or not self.current_annotation:
            return
        
        if not self.annotation_mode and not self.highlight_brush_mode:
            return

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if hasattr(self, 'image_origin'):
            frame_x, frame_y = self.image_origin
            x -= frame_x
            y -= frame_y
            
            self.current_annotation['x2'] = x
            self.current_annotation['y2'] = y
            
            x1, y1 = self.annotation_start
            x2, y2 = x, y
            
            # Ensure proper ordering
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            
            if self.temp_annotation:
                self.canvas.coords(
                    self.temp_annotation,
                    frame_x + x1, frame_y + y1,
                    frame_x + x2, frame_y + y2
                )

    def end_annotation(self, event):
        """Finish creating an annotation or highlight"""
        if not self.annotation_start or not self.current_annotation:
            return
        
        if not self.annotation_mode and not self.highlight_brush_mode:
            return

        try:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            if hasattr(self, 'image_origin'):
                frame_x, frame_y = self.image_origin
                x -= frame_x
                y -= frame_y
                
                x1, y1 = self.annotation_start
                x2, y2 = x, y
                
                # Ensure proper ordering
                if x2 < x1:
                    x1, x2 = x2, x1
                if y2 < y1:
                    y1, y2 = y2, y1
                
                # Check minimum size
                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    self.reset_annotation_state()
                    return
                
                if self.file_id:
                    # Convert to original coordinates
                    original_x1 = x1 / self.zoom_level
                    original_y1 = y1 / self.zoom_level
                    original_x2 = x2 / self.zoom_level
                    original_y2 = y2 / self.zoom_level
                    
                    if self.highlight_brush_mode:
                        # Save highlight
                        bbox = f"{original_x1},{original_y1},{original_x2},{original_y2}"
                        DatabaseManager.save_highlight(
                            self.file_id,
                            self.current_page,
                            texto_destacado="",
                            cor=self.highlight_brush_color,
                            bbox=bbox
                        )
                    else:
                        # Save annotation with optional text
                        text = simpledialog.askstring(
                            "Annotation Text",
                            "Enter annotation text (optional):",
                            parent=self.parent
                        )
                        
                        success = DatabaseManager.save_annotation(
                            self.file_id,
                            self.current_page,
                            original_x1, original_y1,
                            original_x2, original_y2,
                            text,
                            self.annotation_color
                        )
                        
                        if not success:
                            messagebox.showerror("Error", "Failed to save annotation!")
                    
                    self.render_page()
                
                self.reset_annotation_state()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save annotation: {str(e)}")
            self.reset_annotation_state()

    def reset_annotation_state(self):
        """Reset annotation state"""
        if self.temp_annotation:
            self.canvas.delete(self.temp_annotation)
            self.temp_annotation = None
        self.annotation_start = None
        self.current_annotation = None

    # ============= SEARCH METHODS =============
    
    def search_text(self):
        """Search for text in the current page"""
        search_term = self.search_var.get().strip()
        if not search_term or not self.pdf_doc:
            return

        try:
            page = self.pdf_doc.load_page(self.current_page)
            text_instances = page.search_for(search_term)

            if not text_instances:
                messagebox.showinfo("Search", f"Text '{search_term}' not found on this page")
                return

            # Clear previous highlights
            self.clear_search_highlights()

            # Store results for navigation
            self.search_results = text_instances
            self.current_search_index = 0

            # Highlight all occurrences
            for rect in text_instances:
                self.highlight_text(rect, search_term)

        except Exception as e:
            messagebox.showerror("Search Error", f"Failed to search text: {str(e)}")

    def highlight_text(self, rect, search_term):
        """Highlight found text on canvas"""
        if not hasattr(self, 'image_origin'):
            return
            
        frame_x, frame_y = self.image_origin
        zoom = self.zoom_level

        # Convert PDF coordinates to canvas coordinates
        x0 = frame_x + rect.x0 * zoom
        y0 = frame_y + rect.y0 * zoom
        x1 = frame_x + rect.x1 * zoom
        y1 = frame_y + rect.y1 * zoom

        # Create highlight rectangle
        highlight = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline="red",
            fill="yellow",
            stipple="gray50",
            width=2,
            tags="search_highlight"
        )

        self.search_highlights.append(highlight)

    def clear_search_highlights(self):
        """Clear all search highlights"""
        for highlight in self.search_highlights:
            self.canvas.delete(highlight)
        self.search_highlights = []
        self.canvas.delete("search_highlight")

    def clear_search(self):
        """Clear search"""
        self.search_var.set("")
        self.clear_search_highlights()
        self.search_results = []
        self.current_search_index = -1

    def prev_search_result(self):
        """Navigate to previous search result"""
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.show_search_result(self.current_search_index)

    def next_search_result(self):
        """Navigate to next search result"""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.show_search_result(self.current_search_index)

    def show_search_result(self, index):
        """Show specific search result"""
        self.clear_search_highlights()

        if 0 <= index < len(self.search_results):
            rect = self.search_results[index]
            self.highlight_text(rect, self.search_var.get())
            self.scroll_to_highlight(rect)

    def scroll_to_highlight(self, rect):
        """Scroll canvas to show highlight"""
        if not hasattr(self, 'image_origin'):
            return
        
        frame_x, frame_y = self.image_origin
        zoom = self.zoom_level

        y_pos = frame_y + rect.y0 * zoom
        canvas_height = self.canvas.winfo_height()
        
        if canvas_height > 0:
            self.canvas.yview_moveto(y_pos / canvas_height)