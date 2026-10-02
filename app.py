"""
Payslip Splitter Desktop App
A modern Python desktop application for splitting a multi-page PDF of payslips.
Extracts the Matricule from each page and saves it as `<matricule>.pdf`.
Supports both native text and image-based PDFs (via OCR).
"""

import customtkinter as ctk
import threading
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# ─── Optional OCR imports ─────────────────────────────────────────────────────
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True

    # Auto-detect Tesseract on Windows
    _tess_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\marwe\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\Users\marwe\AppData\Local\Tesseract-OCR\tesseract.exe",
    ]
    for _p in _tess_paths:
        if os.path.isfile(_p):
            pytesseract.pytesseract.tesseract_cmd = _p
            break
except ImportError:
    OCR_AVAILABLE = False


def _find_poppler_path() -> str | None:
    script_dir = Path(__file__).parent.resolve()
    for candidate in script_dir.glob("poppler/**/bin"):
        if (candidate / "pdftoppm.exe").exists():
            return str(candidate)
    system_paths = [
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files (x86)\poppler\bin",
        r"C:\poppler\bin",
    ]
    for sp in system_paths:
        if os.path.isfile(os.path.join(sp, "pdftoppm.exe")):
            return sp
    return None

POPPLER_PATH = _find_poppler_path()

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from pypdf import PdfReader, PdfWriter


# ─── App Configuration ────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE  = "Payslip Splitter Pro"
APP_VERSION = "2.0.0"
ACCENT_COLOR  = "#7C3AED"
ACCENT_HOVER  = "#6D28D9"
BG_PRIMARY    = "#0F0F1A"
BG_SECONDARY  = "#16162A"
BG_CARD       = "#1E1E35"
TEXT_PRIMARY  = "#F1F1FF"
TEXT_MUTED    = "#8888AA"
SUCCESS_COLOR = "#10B981"
ERROR_COLOR   = "#EF4444"
WARNING_COLOR = "#F59E0B"
OCR_COLOR     = "#06B6D4"


# ─── Service ──────────────────────────────────────────────────────────────────

