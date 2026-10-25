"""Two-mode, read-only Bloodborne Copilot desktop app."""

from __future__ import annotations

import argparse
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from apps.overlay.chat_client import (
    QUICK_PROMPTS,
    OpenAICompatibleClient,
    ProviderSettings,
    build_system_prompt,
)
from apps.overlay.snapshot import build_snapshot
from apps.overlay.window_modes import WINDOW_MODES
from tools.bloodborne_save_reader.save_reader import inspect_save

COLORS = {
    "background": "#10131b", "panel": "#191e29", "panel_alt": "#202633",
    "accent": "#a83a47", "accent_hover": "#c24a57", "text": "#f1ece5",
    "muted": "#a7a9b1", "dim": "#727783", "border": "#343a48",
    "user": "#f0b6a9", "assistant": "#d8dce5", "error": "#ff8f8f",
}
QUICK_LABELS = {"Build": "BUILD", "Boss": "BOSS", "Next step": "NEXT"}


class CopilotOverlay:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.mode = "compact"
        self.pinned = True
        self.running = True
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.settings = ProviderSettings.from_environment()
        self.snapshot: dict[str, str] | None = None
        self.snapshot_filename = ""
        self.history: list[dict[str, str]] = []
        self.busy = False
        self.result_queue: queue.Queue[tuple[str | None, str | None]] = queue.Queue()
        self.model_result_queue: queue.Queue[tuple[list[str] | None, str | None]] = queue.Queue()
        self.model_lookup_ui: dict[str, Any] | None = None
        self.chat_widgets: dict[str, dict[str, Any]] = {}
        self.snapshot_labels: dict[str, tk.Label] = {}
        self.mode_frames: dict[str, tk.Frame] = {}

        self.root.title("Bloodborne Copilot")
        self.root.configure(bg=COLORS["background"])
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._build_compact_view()
        self._build_full_view()
        self.show_compact()
        self.root.after(120, self._poll_results)

    def _build_compact_view(self) -> None:
        frame = tk.Frame(self.root, bg=COLORS["background"], bd=1, relief="solid")
        self.mode_frames["compact"] = frame
        header = tk.Frame(frame, bg=COLORS["panel"], height=46)
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(
            header, text="HUNTER  /  COPILOT", bg=COLORS["panel"], fg=COLORS["text"],
            font=("Segoe UI", 10, "bold"), padx=12,
        )
        title.pack(side="left", fill="y")
        self._bind_drag(title)
        self._button(header, "×", self.close, bg=COLORS["panel"], width=3).pack(
            side="right", padx=(0, 5), pady=7
        )
        self._button(header, "SET", self.open_settings, bg=COLORS["panel_alt"], width=4).pack(
            side="right", padx=3, pady=7
        )
        self.pin_button = self._button(
            header, "PINNED", self._toggle_pin, bg=COLORS["panel_alt"], width=7
        )
        self.pin_button.pack(side="right", padx=3, pady=7)
        self._button(header, "FULL", self.show_full, bg=COLORS["accent"], width=5).pack(
            side="right", padx=4, pady=7
        )

        profile = tk.Frame(frame, bg=COLORS["panel"], padx=12, pady=8)
        profile.pack(fill="x", padx=8, pady=(8, 4))
        self.compact_character = tk.Label(
            profile, text="No hunter loaded", bg=COLORS["panel"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 12), anchor="w",
        )
        self.compact_character.pack(fill="x")
        self.compact_stats = tk.Label(
            profile, text="Load a save snapshot for build context", bg=COLORS["panel"],
            fg=COLORS["muted"], font=("Consolas", 8), anchor="w", wraplength=390,
            justify="left",
        )
        self.compact_stats.pack(fill="x", pady=(4, 0))
        self.compact_provider = tk.Label(
            profile, text=self._provider_status(), bg=COLORS["panel"], fg=COLORS["dim"],
            font=("Segoe UI", 8), anchor="w",
        )
        self.compact_provider.pack(fill="x", pady=(4, 0))
        self._build_chat_panel(frame, "compact")

    def _build_full_view(self) -> None:
        frame = tk.Frame(self.root, bg=COLORS["background"], padx=12, pady=10)
        self.mode_frames["full"] = frame
        toolbar = tk.Frame(frame, bg=COLORS["background"], height=44)
        toolbar.pack(fill="x", pady=(0, 8))
        toolbar.pack_propagate(False)
        tk.Label(
            toolbar, text="BLOODBORNE COPILOT  ·  HUNTER DESK", bg=COLORS["background"],
            fg=COLORS["text"], font=("Segoe UI", 12, "bold"), anchor="w",
        ).pack(side="left", fill="y", padx=(4, 12))
        for text, command, color in (
            ("LOAD SAVE", self._choose_save, COLORS["panel_alt"]),
            ("SETTINGS", self.open_settings, COLORS["panel_alt"]),
            ("COMPACT", self.show_compact, COLORS["accent"]),
        ):
            self._button(toolbar, text, command, bg=color).pack(side="right", padx=4, pady=5)

        body = tk.Frame(frame, bg=COLORS["background"])
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, minsize=300, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        sidebar = tk.Frame(body, bg=COLORS["panel"], padx=14, pady=14)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(
            sidebar, text="HUNTER SNAPSHOT", bg=COLORS["panel"],
            fg=COLORS["accent_hover"], font=("Segoe UI", 9, "bold"), anchor="w",
        ).pack(fill="x", pady=(0, 10))
        self._snapshot_value(sidebar, "character", "No hunter loaded", large=True)
        self._snapshot_value(sidebar, "stats", "Stats unavailable")
        self._snapshot_value(sidebar, "health", "Not available", title="HP")
        self._snapshot_value(sidebar, "stamina", "Not available", title="STAMINA")
        self._snapshot_value(sidebar, "resources", "Not available", title="ECHOES / INSIGHT")
        self._snapshot_value(sidebar, "boss_flags", "Not available", title="BOSS FLAGS · EXPERIMENTAL")
        self._snapshot_value(sidebar, "inventory", "Not available", title="INVENTORY CANDIDATES")
        tk.Frame(sidebar, bg=COLORS["border"], height=1).pack(fill="x", pady=12)
        tk.Label(
            sidebar,
            text=("Use chat for build ideas, boss preparation, mechanics, or route questions. "
                  "Tell Copilot your current area; the save does not provide live location."),
            bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9),
            justify="left", wraplength=260, anchor="w",
        ).pack(fill="x")
        self.full_snapshot_status = tk.Label(
            sidebar, text="No save loaded", bg=COLORS["panel"], fg=COLORS["dim"],
            font=("Segoe UI", 8), justify="left", wraplength=260, anchor="w",
        )
        self.full_snapshot_status.pack(fill="x", side="bottom", pady=(12, 0))
        chat_container = tk.Frame(body, bg=COLORS["panel"], padx=12, pady=10)
        chat_container.grid(row=0, column=1, sticky="nsew")
        self._build_chat_panel(chat_container, "full")

    def _snapshot_value(
        self, parent: tk.Misc, key: str, initial: str, *,
        title: str | None = None, large: bool = False,
    ) -> None:
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(fill="x", pady=(0, 7))
        if title:
            tk.Label(
                row, text=title, bg=COLORS["panel"], fg=COLORS["dim"],
                font=("Segoe UI", 8, "bold"), anchor="w",
            ).pack(fill="x")
        label = tk.Label(
            row, text=initial, bg=COLORS["panel"],
            fg=COLORS["text"] if large else COLORS["muted"],
            font=("Segoe UI Semibold", 13) if large else ("Segoe UI", 9),
            justify="left", anchor="w", wraplength=265,
        )
        label.pack(fill="x")
        self.snapshot_labels[key] = label

    def _build_chat_panel(self, parent: tk.Misc, mode: str) -> None:
        panel_bg = COLORS["panel"] if mode == "full" else COLORS["background"]
        panel = tk.Frame(parent, bg=panel_bg)
        panel.pack(fill="both", expand=True, padx=8 if mode == "compact" else 0,
                   pady=(2, 8) if mode == "compact" else 0)
        heading = tk.Frame(panel, bg=panel_bg)
        heading.pack(fill="x", pady=(0, 5))
        tk.Label(
            heading, text="COPILOT CHAT", bg=panel_bg, fg=COLORS["accent_hover"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")
        status = tk.StringVar(value="Ready")
        tk.Label(
            heading, textvariable=status, bg=panel_bg, fg=COLORS["dim"],
            font=("Segoe UI", 8),
        ).pack(side="right")

        quick_row = tk.Frame(panel, bg=panel_bg)
        quick_row.pack(fill="x", pady=(0, 5))
        for topic, label in QUICK_LABELS.items():
            button = self._button(
                quick_row, label,
                lambda selected=topic, selected_mode=mode: self._send_quick_prompt(selected, selected_mode),
                bg=COLORS["panel_alt"],
            )
            button.configure(font=("Segoe UI", 7, "bold"), padx=6, pady=4)
            button.pack(side="left", padx=(0, 5))

        transcript_frame = tk.Frame(panel, bg=COLORS["border"], bd=1)
        transcript_frame.pack(fill="both", expand=True)
        transcript = tk.Text(
            transcript_frame, bg=COLORS["background"], fg=COLORS["assistant"],
            insertbackground=COLORS["text"], selectbackground=COLORS["accent"],
            relief="flat", wrap="word", padx=10, pady=9,
            font=("Segoe UI", 9), state="disabled", height=7 if mode == "compact" else 18,
        )
        scrollbar = tk.Scrollbar(
            transcript_frame,
            command=transcript.yview,
            bg=COLORS["panel_alt"],
            troughcolor=COLORS["background"],
            activebackground=COLORS["accent"],
            highlightthickness=0,
            bd=0,
        )
        transcript.configure(yscrollcommand=scrollbar.set)
        transcript.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        transcript.tag_configure("user", foreground=COLORS["user"], font=("Segoe UI", 9, "bold"))
        transcript.tag_configure("assistant", foreground=COLORS["assistant"], font=("Segoe UI", 9, "bold"))
        transcript.tag_configure("body", foreground=COLORS["muted"])
        transcript.tag_configure("error", foreground=COLORS["error"])

        input_row = tk.Frame(panel, bg=panel_bg)
        input_row.pack(fill="x", pady=(6, 0))
        entry = tk.Entry(
            input_row, bg=COLORS["panel_alt"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 9),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 6))
        entry.bind("<Return>", lambda _event, selected_mode=mode: self._send_from_entry(selected_mode))
        send_button = self._button(
            input_row, "SEND", lambda selected_mode=mode: self._send_from_entry(selected_mode),
            bg=COLORS["accent"],
        )
        send_button.pack(side="right", fill="y")
        tk.Label(
            panel, text="Chat and summary go to the provider; the save file is not uploaded.",
            bg=panel_bg, fg=COLORS["dim"], font=("Segoe UI", 7), anchor="w",
            wraplength=700 if mode == "full" else 390,
        ).pack(fill="x", pady=(5, 0))
        self.chat_widgets[mode] = {"text": transcript, "entry": entry, "send": send_button, "status": status}
        self._render_chat(mode)

    @staticmethod
    def _button(
        parent: tk.Misc, text: str, command: Any, *, bg: str, width: int | None = None,
    ) -> tk.Button:
        options: dict[str, Any] = {
            "text": text, "command": command, "bg": bg, "fg": COLORS["text"],
            "activebackground": COLORS["accent_hover"], "activeforeground": COLORS["text"],
            "relief": "flat", "bd": 0, "cursor": "hand2",
            "font": ("Segoe UI", 8, "bold"), "padx": 9, "pady": 5,
        }
        if width is not None:
            options["width"] = width
        return tk.Button(parent, **options)

    def _bind_drag(self, widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._drag)

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        sx, sy, wx, wy = self.drag_origin
        self.root.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")

    def _apply_mode(self, mode: str) -> None:
        preset = WINDOW_MODES[mode]
        self.mode = mode
        self.root.overrideredirect(not preset.decorated)
        self.root.attributes("-topmost", self.pinned if mode == "compact" else False)
        try:
            self.root.attributes("-alpha", preset.opacity)
        except tk.TclError:
            pass
        self.root.resizable(preset.resizable, preset.resizable)
        if mode == "compact":
            self.root.minsize(preset.width, preset.height)
            self.root.maxsize(preset.width, preset.height)
            self.root.geometry(f"{preset.width}x{preset.height}+45+75")
        else:
            self.root.minsize(820, 600)
            self.root.maxsize(10000, 10000)
            self.root.geometry(f"{preset.width}x{preset.height}+70+65")
        for name, frame in self.mode_frames.items():
            if name == mode:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        self.root.update_idletasks()
        self.root.lift()

    def show_compact(self) -> None:
        self._apply_mode("compact")

    def show_full(self) -> None:
        self._apply_mode("full")

    def _toggle_pin(self) -> None:
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned if self.mode == "compact" else False)
        self.pin_button.configure(text="PINNED" if self.pinned else "FLOAT")

    def _provider_status(self) -> str:
        if self.settings.api_key:
            return f"API ready · {self.settings.model}"
        if "api.openai.com" in self.settings.base_url:
            return "API key needed · open Settings"
        return f"No key set · {self.settings.model}"

    def open_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("AI provider settings")
        dialog.configure(bg=COLORS["background"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("540x450")
        body = tk.Frame(dialog, bg=COLORS["background"], padx=18, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(
            body, text="OPENAI-COMPATIBLE PROVIDER", bg=COLORS["background"],
            fg=COLORS["text"], font=("Segoe UI", 11, "bold"), anchor="w",
        ).pack(fill="x", pady=(0, 12))

        fields: dict[str, Any] = {}
        for label, key, value in (
            ("Base URL", "base_url", self.settings.base_url),
            ("API key", "api_key", self.settings.api_key),
        ):
            tk.Label(
                body, text=label, bg=COLORS["background"], fg=COLORS["muted"],
                font=("Segoe UI", 9), anchor="w",
            ).pack(fill="x", pady=(5, 3))
            entry = tk.Entry(
                body, bg=COLORS["panel_alt"], fg=COLORS["text"],
                insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 9),
                show="*" if key == "api_key" else "",
            )
            entry.insert(0, value)
            entry.pack(fill="x", ipady=7)
            fields[key] = entry

        model_header = tk.Frame(body, bg=COLORS["background"])
        model_header.pack(fill="x", pady=(8, 3))
        tk.Label(
            model_header, text="Model", bg=COLORS["background"], fg=COLORS["muted"],
            font=("Segoe UI", 9), anchor="w",
        ).pack(side="left")
        model_status = tk.StringVar(value="Load the provider list or type a model ID")
        load_models_button = self._button(
            model_header,
            "LOAD MODELS",
            lambda: self._start_model_lookup(fields, model_status, load_models_button),
            bg=COLORS["panel_alt"],
        )
        load_models_button.pack(side="right")
        model_combo = ttk.Combobox(body, state="normal", font=("Segoe UI", 9))
        model_combo.set(self.settings.model)
        model_combo.pack(fill="x", ipady=3)
        fields["model"] = model_combo
        tk.Label(
            body, textvariable=model_status, bg=COLORS["background"], fg=COLORS["dim"],
            font=("Segoe UI", 8), anchor="w",
        ).pack(fill="x", pady=(3, 0))
        self.model_lookup_ui = {
            "dialog": dialog,
            "combo": model_combo,
            "status": model_status,
            "button": load_models_button,
        }

        tk.Label(
            body,
            text=(
                "The key stays in memory for this run only. Model discovery uses the provider's "
                "GET /models endpoint; some compatible services may not implement it."
            ),
            bg=COLORS["background"], fg=COLORS["dim"], font=("Segoe UI", 8),
            justify="left", wraplength=500, anchor="w",
        ).pack(fill="x", pady=(10, 12))
        actions = tk.Frame(body, bg=COLORS["background"])
        actions.pack(fill="x", side="bottom")

        def close_dialog() -> None:
            self.model_lookup_ui = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

        def apply_settings() -> None:
            base_url = fields["base_url"].get().strip().rstrip("/")
            model = fields["model"].get().strip()
            api_key = fields["api_key"].get().strip()
            if not base_url.startswith(("https://", "http://")):
                model_status.set("Base URL must start with http:// or https://")
                return
            if not model:
                model_status.set("Enter a model name in Settings")
                return
            self.settings = ProviderSettings(base_url=base_url, model=model, api_key=api_key)
            self.compact_provider.configure(text=self._provider_status())
            self._set_all_status(self._provider_status())
            close_dialog()

        self._button(actions, "CANCEL", close_dialog, bg=COLORS["panel_alt"]).pack(
            side="right", padx=(6, 0)
        )
        self._button(actions, "APPLY FOR THIS SESSION", apply_settings, bg=COLORS["accent"]).pack(
            side="right"
        )

    def _start_model_lookup(
        self,
        fields: dict[str, Any],
        status: tk.StringVar,
        button: tk.Button,
    ) -> None:
        base_url = fields["base_url"].get().strip().rstrip("/")
        api_key = fields["api_key"].get().strip()
        if not base_url.startswith(("https://", "http://")):
            status.set("Base URL must start with http:// or https://")
            return
        if not api_key and "api.openai.com" in base_url:
            status.set("Enter your API key first")
            return
        button.configure(state="disabled")
        status.set("Loading available model IDs…")
        threading.Thread(
            target=self._request_model_list,
            args=(base_url, api_key),
            name="bloodborne-copilot-model-list",
            daemon=True,
        ).start()

    def _request_model_list(self, base_url: str, api_key: str) -> None:
        try:
            client = OpenAICompatibleClient(base_url, "", api_key)
            self.model_result_queue.put((client.list_models(), None))
        except Exception as exc:
            self.model_result_queue.put((None, str(exc)))

    def _finish_model_lookup(self, models: list[str] | None, error: str | None) -> None:
        ui = self.model_lookup_ui
        if not ui:
            return
        try:
            if not ui["dialog"].winfo_exists():
                return
            ui["button"].configure(state="normal")
            if error:
                ui["status"].set(f"Could not load models: {error}")
            elif not models:
                ui["combo"].configure(values=())
                ui["status"].set("The endpoint returned no model IDs; type one manually")
            else:
                ui["combo"].configure(values=tuple(models))
                ui["status"].set(
                    f"Loaded {len(models)} model IDs. Some may not support chat completions."
                )
        except tk.TclError:
            self.model_lookup_ui = None

    def _set_all_status(self, text: str) -> None:
        for widgets in self.chat_widgets.values():
            widgets["status"].set(text)

    def _choose_save(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a Bloodborne userdata save",
            filetypes=[("Bloodborne save", "userdata*")],
        )
        if path:
            self.load_save(Path(path))

    def load_save(self, path: Path) -> None:
        try:
            snapshot = build_snapshot(inspect_save(path))
        except (OSError, ValueError) as exc:
            self._set_all_status(f"Could not read save: {exc}")
            return
        self.snapshot = snapshot
        self.snapshot_filename = path.name
        self.compact_character.configure(text=snapshot["character"])
        self.compact_stats.configure(text=snapshot["stats"])
        for key, value in snapshot.items():
            if key in self.snapshot_labels:
                self.snapshot_labels[key].configure(text=value)
        self.full_snapshot_status.configure(text=f"{snapshot['disclaimer']}\n{path.name}")

    def _send_quick_prompt(self, topic: str, mode: str) -> None:
        self._send_message(QUICK_PROMPTS[topic], mode)

    def _send_from_entry(self, mode: str) -> str:
        entry = self.chat_widgets[mode]["entry"]
        text = entry.get().strip()
        if text:
            entry.delete(0, "end")
            self._send_message(text, mode)
        return "break"

    def _send_message(self, text: str, source_mode: str) -> None:
        if self.busy:
            return
        if not self.settings.model or not self.settings.base_url:
            self.chat_widgets[source_mode]["status"].set("Set provider details in Settings")
            return
        if not self.settings.api_key and "api.openai.com" in self.settings.base_url:
            self.chat_widgets[source_mode]["status"].set("Add an API key in Settings")
            return
        self.history.append({"role": "user", "content": text})
        messages = [
            {"role": "system", "content": build_system_prompt(self.snapshot)},
            *self.history[-24:],
        ]
        self.busy = True
        self._set_busy(True)
        self._set_all_status(f"Contacting {self.settings.model}…")
        self._render_chat()
        settings = self.settings
        threading.Thread(
            target=self._request_reply,
            args=(messages, settings),
            name="bloodborne-copilot-chat",
            daemon=True,
        ).start()

    def _request_reply(
        self, messages: list[dict[str, str]], settings: ProviderSettings,
    ) -> None:
        try:
            client = OpenAICompatibleClient(settings.base_url, settings.model, settings.api_key)
            self.result_queue.put((client.complete(messages), None))
        except Exception as exc:
            self.result_queue.put((None, str(exc)))

    def _poll_results(self) -> None:
        while True:
            try:
                response, error = self.result_queue.get_nowait()
            except queue.Empty:
                break
            if response:
                self.history.append({"role": "assistant", "content": response})
            elif error:
                self.history.append({"role": "assistant", "content": f"Request failed: {error}"})
            self.busy = False
            self._set_busy(False)
            self._set_all_status("Ready" if not error else "Check provider settings or connection")
            self._render_chat()
        while True:
            try:
                models, model_error = self.model_result_queue.get_nowait()
            except queue.Empty:
                break
            self._finish_model_lookup(models, model_error)
        if self.running:
            self.root.after(120, self._poll_results)

    def _set_busy(self, busy: bool) -> None:
        for widgets in self.chat_widgets.values():
            widgets["send"].configure(state="disabled" if busy else "normal")

    def _render_chat(self, mode: str | None = None) -> None:
        modes = [mode] if mode else list(self.chat_widgets)
        for selected_mode in modes:
            widgets = self.chat_widgets.get(selected_mode)
            if not widgets:
                continue
            transcript: tk.Text = widgets["text"]
            transcript.configure(state="normal")
            transcript.delete("1.0", "end")
            messages = self.history[-8:] if selected_mode == "compact" else self.history[-100:]
            if not messages:
                transcript.insert(
                    "end",
                    "Ready when you are. Ask about a build, boss, mechanic, or next step. "
                    "I cannot see the live game yet.\n",
                    "body",
                )
            for message in messages:
                role = message["role"]
                label = "YOU" if role == "user" else "COPILOT"
                tag = "user" if role == "user" else "assistant"
                content_tag = "error" if message["content"].startswith("Request failed:") else "body"
                transcript.insert("end", f"{label}\n", tag)
                transcript.insert("end", f"{message['content']}\n\n", content_tag)
            transcript.configure(state="disabled")
            transcript.see("end")

    def close(self) -> None:
        self.running = False
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bloodborne Copilot two-mode desktop app")
    parser.add_argument("--save", type=Path, help="Optionally load a userdata save on startup")
    parser.add_argument("--full", action="store_true", help="Start in the full window view")
    args = parser.parse_args(argv)
    root = tk.Tk()
    app = CopilotOverlay(root)
    if args.full:
        root.after(150, app.show_full)
    if args.save is not None:
        root.after(150, lambda: app.load_save(args.save))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
