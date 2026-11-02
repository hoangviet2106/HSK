import ctypes
import html
import logging
import re
import threading
import time
import tkinter as tk
from typing import Optional

import pyperclip
import requests
from pynput import keyboard, mouse
from pypinyin import Style, lazy_pinyin


HOTKEY_QUIT = "<ctrl>+<shift>+q"
TRANSLATION_URL = "https://api.mymemory.translated.net/get"
CHINESE_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
COLORS = {
    "paper": "#F4EEDF",
    "card": "#FFFCF5",
    "ink": "#283B32",
    "muted": "#817A6B",
    "cinnabar": "#A94435",
    "gold": "#D2B16F",
    "jade": "#54796A",
    "border": "#E5D9C2",
    "pinyin": "#F0F2E9",
}


class ChineseVietnameseTranslator:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("漢越小箋 · Trung Việt")
        self.root.configure(bg=COLORS["paper"])
        window_width = 440
        window_x = max(0, self.root.winfo_screenwidth() - window_width - 24)
        self.root.geometry(f"{window_width}x520+{window_x}+72")
        self.root.minsize(380, 460)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.bind("<Configure>", self._on_panel_configure)
        self.panel_bounds = (0, 0, 0, 0)
        self._build_panel()
        self.state_lock = threading.Lock()
        self.clipboard_lock = threading.Lock()
        self.active_text: Optional[str] = None
        self.update_generation = 0
        self.pending_translations: dict[str, list[int]] = {}
        self.translation_cache: dict[str, str] = {}
        self.keyboard_controller = keyboard.Controller()

    def _build_panel(self) -> None:
        content = tk.Frame(self.root, bg=COLORS["paper"], padx=16, pady=16)
        content.pack(fill="both", expand=True)

        banner = tk.Frame(content, bg=COLORS["ink"], padx=16, pady=14)
        banner.pack(fill="x", pady=(0, 14))
        title_block = tk.Frame(banner, bg=COLORS["ink"])
        title_block.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_block,
            text="漢越小箋",
            bg=COLORS["ink"],
            fg="#FFF9EC",
            font=("Microsoft YaHei UI", 21, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text="TRUNG  →  VIỆT   ·   PINYIN & NGHĨA",
            bg=COLORS["ink"],
            fg=COLORS["gold"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(2, 0))
        seal = tk.Frame(
            banner,
            bg=COLORS["cinnabar"],
            highlightthickness=1,
            highlightbackground=COLORS["gold"],
            padx=7,
            pady=4,
        )
        seal.pack(side="right", padx=(8, 0))
        tk.Label(
            seal,
            text="译",
            bg=COLORS["cinnabar"],
            fg="#FFF5E7",
            font=("Microsoft YaHei UI", 17, "bold"),
        ).pack()

        self.source_label = self._make_card(
            content,
            "漢字  ·  CHỮ HÁN",
            "Bôi đen chữ Trung để bắt đầu",
            background=COLORS["card"],
            foreground=COLORS["ink"],
            font=("Microsoft YaHei UI", 22),
        )
        self.pinyin_label = self._make_card(
            content,
            "拼音  ·  PINYIN",
            "Pinyin có dấu thanh sẽ hiện ở đây",
            background=COLORS["pinyin"],
            foreground=COLORS["jade"],
            font=("Segoe UI", 15),
        )
        self.meaning_label = self._make_card(
            content,
            "释义  ·  NGHĨA TIẾNG VIỆT",
            "Bản dịch sẽ hiện ở đây",
            background=COLORS["card"],
            foreground=COLORS["ink"],
            font=("Segoe UI", 13),
            expand=True,
        )

        footer = tk.Frame(content, bg=COLORS["paper"])
        footer.pack(fill="x", pady=(12, 0))
        tk.Frame(footer, bg=COLORS["gold"], height=1).pack(fill="x", pady=(0, 8))
        tk.Label(
            footer,
            text="BÔI ĐEN ĐỂ DỊCH     ·     Ctrl+Shift+Q ĐỂ THOÁT",
            bg=COLORS["paper"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="center")

    @staticmethod
    def _make_card(
        parent: tk.Frame,
        title: str,
        initial_text: str,
        background: str,
        foreground: str,
        font: tuple[str, int],
        expand: bool = False,
    ) -> tk.Label:
        card = tk.Frame(
            parent,
            bg=background,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            padx=13,
            pady=10,
        )
        card.pack(fill="both" if expand else "x", expand=expand, pady=5)
        tk.Label(
            card,
            text=title,
            bg=background,
            fg=COLORS["cinnabar"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        tk.Frame(card, bg=COLORS["border"], height=1).pack(fill="x", pady=(6, 8))
        value = tk.Label(
            card,
            text=initial_text,
            bg=background,
            fg=foreground,
            font=font,
            wraplength=350,
            justify="left",
            anchor="nw",
        )
        value.pack(anchor="nw", fill="both" if expand else "x", expand=expand)
        return value

    def _on_panel_configure(self, event: tk.Event) -> None:
        if event.widget is self.root:
            left = self.root.winfo_rootx()
            top = self.root.winfo_rooty()
            self.panel_bounds = (
                left,
                top,
                left + self.root.winfo_width(),
                top + self.root.winfo_height(),
            )

    def run(self) -> None:
        hotkeys = keyboard.GlobalHotKeys(
            {
                HOTKEY_QUIT: self.stop,
            }
        )
        mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        hotkeys.start()
        mouse_listener.start()
        try:
            self.root.mainloop()
        finally:
            mouse_listener.stop()
            hotkeys.stop()

    def stop(self) -> None:
        self.root.after(0, self.root.destroy)

    def _on_mouse_click(
        self, x: int, y: int, button: mouse.Button, pressed: bool
    ) -> None:
        if pressed or button != mouse.Button.left:
            return
        left, top, right, bottom = self.panel_bounds
        if left <= x < right and top <= y < bottom:
            return
        threading.Thread(
            target=self._copy_and_translate_selection, daemon=True
        ).start()

    def _copy_and_translate_selection(self) -> None:
        if not self.clipboard_lock.acquire(blocking=False):
            return
        try:
            previous_clipboard = pyperclip.paste()
            clipboard_sequence = self._clipboard_sequence()
            try:
                with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                    self.keyboard_controller.press("c")
                    self.keyboard_controller.release("c")
                time.sleep(0.12)
                selection_was_copied = (
                    self._clipboard_sequence() != clipboard_sequence
                )
                selected_text = pyperclip.paste().strip() if selection_was_copied else ""
            finally:
                pyperclip.copy(previous_clipboard)
            if not selected_text or not CHINESE_PATTERN.search(selected_text):
                return
            self._activate_text(selected_text)
        except Exception as exc:
            logging.exception("Could not read the selected text")
            self._show_message(f"Không đọc được văn bản đã chọn: {exc}")
        finally:
            self.clipboard_lock.release()

    @staticmethod
    def _clipboard_sequence() -> int:
        return ctypes.windll.user32.GetClipboardSequenceNumber()

    def _activate_text(self, text: str) -> None:
        with self.state_lock:
            if text == self.active_text:
                return
            self.active_text = text
            self.update_generation += 1
            generation = self.update_generation
            cached = self.translation_cache.get(text)
        self.root.after(0, self._set_source, text, generation)
        if cached is not None:
            self.root.after(0, self._set_meaning, text, cached, generation)
        else:
            self._translate_async(text, generation)

    def _translate_async(self, text: str, generation: int) -> None:
        with self.state_lock:
            if text in self.translation_cache:
                cached = self.translation_cache[text]
                self.root.after(0, self._set_meaning, text, cached, generation)
                return
            if text in self.pending_translations:
                self.pending_translations[text].append(generation)
                return
            self.pending_translations[text] = [generation]
        threading.Thread(
            target=self._translate_worker,
            args=(text,),
            daemon=True,
        ).start()

    def _translate_worker(self, text: str) -> None:
        try:
            translated = self._translate(text)
            with self.state_lock:
                self.translation_cache[text] = translated
                requests = self.pending_translations.pop(text)
                requests = [
                    generation
                    for generation in requests
                    if generation == self.update_generation and text == self.active_text
                ]
            for generation in requests:
                self.root.after(0, self._set_meaning, text, translated, generation)
        except Exception as exc:
            with self.state_lock:
                requests = self.pending_translations.pop(text, [])
                current_generations = [
                    generation
                    for generation in requests
                    if generation == self.update_generation and text == self.active_text
                ]
            logging.exception("Translation request failed")
            for generation in current_generations:
                self.root.after(
                    0,
                    self._set_meaning,
                    text,
                    f"Dịch không thành công: {exc}",
                    generation,
                )

    def _set_source(self, text: str, generation: int) -> None:
        with self.state_lock:
            if generation != self.update_generation or text != self.active_text:
                return
        syllables = lazy_pinyin(
            text, style=Style.TONE, errors=lambda value: list(value)
        )
        self.source_label.configure(text=text)
        self.pinyin_label.configure(text=" ".join(syllables) or "—")
        self.meaning_label.configure(text="Đang dịch…")

    def _set_meaning(self, text: str, meaning: str, generation: int) -> None:
        with self.state_lock:
            if generation != self.update_generation or text != self.active_text:
                return
        self.meaning_label.configure(text=meaning)

    @staticmethod
    def _translate(text: str) -> str:
        if len(text) > 450:
            raise ValueError("Văn bản dài hơn giới hạn 450 ký tự mỗi lần dịch.")
        response = requests.get(
            TRANSLATION_URL,
            params={"q": text, "langpair": "zh-CN|vi"},
            timeout=(4, 10),
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("responseStatus") != 200:
            raise RuntimeError(
                payload.get("responseDetails") or "Dịch vụ từ chối yêu cầu."
            )
        result = payload.get("responseData", {}).get("translatedText", "").strip()
        if not result:
            raise RuntimeError("Dịch vụ không trả về bản dịch.")
        return html.unescape(result)

    def _show_message(self, message: str) -> None:
        self.root.after(0, self.meaning_label.configure, {"text": message})


if __name__ == "__main__":
    logging.basicConfig(
        filename="translator.log",
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    ChineseVietnameseTranslator().run()
