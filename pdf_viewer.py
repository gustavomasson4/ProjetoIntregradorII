import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import warnings
from database import DatabaseManager

warnings.filterwarnings("ignore", category=UserWarning, module="fitz")

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

        self.setup_ui()

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
            frame_x, frame_y = self.image_origin
            x -= frame_x
            y -= frame_y
            self.current_annotation['x2'] = x
            self.current_annotation['y2'] = y
            # No modo pincel, não desenha overlay na tela (só salva no banco e mostra na próxima render_page)
            return
        if not self.annotation_mode or not self.annotation_start or not self.current_annotation:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
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
        # Não precisa deletar temp_highlight (virtual, não desenhado no canvas)
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