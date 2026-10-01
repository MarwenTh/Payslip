"""
PDF Extractor Desktop App
A modern, premium Python desktop application for extracting text from PDF files.
Supports both text-based PDFs and image-based (scanned) PDFs via OCR.
Built with customtkinter, pypdf, pdfplumber, and pytesseract.
"""

import customtkinter as ctk
import threading
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# ─── Optional OCR imports (gracefully handled if missing) ─────────────────────
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True

    # Auto-detect Tesseract on Windows (common install paths)
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
    """
    Locate the Poppler 'bin' directory.
    Checks:
      1. A 'poppler' folder bundled alongside this script (portable)
      2. Common system install paths on Windows
    Returns the bin path string, or None if not found.
    """
    script_dir = Path(__file__).parent.resolve()

    # 1. Bundled portable poppler (any version subfolder)
    for candidate in script_dir.glob("poppler/**/bin"):
        if (candidate / "pdftoppm.exe").exists():
            return str(candidate)

    # 2. System-wide locations
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

from pypdf import PdfReader


# ─── App Configuration ────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE  = "PDF Extractor"
APP_VERSION = "1.1.0"
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
OCR_COLOR     = "#06B6D4"   # Cyan — OCR mode indicator


# ─── PDF Extractor Service ────────────────────────────────────────────────────

class PDFExtractorService:
    """
    Handles PDF text extraction with two strategies:
      1. Native text extraction (pypdf / pdfplumber) — fast, lossless
      2. OCR extraction (Tesseract) — for scanned / image-based PDFs
    """

    @staticmethod
    def extract_native(pdf_path: str) -> dict:
        """
        Extract text using pdfplumber (preferred) or pypdf as fallback.
        Returns structured page data.
        """
        pages = []

        if PDFPLUMBER_AVAILABLE:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages.append(PDFExtractorService._make_page(i + 1, text))
        else:
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(PDFExtractorService._make_page(i + 1, text))

        return PDFExtractorService._build_result(pdf_path, pages, mode="native")

    @staticmethod
    def extract_ocr(pdf_path: str, progress_callback=None) -> dict:
        """
        Convert each PDF page to an image and run Tesseract OCR on it.
        Calls progress_callback(current_page, total_pages) if provided.
        """
        if not OCR_AVAILABLE:
            raise RuntimeError(
                "OCR dependencies are not installed.\n\n"
                "Please install:\n"
                "  1. Tesseract OCR:  https://github.com/UB-Mannheim/tesseract/wiki\n"
                "  2. Python packages: pip install pytesseract pdf2image"
            )

        # Resolve poppler path (bundled or system)
        poppler = POPPLER_PATH
        if poppler is None:
            raise RuntimeError(
                "Poppler not found.\n\n"
                "Please place the Poppler 'bin' folder inside a 'poppler/' "
                "subfolder next to app.py, or install it system-wide.\n\n"
                "Download: https://github.com/oschwartz10612/poppler-windows/releases"
            )

        # Convert PDF pages to PIL images
        images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler)
        total = len(images)
        pages = []

        for i, img in enumerate(images):
            if progress_callback:
                progress_callback(i + 1, total)
            text = pytesseract.image_to_string(img, lang="eng+fra+ara")
            pages.append(PDFExtractorService._make_page(i + 1, text))

        return PDFExtractorService._build_result(pdf_path, pages, mode="ocr")

    @staticmethod
    def has_text(result: dict) -> bool:
        """Return True if any page has extractable text."""
        return result["total_words"] > 0

    @staticmethod
    def export_to_txt(result: dict, output_path: str) -> None:
        """Write extracted text to a .txt file with page separators."""
        mode_label = "OCR" if result.get("mode") == "ocr" else "Native"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"PDF Extractor [{mode_label}] — {result['file_name']}\n")
            f.write("=" * 60 + "\n\n")
            for page in result["pages"]:
                f.write(f"--- Page {page['page_num']} ---\n")
                f.write(page["text"])
                f.write("\n\n")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_page(page_num: int, text: str) -> dict:
        return {
            "page_num": page_num,
            "text": text,
            "word_count": len(text.split()),
            "char_count": len(text),
        }

    @staticmethod
    def _build_result(pdf_path: str, pages: list, mode: str) -> dict:
        total_words = sum(p["word_count"] for p in pages)
        total_chars = sum(p["char_count"] for p in pages)
        file_size_kb = os.path.getsize(pdf_path) / 1024
        return {
            "pages": pages,
            "total_pages": len(pages),
            "total_words": total_words,
            "total_chars": total_chars,
            "file_name": Path(pdf_path).name,
            "file_size_kb": file_size_kb,
            "mode": mode,
        }


