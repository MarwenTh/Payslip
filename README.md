# 📄 PDF Extractor

A modern, premium Python desktop application for extracting text from PDF files.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![UI](https://img.shields.io/badge/UI-customtkinter-blueviolet)

---

## ✨ Features

- 📂 **File Picker** — Select any PDF via native file dialog
- 📖 **Page Navigator** — Browse extracted text page by page
- 📊 **Document Stats** — Total pages, word count, and file size
- ⎘ **Copy All** — Copies all extracted text to clipboard
- 💾 **Export .txt** — Save extracted content as a `.txt` file with page separators
- 🔄 **Non-blocking** — Extraction runs in a background thread; UI stays responsive

---

## 🛠 Tech Stack

| Layer | Library |
|---|---|
| UI Framework | [customtkinter](https://github.com/TomSchimansky/CustomTkinter) |
| PDF Engine | [pypdf](https://github.com/py-pdf/pypdf) |
| Language | Python 3.10+ |

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/MarwenTh/Payslip.git
cd Payslip
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python app.py
```

---

## 📁 Project Structure

```
payslip/
├── app.py            # Main application entry point
├── requirements.txt  # Python dependencies
├── .gitignore
└── README.md
```

---

## 📝 License

MIT © [MarwenTh](https://github.com/MarwenTh)
