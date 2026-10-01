"""
PDF Extractor Desktop App
A modern, premium Python desktop application for extracting text from PDF files.
Built with customtkinter and PyMuPDF.
"""

import customtkinter as ctk
from pypdf import PdfReader
import threading
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


# ─── App Configuration ────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "Kufferath Payslip"
APP_VERSION = "1.0.0"
ACCENT_COLOR = "#7C3AED"        # Violet-600
ACCENT_HOVER = "#6D28D9"        # Violet-700
BG_PRIMARY = "#0F0F1A"          # Deep navy-black
BG_SECONDARY = "#16162A"        # Slightly lighter
BG_CARD = "#1E1E35"             # Card background
TEXT_PRIMARY = "#F1F1FF"
TEXT_MUTED = "#8888AA"
SUCCESS_COLOR = "#10B981"
ERROR_COLOR = "#EF4444"
WARNING_COLOR = "#F59E0B"


# ─── PDF Service ──────────────────────────────────────────────────────────────

class PDFExtractorService:
    """Handles all PDF reading and text extraction logic."""

    @staticmethod
    def extract_text(pdf_path: str) -> dict:
        """
        Extract text from a PDF file, page by page.

        Returns a dict with:
          - pages: list of { page_num, text, word_count, char_count }
          - total_pages: int
          - total_words: int
          - total_chars: int
          - file_name: str
          - file_size_kb: float
          - metadata: dict
        """
        reader = PdfReader(pdf_path)
        pages = []
        total_words = 0
        total_chars = 0

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            words = len(text.split())
            chars = len(text)
            total_words += words
            total_chars += chars
            pages.append({
                "page_num": i + 1,
                "text": text,
                "word_count": words,
                "char_count": chars,
            })

        meta = reader.metadata or {}
        metadata = {
            "title": meta.get("/Title", ""),
            "author": meta.get("/Author", ""),
            "subject": meta.get("/Subject", ""),
            "creator": meta.get("/Creator", ""),
        }

        file_size_kb = os.path.getsize(pdf_path) / 1024

        return {
            "pages": pages,
            "total_pages": len(pages),
            "total_words": total_words,
            "total_chars": total_chars,
            "file_name": Path(pdf_path).name,
            "file_size_kb": file_size_kb,
            "metadata": metadata,
        }

    @staticmethod
    def export_to_txt(result: dict, output_path: str) -> None:
        """Write extracted text to a .txt file with page separators."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"PDF Extractor — {result['file_name']}\n")
            f.write("=" * 60 + "\n\n")
            for page in result["pages"]:
                f.write(f"--- Page {page['page_num']} ---\n")
                f.write(page["text"])
                f.write("\n\n")


# ─── UI Components ────────────────────────────────────────────────────────────

class StatCard(ctk.CTkFrame):
    """A small card showing a stat label and value."""

    def __init__(self, master, label: str, value: str = "—", **kwargs):
        super().__init__(
            master,
            fg_color=BG_CARD,
            corner_radius=12,
            **kwargs
        )
        self.label_widget = ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED
        )
        self.label_widget.pack(pady=(10, 2))

        self.value_widget = ctk.CTkLabel(
            self, text=value,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.value_widget.pack(pady=(0, 10))

    def update_value(self, value: str) -> None:
        self.value_widget.configure(text=value)


class StatusBar(ctk.CTkFrame):
    """Bottom status bar showing current app state."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG_SECONDARY,
            corner_radius=0,
            height=32,
            **kwargs
        )
        self._dot = ctk.CTkLabel(
            self, text="●", font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED
        )
        self._dot.pack(side="left", padx=(14, 4))

        self._msg = ctk.CTkLabel(
            self, text="Ready — open a PDF to begin",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED
        )
        self._msg.pack(side="left")

        # Version label on the right
        ctk.CTkLabel(
            self, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED
        ).pack(side="right", padx=14)

    def set(self, message: str, color: str = TEXT_MUTED) -> None:
        self._msg.configure(text=message, text_color=color)
        self._dot.configure(text_color=color)


# ─── Main Application Window ──────────────────────────────────────────────────

