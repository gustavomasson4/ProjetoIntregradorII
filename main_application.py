import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pdf_viewer import PDFViewer

class MainApplication:
    def __init__(self, root, user_email):
        self.user_email = user_email
        self.root = root
        self.configure_window()
        self.setup_ui()

    def configure_window(self):
        """Configure main window settings"""
        self.root.title("PDF Library")
        self.root.geometry("1024x768")
        self.root.resizable(True, True)

    def setup_ui(self):
        """Setup UI components"""
        # Create a notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both')

        # Add tabs
        tab_pdf_viewer = ttk.Frame(notebook)
        tab_library = ttk.Frame(notebook)
        notebook.add(tab_pdf_viewer, text="Visualizador de PDF")
        notebook.add(tab_library, text="Biblioteca")

        # Setup PDF Viewer Tab
        self.setup_pdf_viewer_tab(tab_pdf_viewer)

        # Setup Library Tab
        self.setup_library_tab(tab_library)

    def setup_pdf_viewer_tab(self, tab):
        """Setup the PDF Viewer tab"""
        # Add a label to indicate the purpose of the tab
        ttk.Label(tab, text="Visualizador de PDFs", font=("Arial", 16)).pack(pady=10)

        # Add the "Open PDF" button
        open_pdf_button = ttk.Button(tab, text="Abrir PDF", command=self.open_pdf)
        open_pdf_button.pack(pady=10)

        # Add the PDF Viewer component
        self.pdf_viewer = PDFViewer(tab)
        self.pdf_viewer.main_frame.pack(expand=True, fill='both')

    def setup_library_tab(self, tab):
        """Setup the library tab"""
        ttk.Label(tab, text=f"Bem-vindo(a), {self.user_email}!", font=("Arial", 16)).pack(anchor='center', pady=20)
        ttk.Label(tab, text="Esta é sua biblioteca onde você pode gerenciar seus arquivos.", font=("Arial", 12)).pack(anchor='center')

    def open_pdf(self):
        """Open a PDF file and load it into the viewer"""
        filepath = filedialog.askopenfilename(
            title="Selecione um arquivo PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if filepath:
            try:
                self.pdf_viewer.load_pdf(filepath)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o PDF:\n{str(e)}")