class PayslipSplitterService:
    @staticmethod
    def extract_matricule_from_text(text: str) -> str | None:
        """
        Looks for the word MATRICULE and grabs the first number found after it.
        """
        # Look for MATRICULE followed by optional text/newlines, then capture the first group of digits
        match = re.search(r'MATRICULE.*?\n.*?(\d{3,})', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        
        # Fallback: just look for the word MATRICULE and grab the next digit sequence anywhere
        match = re.search(r'MATRICULE\D*(\d{3,})', text, re.IGNORECASE)
        if match:
            return match.group(1)
            
        return None

    @staticmethod
    def split_payslips(pdf_path: str, output_dir: str, progress_callback, log_callback) -> None:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # For OCR, we need to convert pages to images. We do this lazily per page.
        for i in range(total_pages):
            progress_callback(i, total_pages)
            page = reader.pages[i]
            
            # 1. Try native text extraction first
            text = page.extract_text() or ""
            matricule = PayslipSplitterService.extract_matricule_from_text(text)
            
            # 2. If no text or no matricule found, fallback to OCR for this page
            used_ocr = False
            if not matricule and OCR_AVAILABLE and POPPLER_PATH:
                log_callback(f"Page {i+1}: No native text found. Running OCR...", WARNING_COLOR)
                try:
                    images = convert_from_path(
                        pdf_path, 
                        dpi=300, 
                        first_page=i+1, 
                        last_page=i+1, 
                        poppler_path=POPPLER_PATH
                    )
                    if images:
                        text = pytesseract.image_to_string(images[0], lang="eng+fra+ara")
                        matricule = PayslipSplitterService.extract_matricule_from_text(text)
                        used_ocr = True
                except Exception as e:
                    log_callback(f"Page {i+1}: OCR Error - {e}", ERROR_COLOR)
            
            if not matricule:
                matricule = f"UNKNOWN_PAGE_{i+1}"
                log_callback(f"Page {i+1}: Could not find matricule. Saving as {matricule}.pdf", ERROR_COLOR)
            else:
                mode = "[OCR]" if used_ocr else "[Native]"
                log_callback(f"Page {i+1}: Found matricule {matricule} {mode}", SUCCESS_COLOR)
            
            # 3. Save the single page
            writer = PdfWriter()
            writer.add_page(page)
            
            out_filename = f"{matricule}.pdf"
            out_filepath = os.path.join(output_dir, out_filename)
            
            # Handle duplicate matricules (e.g., if a person has 2 pages)
            counter = 1
            while os.path.exists(out_filepath):
                out_filename = f"{matricule}_{counter}.pdf"
                out_filepath = os.path.join(output_dir, out_filename)
                counter += 1
                
            with open(out_filepath, "wb") as f_out:
                writer.write(f_out)
                
        progress_callback(total_pages, total_pages)


# ─── UI ───────────────────────────────────────────────────────────────────────

class StatusBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_SECONDARY, corner_radius=0, height=32, **kwargs)
        self._dot = ctk.CTkLabel(self, text="●", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        self._dot.pack(side="left", padx=(14, 4))
        self._msg = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self._msg.pack(side="left")
        ctk.CTkLabel(self, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side="right", padx=14)

    def set(self, message: str, color: str = TEXT_MUTED) -> None:
        self._msg.configure(text=message, text_color=color)
        self._dot.configure(text_color=color)


class PayslipSplitterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._input_pdf: str = ""
        self._output_dir: str = ""
        
        self._configure_window()
        self._build_ui()

    def _configure_window(self) -> None:
        self.title(APP_TITLE)
        self.geometry("900x600")
        self.minsize(800, 500)
        self.configure(fg_color=BG_PRIMARY)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 900) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"900x600+{x}+{y}")

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=0, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=14)
        ctk.CTkLabel(title_frame, text="⬡", font=ctk.CTkFont(size=22), text_color=ACCENT_COLOR).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(title_frame, text="Payslip Splitter", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Select Files Grid
        file_frame = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14)
        file_frame.pack(fill="x", pady=(0, 20))
        
        # Input PDF
        self._btn_input = ctk.CTkButton(file_frame, text="1. Select Input PDF", width=160, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, command=self._select_input)
        self._btn_input.grid(row=0, column=0, padx=20, pady=20)
        self._lbl_input = ctk.CTkLabel(file_frame, text="No file selected", text_color=TEXT_MUTED)
        self._lbl_input.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        # Output Dir
        self._btn_output = ctk.CTkButton(file_frame, text="2. Select Output Folder", width=160, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, command=self._select_output)
        self._btn_output.grid(row=1, column=0, padx=20, pady=(0, 20))
        self._lbl_output = ctk.CTkLabel(file_frame, text="No folder selected", text_color=TEXT_MUTED)
        self._lbl_output.grid(row=1, column=1, sticky="w", padx=(0, 20))
        
        # Action
        self._btn_split = ctk.CTkButton(body, text="▶ Start Splitting", height=45, fg_color=SUCCESS_COLOR, hover_color="#059669", text_color="white", font=ctk.CTkFont(weight="bold", size=14), command=self._start_split, state="disabled")
        self._btn_split.pack(fill="x", pady=(0, 20))

        # Progress
        self._progress = ctk.CTkProgressBar(body, fg_color=BG_SECONDARY, progress_color=ACCENT_COLOR, height=8)
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(0, 10))
        
        # Logs
        self._log_box = ctk.CTkTextbox(body, fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=12), corner_radius=10)
        self._log_box.pack(fill="both", expand=True)
        self._log_box.insert("end", "Waiting to start...\n")
        self._log_box.configure(state="disabled")

        # Status
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")

    def _select_input(self) -> None:
        path = filedialog.askopenfilename(title="Select Payslips PDF", filetypes=[("PDF files", "*.pdf")])
        if path:
            self._input_pdf = path
            self._lbl_input.configure(text=Path(path).name, text_color=TEXT_PRIMARY)
            self._check_ready()

    def _select_output(self) -> None:
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self._output_dir = path
            self._lbl_output.configure(text=path, text_color=TEXT_PRIMARY)
            self._check_ready()

    def _check_ready(self) -> None:
        if self._input_pdf and self._output_dir:
            self._btn_split.configure(state="normal")

    def _log(self, msg: str, color: str = TEXT_PRIMARY) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _start_split(self) -> None:
        self._btn_split.configure(state="disabled", text="Splitting...")
        self._btn_input.configure(state="disabled")
        self._btn_output.configure(state="disabled")
        self._progress.set(0)
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        
        self._status.set("Processing...", WARNING_COLOR)
        
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            def on_progress(current, total):
                val = current / total if total > 0 else 1
                self.after(0, self._progress.set, val)
                self.after(0, self._status.set, f"Processing page {current+1} of {total}...", WARNING_COLOR)
                
            def on_log(msg, color):
                self.after(0, self._log, msg, color)

            PayslipSplitterService.split_payslips(self._input_pdf, self._output_dir, on_progress, on_log)
            self.after(0, self._on_done)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_done(self) -> None:
        self._btn_split.configure(state="normal", text="▶ Start Splitting")
        self._btn_input.configure(state="normal")
        self._btn_output.configure(state="normal")
        self._status.set("✓ Splitting complete!", SUCCESS_COLOR)
        messagebox.showinfo("Success", "All payslips have been split successfully!")

    def _on_error(self, err: str) -> None:
        self._btn_split.configure(state="normal", text="▶ Start Splitting")
        self._btn_input.configure(state="normal")
        self._btn_output.configure(state="normal")
        self._status.set("✗ Error occurred", ERROR_COLOR)
        self._log(f"ERROR: {err}", ERROR_COLOR)
        messagebox.showerror("Error", f"Failed to split PDF:\n\n{err}")


if __name__ == "__main__":
    app = PayslipSplitterApp()
    app.mainloop()
