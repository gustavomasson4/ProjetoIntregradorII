import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import ttk, messagebox

class PDFViewer:
    def __init__(self, parent):
        self.parent = parent
        self.current_page = 0
        self.file_id = None
        self.pdf_doc = None
        self.zoom_level = 1.0
        self.annotation_mode = False
        self.annotation_color = "red"
        self.setup_ui()

    def setup_ui(self):
        """Setup the PDF viewer UI"""
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        self.canvas = tk.Canvas(self.main_frame, bg='white')
        self.canvas.pack(expand=True, fill='both')
        self.btn_prev = ttk.Button(self.main_frame, text="◄ Previous", command=self.prev_page)
        self.btn_next = ttk.Button(self.main_frame, text="Next ►", command=self.next_page)

    def load_pdf(self, filepath):
        """Load a PDF file"""
        self.pdf_doc = fitz.open(filepath)
        self.render_page()

    def render_page(self):
        """Render the current PDF page"""
        if self.pdf_doc:
            page = self.pdf_doc.load_page(self.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_level, self.zoom_level))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor='nw', image=photo)
            self.canvas.image = photo  # Keep reference