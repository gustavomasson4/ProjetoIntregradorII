import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import warnings
from database import DatabaseManager
import threading

warnings.filterwarnings("ignore", category=UserWarning, module="fitz")

# TTS imports
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("pyttsx3 not installed. Install with: pip install pyttsx3")

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
        
        # TTS attributes
        self.tts_engine = None
        self.is_reading = False
        self.is_paused = False
        self.reading_thread = None
        self.stop_event = threading.Event()
        self.current_text = ""
        self.current_sentence_index = 0
        self.sentences = []

        self.setup_ui()
        self.initialize_tts()

    def initialize_tts(self):
        """Initialize TTS engine"""
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.9)
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    self.tts_engine.setProperty('voice', voices[0].id)
            except Exception as e:
                print(f"Error initializing TTS: {e}")
                self.tts_engine = None

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # TTS controls at TOP (before control_frame)
        self.setup_tts_controls()

        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill='x', pady=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side='left')

        self.btn_open = ttk.Button(btn_frame, text="Open PDF", command=self.open_pdf)
        self.btn_open.pack(side='left', padx=5)

        self.btn_prev = ttk.Button(btn_frame, text="◄ Previous", command=self.prev_page, state='disabled')
        self.btn_prev.pack(side='left', padx=5)

        self.btn_next = ttk.Button(btn_frame, text="Next ►", command=self.next_page, state='disabled')
        self.btn_next.pack(side='left', padx=5)

        # Highlight brush button
        annot_frame = ttk.Frame(control_frame)
        annot_frame.pack(side='right', padx=20)

        self.btn_highlight_brush = ttk.Button(
            annot_frame,
            text="Highlight (Brush)",
            command=self.toggle_highlight_brush_mode
        )
        self.btn_highlight_brush.pack(side='left', padx=5)

        self.lbl_page = ttk.Label(control_frame, text="Page: 0/0")
        self.lbl_page.pack(side='left', padx=20)

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

        # Normal annotation controls
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

        self.setup_pdf_display()

        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side='right', padx=20)

        ttk.Label(search_frame, text="Search:").pack(side='left')

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=5)

        ttk.Button(
            search_frame,
            text="Find",
            command=self.search_text
        ).pack(side='left', padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side='left', padx=5)

        # Bind Ctrl+F para ativar a busca
        self.parent.bind('<Control-f>', lambda e: search_entry.focus())
        search_entry.bind('<Return>', lambda e: self.search_text())

        nav_frame = ttk.Frame(search_frame)
        nav_frame.pack(side='left', padx=5)

        ttk.Button(
            nav_frame,
            text="◄ Prev",
            command=self.prev_search_result
        ).pack(side='left', padx=2)

        ttk.Button(
            nav_frame,
            text="Next ►",
            command=self.next_search_result
        ).pack(side='left', padx=2)

        # Variáveis para controle de navegação
        self.search_results = []
        self.current_search_index = -1

    def setup_tts_controls(self):
        """Setup TTS control panel"""
        tts_frame = ttk.LabelFrame(self.main_frame, text="📖 Text Reader (TTS)", padding=10)
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
        
        ttk.Label(settings_frame, text="Speed:").pack(side='left', padx=5)
        
        self.speed_var = tk.IntVar(value=150)
        speed_scale = ttk.Scale(
            settings_frame,
            from_=50,
            to=300,
            variable=self.speed_var,
            orient='horizontal',
            length=150,
            command=self.on_speed_change
        )
        speed_scale.pack(side='left', padx=5)
        
        self.speed_label = ttk.Label(settings_frame, text="150 WPM")
        self.speed_label.pack(side='left', padx=5)
        
        ttk.Label(settings_frame, text="Volume:").pack(side='left', padx=5)
        
        self.volume_var = tk.DoubleVar(value=0.9)
        volume_scale = ttk.Scale(
            settings_frame,
            from_=0.0,
            to=1.0,
            variable=self.volume_var,
            orient='horizontal',
            length=100,
            command=self.on_volume_change
        )
        volume_scale.pack(side='left', padx=5)
        
        self.tts_status_label = ttk.Label(tts_frame, text="Ready", font=('Arial', 9, 'italic'))
        self.tts_status_label.pack(pady=5)
        
        if not TTS_AVAILABLE:
            self.tts_status_label.config(text="⚠️ TTS not available. Install pyttsx3.")
            self.read_page_btn.config(state='disabled')
            self.read_from_btn.config(state='disabled')
        
        # Start status update loop
        self.update_tts_status()

    def test_tts(self):
        """Test TTS with a simple phrase"""
        if not TTS_AVAILABLE or not self.tts_engine:
            messagebox.showerror("Error", "TTS engine not available. Install pyttsx3.")
            return
        
        test_text = "Hello! This is a test of the text to speech system. It is working correctly."
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
            
            # Clean up text
            text = text.strip()
            # Remove excessive whitespace but keep paragraph breaks
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    cleaned_lines.append(line)
            
            text = ' '.join(cleaned_lines)
            return text
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def read_current_page(self):
        """Read the current page"""
        if not TTS_AVAILABLE or not self.tts_engine:
            messagebox.showerror("Error", "TTS engine not available. Install pyttsx3.")
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
        if not TTS_AVAILABLE or not self.tts_engine:
            messagebox.showerror("Error", "TTS engine not available. Install pyttsx3.")
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
                all_text.append(f"Page {page_num + 1}. {text}")
        
        if not all_text:
            messagebox.showwarning("Warning", "No text found!")
            return
        
        combined_text = " ... ".join(all_text)
        self.start_reading(combined_text)

    def start_reading(self, text):
        """Start reading text in a separate thread"""
        if self.is_reading:
            self.stop_reading()
        
        self.current_text = text
        
        # Better sentence splitting - handle multiple punctuation marks
        import re
        # Split by . ! ? followed by space or end of string
        sentences = re.split(r'[.!?]+(?:\s+|$)', text)
        self.sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
        
        self.current_sentence_index = 0
        self.is_reading = True
        self.is_paused = False
        self.stop_event.clear()
        
        print(f"Starting to read {len(self.sentences)} sentences")
        
        self.reading_thread = threading.Thread(target=self._read_text, daemon=True)
        self.reading_thread.start()

    def _read_text(self):
        """Internal method to read text (runs in separate thread)"""
        try:
            engine = pyttsx3.init()
            
            # Get current settings
            if self.tts_engine:
                engine.setProperty('rate', self.tts_engine.getProperty('rate'))
                engine.setProperty('volume', self.tts_engine.getProperty('volume'))
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    engine.setProperty('voice', voices[0].id)
            
            print(f"Starting to speak {len(self.sentences)} sentences")
            
            while self.current_sentence_index < len(self.sentences):
                if self.stop_event.is_set():
                    print("Stop event detected, breaking")
                    break
                
                # Wait while paused
                while self.is_paused and not self.stop_event.is_set():
                    threading.Event().wait(0.1)
                
                if self.stop_event.is_set():
                    print("Stop event detected after pause, breaking")
                    break
                
                sentence = self.sentences[self.current_sentence_index]
                if sentence:
                    print(f"Speaking sentence {self.current_sentence_index + 1}: {sentence[:50]}...")
                    engine.say(sentence)
                    engine.runAndWait()
                
                self.current_sentence_index += 1
            
            print("Finished reading")
            self.is_reading = False
            self.current_sentence_index = 0
            
        except Exception as e:
            print(f"Error during reading: {e}")
            import traceback
            traceback.print_exc()
            self.is_reading = False
            self.current_sentence_index = 0

    def toggle_pause_reading(self):
        """Toggle pause/resume"""
        if self.is_paused:
            self.is_paused = False
            self.pause_btn.config(text="⏸ Pause")
        else:
            self.is_paused = True
            self.pause_btn.config(text="▶ Resume")

    def stop_reading(self):
        """Stop reading"""
        if self.is_reading:
            self.stop_event.set()
            self.is_reading = False
            self.is_paused = False
            
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=1.0)

    def on_speed_change(self, value):
        """Handle speed change"""
        speed = int(float(value))
        self.speed_label.config(text=f"{speed} WPM")
        if self.tts_engine:
            self.tts_engine.setProperty('rate', speed)

    def on_volume_change(self, value):
        """Handle volume change"""
        volume = float(value)
        if self.tts_engine:
            self.tts_engine.setProperty('volume', volume)

    def update_tts_status(self):
        """Update reading status"""
        if self.is_reading:
            if self.is_paused:
                progress = f"({self.current_sentence_index}/{len(self.sentences)})"
                self.tts_status_label.config(text=f"⏸ Paused {progress}")
            else:
                progress = f"({self.current_sentence_index}/{len(self.sentences)})"
                self.tts_status_label.config(text=f"🔊 Reading... {progress}")
            
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
        
        # Schedule next update
        self.parent.after(200, self.update_tts_status)

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill='x', pady=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side='left')

        self.btn_open = ttk.Button(btn_frame, text="Open PDF", command=self.open_pdf)
        self.btn_open.pack(side='left', padx=5)

        self.btn_prev = ttk.Button(btn_frame, text="◄ Previous", command=self.prev_page, state='disabled')
        self.btn_prev.pack(side='left', padx=5)

        self.btn_next = ttk.Button(btn_frame, text="Next ►", command=self.next_page, state='disabled')
        self.btn_next.pack(side='left', padx=5)

        # Highlight brush button
        annot_frame = ttk.Frame(control_frame)
        annot_frame.pack(side='right', padx=20)

        self.btn_highlight_brush = ttk.Button(
            annot_frame,
            text="Highlight (Brush)",
            command=self.toggle_highlight_brush_mode
        )
        self.btn_highlight_brush.pack(side='left', padx=5)

        self.lbl_page = ttk.Label(control_frame, text="Page: 0/0")
        self.lbl_page.pack(side='left', padx=20)

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

        # Normal annotation controls
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

        self.setup_pdf_display()

        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side='right', padx=20)

        ttk.Label(search_frame, text="Search:").pack(side='left')

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=5)

        ttk.Button(
            search_frame,
            text="Find",
            command=self.search_text
        ).pack(side='left', padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side='left', padx=5)

        # Bind Ctrl+F para ativar a busca
        self.parent.bind('<Control-f>', lambda e: search_entry.focus())
        search_entry.bind('<Return>', lambda e: self.search_text())

        nav_frame = ttk.Frame(search_frame)
        nav_frame.pack(side='left', padx=5)

        ttk.Button(
            nav_frame,
            text="◄ Prev",
            command=self.prev_search_result
        ).pack(side='left', padx=2)

        ttk.Button(
            nav_frame,
            text="Next ►",
            command=self.next_search_result
        ).pack(side='left', padx=2)

        # Variáveis para controle de navegação
        self.search_results = []
        self.current_search_index = -1

    def search_text(self):
        """Buscar texto no PDF"""
        search_term = self.search_var.get().strip()
        if not search_term or not self.pdf_doc:
            return

        try:
            page = self.pdf_doc.load_page(self.current_page)
            text_instances = page.search_for(search_term)

            if not text_instances:
                messagebox.showinfo("Search", f"Text '{search_term}' not found on this page")
                return

            # Limpar highlights anteriores
            self.clear_search_highlights()

            # Guardar resultados para navegação
            self.search_results = text_instances
            self.current_search_index = 0

            # Destacar todas as ocorrências
            for rect in text_instances:
                self.highlight_text(rect, search_term)

        except Exception as e:
            messagebox.showerror("Search Error", f"Failed to search text: {str(e)}")

    def show_search_result(self, index):
        """Mostrar resultado específico da busca"""
        self.clear_search_highlights()

        if 0 <= index < len(self.search_results):
            rect = self.search_results[index]
            self.highlight_text(rect, self.search_var.get())
            self.scroll_to_highlight(rect)

    def scroll_to_highlight(self, rect):
        """Fazer scroll para o highlight"""
        if not hasattr(self, 'image_origin'):
            return
        frame_x, frame_y = self.image_origin
        zoom = self.zoom_level

        y_pos = frame_y + rect.y0 * zoom
        canvas_height = self.canvas.winfo_height()
        if canvas_height > 0:
            self.canvas.yview_moveto(y_pos / canvas_height)

    def prev_search_result(self):
        """Navegar para resultado anterior"""
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.show_search_result(self.current_search_index)

    def next_search_result(self):
        """Navegar para próximo resultado"""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.show_search_result(self.current_search_index)

    def highlight_text(self, rect, search_term):
        """Destacar texto encontrado no canvas"""
        if not hasattr(self, 'image_origin'):
            return
            
        frame_x, frame_y = self.image_origin
        zoom = self.zoom_level

        # Converter coordenadas do PDF para coordenadas do canvas
        x0 = frame_x + rect.x0 * zoom
        y0 = frame_y + rect.y0 * zoom
        x1 = frame_x + rect.x1 * zoom
        y1 = frame_y + rect.y1 * zoom

        # Criar retângulo de highlight
        highlight = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline="red",
            fill="yellow",
            stipple="gray50",  # Efeito semi-transparente
            width=2,
            tags="search_highlight"
        )

        # Guardar referência para poder remover depois
        if not hasattr(self, 'search_highlights'):
            self.search_highlights = []
        self.search_highlights.append(highlight)

    def clear_search_highlights(self):
        """Limpar todos os highlights de busca"""
        if hasattr(self, 'search_highlights'):
            for highlight in self.search_highlights:
                self.canvas.delete(highlight)
            self.search_highlights = []
        else:
            self.canvas.delete("search_highlight")

    def clear_search(self):
        """Limpar busca"""
        self.search_var.set("")
        self.clear_search_highlights()
        self.search_results = []
        self.current_search_index = -1

    def setup_pdf_display(self):
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

        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<Button-1>", self.start_annotation)
        self.canvas.bind("<B1-Motion>", self.draw_annotation)
        self.canvas.bind("<ButtonRelease-1>", self.end_annotation)

    def open_pdf(self):
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
                self.file_id = 1  # Substitua por seu ID real
                self.render_page()
                self.update_controls()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open PDF:\n{str(e)}")

    def render_page(self):
        self.canvas.delete("annotation")
        self.annotations_on_canvas = []

        if not self.pdf_doc or not 0 <= self.current_page < len(self.pdf_doc):
            return

        try:
            page = self.pdf_doc.load_page(self.current_page)
            zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # --- NOVO: overlay para highlights tipo pincel
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)

            if self.file_id:
                db_highlights = DatabaseManager.get_highlights(self.file_id, self.current_page)
                for texto_destacado, cor, bbox, _ in db_highlights:
                    if bbox:
                        x1, y1, x2, y2 = map(float, bbox.split(","))
                        x1, y1 = x1 * self.zoom_level, y1 * self.zoom_level
                        x2, y2 = x2 * self.zoom_level, y2 * self.zoom_level
                        # RGBA para amarelo semi-transparente
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

            # Render annotations (caixas e textos)
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
        self.render_page()

    def prev_page(self):
        if self.pdf_doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            self.update_controls()

    def next_page(self):
        if self.pdf_doc and self.current_page < len(self.pdf_doc) - 1:
            self.current_page += 1
            self.render_page()
            self.update_controls()

    def change_zoom(self, value):
        self.zoom_level = float(value.replace("%", "")) / 100
        if self.pdf_doc:
            self.render_page()

    def update_controls(self):
        if self.pdf_doc:
            total_pages = len(self.pdf_doc)
            self.btn_prev.config(state='normal' if self.current_page > 0 else 'disabled')
            self.btn_next.config(state='normal' if self.current_page < total_pages - 1 else 'disabled')
            self.lbl_page.config(text=f"Page: {self.current_page + 1}/{total_pages}")
        else:
            self.btn_prev.config(state='disabled')
            self.btn_next.config(state='disabled')
            self.lbl_page.config(text="Page: 0/0")

    def start_annotation(self, event):
        if self.highlight_brush_mode:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            if hasattr(self, 'image_origin'):
                frame_x, frame_y = self.image_origin
                x -= frame_x
                y -= frame_y
                if x >= 0 and y >= 0:
                    self.annotation_start = (x, y)
                    self.current_annotation = {
                        'x1': x,
                        'y1': y,
                        'x2': x,
                        'y2': y,
                        'color': self.highlight_brush_color
                    }
            return  # Não faz o normal
        if not self.annotation_mode or not self.pdf_doc or not self.file_id:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        if hasattr(self, 'image_origin'):
            frame_x, frame_y = self.image_origin
            x -= frame_x
            y -= frame_y
            if x >= 0 and y >= 0:
                self.annotation_start = (x, y)
                self.current_annotation = {
                    'x1': x,
                    'y1': y,
                    'x2': x,
                    'y2': y,
                    'color': self.annotation_color
                }
                if self.temp_annotation:
                    self.canvas.delete(self.temp_annotation)
                self.temp_annotation = self.canvas.create_rectangle(
                    frame_x + x, frame_y + y,
                    frame_x + x, frame_y + y,
                    outline=self.annotation_color,
                    width=2,
                    tags="temp_annotation"
                )

    def draw_annotation(self, event):
        if self.highlight_brush_mode and self.annotation_start and self.current_annotation:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            if hasattr(self, 'image_origin'):
                frame_x, frame_y = self.image_origin
                x -= frame_x
                y -= frame_y
                self.current_annotation['x2'] = x
                self.current_annotation['y2'] = y
            return
        if not self.annotation_mode or not self.annotation_start or not self.current_annotation:
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

    def reset_annotation_state(self):
        if self.temp_annotation:
            self.canvas.delete(self.temp_annotation)
            self.temp_annotation = None
        self.annotation_start = None
        self.current_annotation = None

    def toggle_annotation_mode(self):
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

    def change_annotation_color(self, color):
        self.annotation_color = color

    def toggle_highlight_brush_mode(self):
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

    def end_annotation(self, event):
        if self.highlight_brush_mode and self.annotation_start and self.current_annotation:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            if hasattr(self, 'image_origin'):
                frame_x, frame_y = self.image_origin
                x -= frame_x
                y -= frame_y
                x1, y1 = self.annotation_start
                x2, y2 = x, y
                if x2 < x1:
                    x1, x2 = x2, x1
                if y2 < y1:
                    y1, y2 = y2, y1
                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    self.reset_annotation_state()
                    return
                if self.file_id:
                    original_x1 = x1 / self.zoom_level
                    original_y1 = y1 / self.zoom_level
                    original_x2 = x2 / self.zoom_level
                    original_y2 = y2 / self.zoom_level
                    bbox = f"{original_x1},{original_y1},{original_x2},{original_y2}"
                    DatabaseManager.save_highlight(
                        self.file_id,
                        self.current_page,
                        texto_destacado="",  # Sem texto
                        cor=self.highlight_brush_color,
                        bbox=bbox
                    )
                    self.render_page()
                self.reset_annotation_state()
            return
        if not self.annotation_mode or not self.annotation_start or not self.current_annotation:
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
                if x2 < x1:
                    x1, x2 = x2, x1
                if y2 < y1:
                    y1, y2 = y2, y1
                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    self.reset_annotation_state()
                    return
                text = simpledialog.askstring(
                    "Annotation Text",
                    "Enter annotation text (optional):",
                    parent=self.parent
                )
                if self.file_id:
                    original_x1 = x1 / self.zoom_level
                    original_y1 = y1 / self.zoom_level
                    original_x2 = x2 / self.zoom_level
                    original_y2 = y2 / self.zoom_level
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
                    else:
                        self.render_page()
                self.reset_annotation_state()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save annotation: {str(e)}")
            self.reset_annotation_state()