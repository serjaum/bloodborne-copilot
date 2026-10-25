"""A small, read-only, always-on-top Bloodborne companion panel."""

from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

from tools.bloodborne_save_reader.save_reader import inspect_save
from apps.overlay.snapshot import build_snapshot


COLORS = {
    "background": "#10131b",
    "panel": "#191e29",
    "panel_alt": "#202633",
    "accent": "#a83a47",
    "accent_hover": "#c24a57",
    "text": "#f1ece5",
    "muted": "#a7a9b1",
    "dim": "#727783",
    "border": "#343a48",
}


class CopilotOverlay:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.pinned = True
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.root.title("Bloodborne Copilot")
        self.root.geometry("430x438+45+75")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.96)
        except tk.TclError:
            pass
        self.root.configure(bg=COLORS["border"])
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        shell = tk.Frame(root, bg=COLORS["background"], bd=1, relief="solid")
        shell.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_header(shell)
        self._build_content(shell)

    def _build_header(self, parent: tk.Misc) -> None:
        header = tk.Frame(parent, bg=COLORS["panel"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="BLOODBORNE  /  COPILOT",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
            padx=14,
        )
        title.pack(side="left", fill="y")
        title.bind("<ButtonPress-1>", self._start_drag)
        title.bind("<B1-Motion>", self._drag)

        self.pin_button = self._button(
            header, "PINNED", self._toggle_pin, bg=COLORS["panel_alt"], width=8
        )
        self.pin_button.pack(side="right", padx=(4, 8), pady=9)
        close_button = self._button(
            header, "×", self.root.destroy, bg=COLORS["panel"], width=3
        )
        close_button.pack(side="right", padx=(0, 2), pady=7)

    def _build_content(self, parent: tk.Misc) -> None:
        content = tk.Frame(parent, bg=COLORS["background"], padx=15, pady=13)
        content.pack(fill="both", expand=True)

        self.character_label = tk.Label(
            content,
            text="No hunter loaded",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=("Segoe UI Semibold", 15),
            anchor="w",
        )
        self.character_label.pack(fill="x")

        self.stats_label = tk.Label(
            content,
            text="Load a userdata000X save snapshot",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=("Consolas", 9),
            anchor="w",
            justify="left",
            wraplength=350,
        )
        self.stats_label.pack(fill="x", pady=(7, 13))

        divider = tk.Frame(content, bg=COLORS["border"], height=1)
        divider.pack(fill="x", pady=(0, 11))

        self.health_label = self._metric(content, "HP")
        self.stamina_label = self._metric(content, "STAMINA")
        self.resources_label = self._metric(content, "ECHOES  /  INSIGHT")
        self.bosses_label = self._metric(content, "BOSS FLAGS")
        self.inventory_label = self._metric(content, "INVENTORY")

        self.status_label = tk.Label(
            content,
            text="No save loaded · this panel does not watch the game",
            bg=COLORS["background"],
            fg=COLORS["dim"],
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
            wraplength=350,
        )
        self.status_label.pack(fill="x", pady=(5, 10))

        actions = tk.Frame(content, bg=COLORS["background"])
        actions.pack(fill="x", side="bottom")
        load_button = self._button(
            actions, "LOAD SAVE SNAPSHOT", self._choose_save, bg=COLORS["accent"]
        )
        load_button.pack(side="left", fill="x", expand=True)
        load_button.bind("<Enter>", lambda _event: load_button.configure(bg=COLORS["accent_hover"]))
        load_button.bind("<Leave>", lambda _event: load_button.configure(bg=COLORS["accent"]))

    def _metric(self, parent: tk.Misc, title: str) -> tk.Label:
        row = tk.Frame(parent, bg=COLORS["background"])
        row.pack(fill="x", pady=3)
        tk.Label(
            row,
            text=title,
            bg=COLORS["background"],
            fg=COLORS["dim"],
            font=("Segoe UI", 8, "bold"),
            width=20,
            anchor="w",
        ).pack(side="left")
        value = tk.Label(
            row,
            text="Not available",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=220,
        )
        value.pack(side="left", fill="x", expand=True)
        return value

    @staticmethod
    def _button(
        parent: tk.Misc,
        text: str,
        command: Any,
        *,
        bg: str,
        width: int | None = None,
    ) -> tk.Button:
        options: dict[str, Any] = {
            "text": text,
            "command": command,
            "bg": bg,
            "fg": COLORS["text"],
            "activebackground": COLORS["accent_hover"],
            "activeforeground": COLORS["text"],
            "relief": "flat",
            "bd": 0,
            "cursor": "hand2",
            "font": ("Segoe UI", 8, "bold"),
            "padx": 10,
            "pady": 5,
        }
        if width is not None:
            options["width"] = width
        return tk.Button(parent, **options)

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        start_x, start_y, window_x, window_y = self.drag_origin
        x = window_x + event.x_root - start_x
        y = window_y + event.y_root - start_y
        self.root.geometry(f"+{x}+{y}")

    def _toggle_pin(self) -> None:
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned)
        self.pin_button.configure(text="PINNED" if self.pinned else "UNPINNED")

    def _choose_save(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a Bloodborne userdata save",
            filetypes=[("Bloodborne save", "userdata*")],
        )
        if path:
            self.load_save(Path(path))

    def load_save(self, path: Path) -> None:
        try:
            data = inspect_save(path)
            snapshot = build_snapshot(data)
        except (OSError, ValueError) as exc:
            self.status_label.configure(
                text=f"Could not read save: {exc}", fg=COLORS["accent_hover"]
            )
            return

        self.character_label.configure(text=snapshot["character"])
        self.stats_label.configure(text=snapshot["stats"])
        self.health_label.configure(text=snapshot["health"])
        self.stamina_label.configure(text=snapshot["stamina"])
        self.resources_label.configure(text=snapshot["resources"])
        self.bosses_label.configure(text=snapshot["boss_flags"])
        self.inventory_label.configure(text=snapshot["inventory"])
        self.status_label.configure(
            text=f"{snapshot['disclaimer']}  ·  {path.name}", fg=COLORS["muted"]
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bloodborne Copilot read-only overlay")
    parser.add_argument("--save", type=Path, help="Optionally load a userdata save on startup")
    args = parser.parse_args(argv)

    root = tk.Tk()
    app = CopilotOverlay(root)
    if args.save is not None:
        root.after(150, lambda: app.load_save(args.save))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
