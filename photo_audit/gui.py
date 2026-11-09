from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import all_photo_paths, audit, discover_photos, find_content_duplicates, read_ids, write_reports


class AuditApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Photo Audit Tool")
        self.geometry("760x430")
        self.minsize(650, 380)
        self.input_path = tk.StringVar()
        self.photos_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(Path.cwd() / "reports"))
        self.id_column = tk.StringVar(value="ID")
        self.prefix = tk.BooleanVar(value=False)
        self.hash_files = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Ready — processing stays on this computer.")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Photo Audit Tool", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))
        self._path_row(frame, 1, "CSV / Excel", self.input_path, self._choose_input)
        self._path_row(frame, 2, "Photo folder", self.photos_path, self._choose_photos)
        self._path_row(frame, 3, "Report folder", self.output_path, self._choose_output)
        ttk.Label(frame, text="ID column").grid(row=4, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.id_column).grid(row=4, column=1, sticky="ew", pady=8)
        ttk.Checkbutton(frame, text="Match filename prefix before underscore", variable=self.prefix).grid(row=5, column=1, sticky="w")
        ttk.Checkbutton(frame, text="Detect byte-identical files (SHA-256)", variable=self.hash_files).grid(row=6, column=1, sticky="w")
        self.run_button = ttk.Button(frame, text="Run audit", command=self._start)
        self.run_button.grid(row=7, column=1, sticky="w", pady=20)
        ttk.Separator(frame).grid(row=8, column=0, columnspan=3, sticky="ew")
        ttk.Label(frame, textvariable=self.status, wraplength=680).grid(row=9, column=0, columnspan=3, sticky="w", pady=14)
        frame.columnconfigure(1, weight=1)

    def _path_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 12))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=8)
        ttk.Button(parent, text="Browse…", command=command).grid(row=row, column=2, padx=(10, 0))

    def _choose_input(self) -> None:
        value = filedialog.askopenfilename(filetypes=[("Data files", "*.csv *.xlsx *.xlsm")])
        if value:
            self.input_path.set(value)

    def _choose_photos(self) -> None:
        if value := filedialog.askdirectory():
            self.photos_path.set(value)

    def _choose_output(self) -> None:
        if value := filedialog.askdirectory():
            self.output_path.set(value)

    def _start(self) -> None:
        self.run_button.configure(state="disabled")
        self.status.set("Scanning…")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            source, folder, output = Path(self.input_path.get()), Path(self.photos_path.get()), Path(self.output_path.get())
            ids = read_ids(source, self.id_column.get())
            photos = discover_photos(folder, self.prefix.get())
            rows, extras = audit(ids, photos)
            groups = find_content_duplicates(all_photo_paths(photos)) if self.hash_files.get() else []
            summary = write_reports(rows, extras, output, groups)
            self.after(0, self._done, summary, output)
        except Exception as exc:
            self.after(0, self._failed, str(exc))

    def _done(self, summary: dict[str, int], output: Path) -> None:
        self.run_button.configure(state="normal")
        self.status.set(" | ".join(f"{key}={value}" for key, value in summary.items()))
        messagebox.showinfo("Audit complete", f"Reports saved to:\n{output.resolve()}")

    def _failed(self, message: str) -> None:
        self.run_button.configure(state="normal")
        self.status.set(f"Error: {message}")
        messagebox.showerror("Audit failed", message)


def launch() -> None:
    AuditApp().mainloop()