# ─── UI Components ────────────────────────────────────────────────────────────

class StatCard(ctk.CTkFrame):
    """Small card displaying a labelled numeric stat."""

    def __init__(self, master, label: str, value: str = "—", **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=12, **kwargs)
        ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
        ).pack(pady=(10, 2))
        self._val = ctk.CTkLabel(
            self, text=value,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self._val.pack(pady=(0, 10))

    def update_value(self, value: str, color: str = TEXT_PRIMARY) -> None:
        self._val.configure(text=value, text_color=color)


class StatusBar(ctk.CTkFrame):
    """Bottom status bar."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master, fg_color=BG_SECONDARY, corner_radius=0, height=32, **kwargs
        )
        self._dot = ctk.CTkLabel(self, text="●", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        self._dot.pack(side="left", padx=(14, 4))
        self._msg = ctk.CTkLabel(
            self, text="Ready — open a PDF to begin",
            font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
        )
        self._msg.pack(side="left")
        ctk.CTkLabel(
            self, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=10), text_color=TEXT_MUTED
        ).pack(side="right", padx=14)

    def set(self, message: str, color: str = TEXT_MUTED) -> None:
        self._msg.configure(text=message, text_color=color)
        self._dot.configure(text_color=color)


class OCRBanner(ctk.CTkFrame):
    """
    Banner shown when no text is found in a PDF.
    Prompts the user to enable OCR mode.
    """

    def __init__(self, master, on_ocr_click, **kwargs):
        super().__init__(master, fg_color="#0C2233", corner_radius=12, **kwargs)
        ctk.CTkLabel(
            self,
            text="🔍  No text layer found in this PDF",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OCR_COLOR
        ).pack(pady=(14, 4), padx=20)
        ctk.CTkLabel(
            self,
            text="This appears to be a scanned / image-based PDF.\nUse OCR to extract text from the page images.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            justify="center"
        ).pack(pady=(0, 10))
        ctk.CTkButton(
            self,
            text="✦  Run OCR on this PDF",
            fg_color=OCR_COLOR, hover_color="#0891B2",
            text_color="white",
            width=200, height=38, corner_radius=10,
            command=on_ocr_click
        ).pack(pady=(0, 14))


# ─── Main Application Window ──────────────────────────────────────────────────

class PDFExtractorApp(ctk.CTk):
    """
    Main application window for the PDF Extractor.
    Supports native text extraction and OCR for image-based PDFs.
    """

    def __init__(self):
        super().__init__()
        self._result: dict | None = None
        self._current_page_index: int = 0
        self._current_pdf_path: str = ""
        self._ocr_banner: OCRBanner | None = None
        self._ocr_progress_bar: ctk.CTkProgressBar | None = None

        self._configure_window()
        self._build_ui()

    # ── Window Setup ──────────────────────────────────────────────────────────

    def _configure_window(self) -> None:
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(820, 560)
        self.configure(fg_color=BG_PRIMARY)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1100) // 2
        y = (self.winfo_screenheight() - 720) // 2
        self.geometry(f"1100x720+{x}+{y}")

    # ── Full UI Layout ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._build_header()
        self._build_body()
        self._build_status_bar()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=0, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(title_frame, text="⬡", font=ctk.CTkFont(size=22), text_color=ACCENT_COLOR).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(title_frame, text="PDF Extractor", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(title_frame, text="Pro", font=ctk.CTkFont(size=10, weight="bold"), text_color=ACCENT_COLOR).pack(side="left", padx=(4, 0), pady=(4, 0))

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=20, pady=12)

        self._btn_copy = ctk.CTkButton(
            btn_frame, text="⎘  Copy All", width=110, height=38,
            fg_color=BG_CARD, hover_color="#2A2A48", text_color=TEXT_PRIMARY,
            corner_radius=10, state="disabled", command=self._on_copy
        )
        self._btn_copy.pack(side="left", padx=(0, 8))

        self._btn_export = ctk.CTkButton(
            btn_frame, text="↓  Export .txt", width=120, height=38,
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color="white",
            corner_radius=10, state="disabled", command=self._on_export
        )
        self._btn_export.pack(side="left")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_content(body)

    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        sidebar = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=0, width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        inner = ctk.CTkFrame(sidebar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        # File picker button
        self._drop_zone = ctk.CTkButton(
            inner, text="📄\n\nClick to open PDF\n\nor drag & drop",
            height=140, fg_color=BG_CARD, hover_color="#252540",
            text_color=TEXT_MUTED, corner_radius=14,
            border_width=2, border_color="#2E2E50",
            font=ctk.CTkFont(size=12), command=self._on_open_file
        )
        self._drop_zone.pack(fill="x")

        self._file_label = ctk.CTkLabel(
            inner, text="No file selected",
            font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, wraplength=200
        )
        self._file_label.pack(pady=(10, 0))

        # Mode badge
        self._mode_badge = ctk.CTkLabel(
            inner, text="", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED
        )
        self._mode_badge.pack(pady=(2, 0))

        ctk.CTkFrame(inner, fg_color="#2E2E50", height=1).pack(fill="x", pady=14)

        # Stats
        ctk.CTkLabel(inner, text="DOCUMENT STATS", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        stats_grid = ctk.CTkFrame(inner, fg_color="transparent")
        stats_grid.pack(fill="x", pady=(8, 0))

        self._stat_pages = StatCard(stats_grid, "Pages")
        self._stat_pages.pack(fill="x", pady=(0, 6))
        self._stat_words = StatCard(stats_grid, "Words")
        self._stat_words.pack(fill="x", pady=(0, 6))
        self._stat_size = StatCard(stats_grid, "File Size")
        self._stat_size.pack(fill="x")

        ctk.CTkFrame(inner, fg_color="#2E2E50", height=1).pack(fill="x", pady=14)

        # Page Navigator
        ctk.CTkLabel(inner, text="PAGE NAVIGATOR", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        nav = ctk.CTkFrame(inner, fg_color="transparent")
        nav.pack(fill="x", pady=(8, 0))

        self._btn_prev = ctk.CTkButton(nav, text="←", width=52, height=36, fg_color=BG_CARD, hover_color="#252540", text_color=TEXT_PRIMARY, corner_radius=8, command=self._on_prev_page, state="disabled")
        self._btn_prev.pack(side="left")
        self._page_indicator = ctk.CTkLabel(nav, text="— / —", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_PRIMARY)
        self._page_indicator.pack(side="left", expand=True)
        self._btn_next = ctk.CTkButton(nav, text="→", width=52, height=36, fg_color=BG_CARD, hover_color="#252540", text_color=TEXT_PRIMARY, corner_radius=8, command=self._on_next_page, state="disabled")
        self._btn_next.pack(side="right")

    def _build_content(self, parent: ctk.CTkFrame) -> None:
        self._content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._content_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        top_bar = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 12))

        self._page_title = ctk.CTkLabel(top_bar, text="Extracted Content", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self._page_title.pack(side="left")

        self._textbox = ctk.CTkTextbox(
            self._content_frame,
            fg_color=BG_CARD, text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=14, wrap="word",
            scrollbar_button_color="#2E2E50",
            scrollbar_button_hover_color=ACCENT_COLOR,
        )
        self._textbox.pack(fill="both", expand=True)
        self._show_placeholder()

    def _build_status_bar(self) -> None:
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")

    # ── Placeholder / OCR Banner ──────────────────────────────────────────────

    def _show_placeholder(self) -> None:
        self._hide_ocr_banner()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert("1.0",
            "\n\n\n"
            "           No PDF loaded yet.\n\n"
            "           Click 'Click to open PDF' in the sidebar\n"
            "           to select a file and extract its content.\n\n\n"
            "           Supports both text-based and scanned PDFs (via OCR)."
        )
        self._textbox.configure(state="disabled")

    def _show_ocr_banner(self) -> None:
        """Display the OCR prompt banner above the (empty) textbox."""
        self._hide_ocr_banner()
        self._ocr_banner = OCRBanner(self._content_frame, on_ocr_click=self._on_ocr_requested)
        # Insert banner between top_bar and textbox
        self._ocr_banner.pack(fill="x", pady=(0, 10), before=self._textbox)

    def _hide_ocr_banner(self) -> None:
        if self._ocr_banner:
            self._ocr_banner.destroy()
            self._ocr_banner = None

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _on_open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return
        self._current_pdf_path = path
        self._status.set("Extracting text…", WARNING_COLOR)
        self._drop_zone.configure(state="disabled")
        thread = threading.Thread(target=self._extract_worker_native, args=(path,), daemon=True)
        thread.start()

    def _extract_worker_native(self, path: str) -> None:
        try:
            result = PDFExtractorService.extract_native(path)
            self.after(0, self._on_extraction_done, result, path)
        except Exception as exc:
            self.after(0, self._on_extraction_error, str(exc))

    def _on_extraction_done(self, result: dict, path: str) -> None:
        self._result = result
        self._current_page_index = 0
        self._current_pdf_path = path

        self._stat_pages.update_value(str(result["total_pages"]))
        self._stat_words.update_value(f"{result['total_words']:,}")
        self._stat_size.update_value(f"{result['file_size_kb']:.1f} KB")
        self._file_label.configure(text=result["file_name"], text_color=TEXT_PRIMARY)

        self._btn_copy.configure(state="normal")
        self._btn_export.configure(state="normal")
        self._btn_prev.configure(state="normal")
        self._btn_next.configure(state="normal")
        self._drop_zone.configure(state="normal", text="📄\n\nOpen another PDF\n\nor drag & drop")

        # Detect image-based PDF
        if not PDFExtractorService.has_text(result):
            self._mode_badge.configure(text="⚠ Image-based PDF", text_color=WARNING_COLOR)
            self._textbox.configure(state="normal")
            self._textbox.delete("1.0", "end")
            self._textbox.configure(state="disabled")
            self._page_title.configure(text=result["file_name"])
            self._page_indicator.configure(text=f"1 / {result['total_pages']}")
            self._show_ocr_banner()
            self._status.set("⚠ No text found — try OCR mode", WARNING_COLOR)
        else:
            self._hide_ocr_banner()
            mode_label = "OCR" if result["mode"] == "ocr" else "Native"
            self._mode_badge.configure(
                text=f"✓ {mode_label} mode",
                text_color=OCR_COLOR if result["mode"] == "ocr" else SUCCESS_COLOR
            )
            self._show_page(0)
            self._status.set(
                f"✓ Extracted {result['total_pages']} pages · {result['total_words']:,} words",
                SUCCESS_COLOR
            )

    def _on_extraction_error(self, error: str) -> None:
        self._status.set(f"✗ Error: {error}", ERROR_COLOR)
        self._drop_zone.configure(state="normal")
        messagebox.showerror("Extraction Failed", f"Could not extract PDF:\n\n{error}")

    # ── OCR Flow ──────────────────────────────────────────────────────────────

    def _on_ocr_requested(self) -> None:
        """User clicked 'Run OCR' — kick off OCR extraction in a thread."""
        if not self._current_pdf_path:
            return

        # Replace banner with a progress bar
        self._hide_ocr_banner()
        self._ocr_progress_bar = ctk.CTkProgressBar(
            self._content_frame,
            orientation="horizontal",
            mode="determinate",
            fg_color=BG_CARD,
            progress_color=OCR_COLOR,
            height=10,
            corner_radius=5,
        )
        self._ocr_progress_bar.set(0)
        self._ocr_progress_bar.pack(fill="x", pady=(0, 10), before=self._textbox)

        self._status.set("⟳ Running OCR… this may take a moment", OCR_COLOR)

        thread = threading.Thread(
            target=self._ocr_worker,
            args=(self._current_pdf_path,),
            daemon=True
        )
        thread.start()

    def _ocr_worker(self, path: str) -> None:
        try:
            def on_progress(current, total):
                progress = current / total
                self.after(0, self._update_ocr_progress, progress, current, total)

            result = PDFExtractorService.extract_ocr(path, progress_callback=on_progress)
            self.after(0, self._on_ocr_done, result)
        except Exception as exc:
            self.after(0, self._on_ocr_error, str(exc))

    def _update_ocr_progress(self, value: float, current: int, total: int) -> None:
        if self._ocr_progress_bar:
            self._ocr_progress_bar.set(value)
        self._status.set(f"⟳ OCR: processing page {current}/{total}…", OCR_COLOR)

    def _on_ocr_done(self, result: dict) -> None:
        if self._ocr_progress_bar:
            self._ocr_progress_bar.destroy()
            self._ocr_progress_bar = None

        self._result = result
        self._current_page_index = 0
        self._stat_words.update_value(f"{result['total_words']:,}", OCR_COLOR)
        self._mode_badge.configure(text="✦ OCR mode", text_color=OCR_COLOR)
        self._show_page(0)
        self._status.set(
            f"✦ OCR complete — {result['total_pages']} pages · {result['total_words']:,} words",
            OCR_COLOR
        )

    def _on_ocr_error(self, error: str) -> None:
        if self._ocr_progress_bar:
            self._ocr_progress_bar.destroy()
            self._ocr_progress_bar = None
        self._status.set(f"✗ OCR failed: {error}", ERROR_COLOR)
        messagebox.showerror(
            "OCR Failed",
            f"{error}\n\n"
            "Make sure Tesseract OCR is installed:\n"
            "  https://github.com/UB-Mannheim/tesseract/wiki\n\n"
            "Also install Python packages:\n"
            "  pip install pytesseract pdf2image"
        )

    # ── Page Navigation ───────────────────────────────────────────────────────

    def _show_page(self, index: int) -> None:
        if not self._result:
            return
        pages = self._result["pages"]
        page = pages[index]
        total = self._result["total_pages"]
        is_ocr = self._result.get("mode") == "ocr"

        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")

        mode_tag = "  [OCR]" if is_ocr else ""
        header = (
            f"PAGE {page['page_num']}{mode_tag}  ·  "
            f"{page['word_count']:,} words  ·  {page['char_count']:,} chars\n"
        )
        self._textbox.insert("end", header)
        self._textbox.insert("end", "─" * 60 + "\n\n")
        self._textbox.insert(
            "end",
            page["text"] if page["text"].strip()
            else "(No extractable text on this page)"
        )
        self._textbox.configure(state="disabled")

        self._page_indicator.configure(text=f"{index + 1} / {total}")
        self._page_title.configure(
            text=f"Page {index + 1} of {total}  —  {self._result['file_name']}"
        )
        self._btn_prev.configure(state="disabled" if index == 0 else "normal")
        self._btn_next.configure(state="disabled" if index == total - 1 else "normal")

    def _on_prev_page(self) -> None:
        if self._current_page_index > 0:
            self._current_page_index -= 1
            self._show_page(self._current_page_index)

    def _on_next_page(self) -> None:
        if self._result and self._current_page_index < self._result["total_pages"] - 1:
            self._current_page_index += 1
            self._show_page(self._current_page_index)

    # ── Copy / Export ─────────────────────────────────────────────────────────

    def _on_copy(self) -> None:
        if not self._result:
            return
        all_text = "\n\n".join(
            f"--- Page {p['page_num']} ---\n{p['text']}"
            for p in self._result["pages"]
        )
        self.clipboard_clear()
        self.clipboard_append(all_text)
        self._status.set("✓ All text copied to clipboard!", SUCCESS_COLOR)

    def _on_export(self) -> None:
        if not self._result:
            return
        stem = Path(self._result["file_name"]).stem
        output_path = filedialog.asksaveasfilename(
            title="Save extracted text",
            defaultextension=".txt",
            initialfile=f"{stem}_extracted.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not output_path:
            return
        try:
            PDFExtractorService.export_to_txt(self._result, output_path)
            self._status.set(f"✓ Exported to {Path(output_path).name}", SUCCESS_COLOR)
        except Exception as exc:
            self._status.set(f"✗ Export failed: {exc}", ERROR_COLOR)
            messagebox.showerror("Export Failed", str(exc))


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = PDFExtractorApp()
    app.mainloop()