class PDFExtractorApp(ctk.CTk):
    """
    Main application window for the PDF Extractor.
    Provides a modern dark UI with drag-and-drop file selection,
    page-aware text display, stats, and export/copy actions.
    """

    def __init__(self):
        super().__init__()

        self._result: dict | None = None
        self._current_page_index: int = 0

        self._configure_window()
        self._build_ui()

    # ── Window Setup ──────────────────────────────────────────────────────────

    def _configure_window(self) -> None:
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(800, 560)
        self.configure(fg_color=BG_PRIMARY)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1100) // 2
        y = (self.winfo_screenheight() - 720) // 2
        self.geometry(f"1100x720+{x}+{y}")

    # ── UI Layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Assemble the full UI layout."""
        self._build_header()
        self._build_body()
        self._build_status_bar()

    def _build_header(self) -> None:
        """Top header with title, file info, and action buttons."""
        header = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=0, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)

        # App icon + title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            title_frame,
            text="⬡",
            font=ctk.CTkFont(size=22),
            text_color=ACCENT_COLOR
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_frame,
            text="PDF Extractor",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="Pro",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=ACCENT_COLOR
        ).pack(side="left", padx=(4, 0), pady=(4, 0))

        # Right-side action buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=20, pady=12)

        self._btn_copy = ctk.CTkButton(
            btn_frame, text="⎘  Copy All",
            width=110, height=38,
            fg_color=BG_CARD, hover_color="#2A2A48",
            text_color=TEXT_PRIMARY,
            corner_radius=10,
            command=self._on_copy
        )
        self._btn_copy.pack(side="left", padx=(0, 8))
        self._btn_copy.configure(state="disabled")

        self._btn_export = ctk.CTkButton(
            btn_frame, text="↓  Export .txt",
            width=120, height=38,
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
            text_color="white",
            corner_radius=10,
            command=self._on_export
        )
        self._btn_export.pack(side="left")
        self._btn_export.configure(state="disabled")

    def _build_body(self) -> None:
        """Main body: left sidebar + right content area."""
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_sidebar(body)
        self._build_content(body)

    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        """Left sidebar: file drop zone, stats, page navigator."""
        sidebar = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=0, width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        sidebar_inner = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_inner.pack(fill="both", expand=True, padx=16, pady=16)

        # Drop zone / file picker button
        self._drop_zone = ctk.CTkButton(
            sidebar_inner,
            text="📄\n\nClick to open PDF\n\nor drag & drop",
            height=140,
            fg_color=BG_CARD,
            hover_color="#252540",
            text_color=TEXT_MUTED,
            corner_radius=14,
            border_width=2,
            border_color="#2E2E50",
            font=ctk.CTkFont(size=12),
            command=self._on_open_file
        )
        self._drop_zone.pack(fill="x")

        # File name label
        self._file_label = ctk.CTkLabel(
            sidebar_inner, text="No file selected",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            wraplength=200
        )
        self._file_label.pack(pady=(10, 0))

        # Separator
        ctk.CTkFrame(sidebar_inner, fg_color="#2E2E50", height=1).pack(
            fill="x", pady=16
        )

        # Stats section
        ctk.CTkLabel(
            sidebar_inner, text="DOCUMENT STATS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        stats_grid = ctk.CTkFrame(sidebar_inner, fg_color="transparent")
        stats_grid.pack(fill="x", pady=(8, 0))

        self._stat_pages = StatCard(stats_grid, "Pages")
        self._stat_pages.pack(fill="x", pady=(0, 6))

        self._stat_words = StatCard(stats_grid, "Words")
        self._stat_words.pack(fill="x", pady=(0, 6))

        self._stat_size = StatCard(stats_grid, "File Size")
        self._stat_size.pack(fill="x")

        # Separator
        ctk.CTkFrame(sidebar_inner, fg_color="#2E2E50", height=1).pack(
            fill="x", pady=16
        )

        # Page Navigator
        ctk.CTkLabel(
            sidebar_inner, text="PAGE NAVIGATOR",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        nav_frame = ctk.CTkFrame(sidebar_inner, fg_color="transparent")
        nav_frame.pack(fill="x", pady=(8, 0))

        self._btn_prev = ctk.CTkButton(
            nav_frame, text="←", width=52, height=36,
            fg_color=BG_CARD, hover_color="#252540",
            text_color=TEXT_PRIMARY, corner_radius=8,
            command=self._on_prev_page, state="disabled"
        )
        self._btn_prev.pack(side="left")

        self._page_indicator = ctk.CTkLabel(
            nav_frame, text="— / —",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self._page_indicator.pack(side="left", expand=True)

        self._btn_next = ctk.CTkButton(
            nav_frame, text="→", width=52, height=36,
            fg_color=BG_CARD, hover_color="#252540",
            text_color=TEXT_PRIMARY, corner_radius=8,
            command=self._on_next_page, state="disabled"
        )
        self._btn_next.pack(side="right")

    def _build_content(self, parent: ctk.CTkFrame) -> None:
        """Right content area: search bar + extracted text display."""
        content = ctk.CTkFrame(parent, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Top bar: page title + search
        top_bar = ctk.CTkFrame(content, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 12))

        self._page_title = ctk.CTkLabel(
            top_bar, text="Extracted Content",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self._page_title.pack(side="left")

        # Search entry
        search_frame = ctk.CTkFrame(top_bar, fg_color=BG_CARD, corner_radius=10)
        search_frame.pack(side="right")

        ctk.CTkLabel(search_frame, text="🔍", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(10, 4), pady=6
        )
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        self._search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self._search_var,
            placeholder_text="Search text…",
            width=200, height=32,
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_PRIMARY
        )
        self._search_entry.pack(side="left", padx=(0, 10))

        # Text display area
        self._textbox = ctk.CTkTextbox(
            content,
            fg_color=BG_CARD,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=14,
            wrap="word",
            scrollbar_button_color="#2E2E50",
            scrollbar_button_hover_color=ACCENT_COLOR,
        )
        self._textbox.pack(fill="both", expand=True)

        self._show_placeholder()

    def _build_status_bar(self) -> None:
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")

    # ── Placeholder ───────────────────────────────────────────────────────────

    def _show_placeholder(self) -> None:
        """Display a friendly placeholder message in the textbox."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert(
            "1.0",
            "\n\n\n"
            "           No PDF loaded yet.\n\n"
            "           Click 'Click to open PDF' in the sidebar\n"
            "           to select a file and extract its content.\n\n\n"
            "           Supported: text-based PDFs (not scanned images)."
        )
        self._textbox.configure(state="disabled")

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _on_open_file(self) -> None:
        """Open file dialog and trigger extraction in a background thread."""
        path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return

        self._status.set("Extracting text…", WARNING_COLOR)
        self._drop_zone.configure(state="disabled")

        thread = threading.Thread(target=self._extract_worker, args=(path,), daemon=True)
        thread.start()

    def _extract_worker(self, path: str) -> None:
        """Run PDF extraction in a background thread, then update UI."""
        try:
            result = PDFExtractorService.extract_text(path)
            self.after(0, self._on_extraction_success, result)
        except Exception as exc:
            self.after(0, self._on_extraction_error, str(exc))

    def _on_extraction_success(self, result: dict) -> None:
        self._result = result
        self._current_page_index = 0

        # Update stats
        self._stat_pages.update_value(str(result["total_pages"]))
        self._stat_words.update_value(f"{result['total_words']:,}")
        self._stat_size.update_value(f"{result['file_size_kb']:.1f} KB")

        # Update file label
        self._file_label.configure(text=result["file_name"], text_color=TEXT_PRIMARY)

        # Enable buttons
        self._btn_copy.configure(state="normal")
        self._btn_export.configure(state="normal")
        self._btn_prev.configure(state="normal")
        self._btn_next.configure(state="normal")

        # Show content
        self._show_page(0)
        self._drop_zone.configure(state="normal", text="📄\n\nOpen another PDF\n\nor drag & drop")
        self._status.set(
            f"✓ Extracted {result['total_pages']} pages · {result['total_words']:,} words",
            SUCCESS_COLOR
        )

    def _on_extraction_error(self, error: str) -> None:
        self._status.set(f"✗ Error: {error}", ERROR_COLOR)
        self._drop_zone.configure(state="normal")
        messagebox.showerror("Extraction Failed", f"Could not extract PDF:\n\n{error}")

    def _show_page(self, index: int) -> None:
        """Render extracted text for a specific page index."""
        if not self._result:
            return

        pages = self._result["pages"]
        page = pages[index]

        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")

        header = f"PAGE {page['page_num']}  ·  {page['word_count']:,} words  ·  {page['char_count']:,} chars\n"
        self._textbox.insert("end", header)
        self._textbox.insert("end", "─" * 60 + "\n\n")
        self._textbox.insert("end", page["text"] if page["text"].strip() else "(No extractable text on this page)")
        self._textbox.configure(state="disabled")

        total = self._result["total_pages"]
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

    def _on_copy(self) -> None:
        """Copy all extracted text from all pages to the clipboard."""
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
        """Prompt for save location and export extracted text to .txt."""
        if not self._result:
            return
        stem = Path(self._result["file_name"]).stem
        default_name = f"{stem}_extracted.txt"
        output_path = filedialog.asksaveasfilename(
            title="Save extracted text",
            defaultextension=".txt",
            initialfile=default_name,
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

    def _on_search_change(self, *_) -> None:
        """Highlight search matches in the current page's text (basic implementation)."""
        # Reserved for future enhancement — live search across pages
        pass


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = PDFExtractorApp()
    app.mainloop()
