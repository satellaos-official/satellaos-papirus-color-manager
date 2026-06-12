#!/usr/bin/env python3

import sys
import os
import subprocess
import shlex
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
    QFrame, QCheckBox, QSizePolicy, QLineEdit
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtSvgWidgets import QSvgWidget

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

COLORS = {
    "dark": {
        "bg":        "#1E1E1E",
        "card":      "#2e2e2e",
        "text":      "#bfbfbf",
        "accent":    "#442178",
        "scrollbar": "#F5F5F5",
        "status_bg": "#252525",
        "status_ok": "#7ecb8f",
        "status_err":"#e06c75",
    },
    "light": {
        "bg":        "#F5F5F5",
        "card":      "#bfbfbf",
        "text":      "#2e2e2e",
        "accent":    "#442178",
        "scrollbar": "#1E1E1E",
        "status_bg": "#e8e8e8",
        "status_ok": "#2d7a3e",
        "status_err":"#c0392b",
    },
}

THEMES = [
    "adwaita", "black", "blue", "bluegrey", "breeze", "brown",
    "carmine", "cyan", "darkcyan", "deeporange", "green", "grey",
    "indigo", "magenta", "nordic", "orange", "palebrown", "paleorange",
    "pink", "red", "teal", "violet", "white", "yaru", "yellow",
]

# (label, command_template)  — {theme} will be substituted at runtime
POST_ACTIONS = [
    ("Update Icon Cache",  "gtk-update-icon-cache -f /usr/share/icons/Papirus"),
    ("Restart Thunar",     "thunar -q"),
    ("Restart XFCE Panel", "xfce4-panel -r"),
    ("Restart XFDesktop",  "xfdesktop --reload"),
]


def build_stylesheet(mode: str) -> str:
    c = COLORS[mode]
    hover_item = "#3a3a3a" if mode == "dark" else "#d0d0d0"
    disabled_bg = "#333333" if mode == "dark" else "#c8c8c8"
    return f"""
        QMainWindow, QWidget#root {{
            background-color: {c['bg']};
        }}
        QWidget {{
            background-color: {c['bg']};
            color: {c['text']};
            font-family: 'Noto Sans', sans-serif;
            font-size: 13px;
        }}
        QListWidget {{
            background-color: {c['card']};
            color: {c['text']};
            border: none;
            border-radius: 6px;
            padding: 4px;
            outline: 0;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {c['accent']};
            color: #ffffff;
        }}
        QListWidget::item:hover:!selected {{
            background-color: {hover_item};
        }}
        QScrollBar:vertical {{
            background: {c['bg']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['scrollbar']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        QPushButton#mode_btn {{
            background-color: {c['card']};
            border: none;
            border-radius: 6px;
            padding: 6px;
        }}
        QPushButton#mode_btn:hover {{
            background-color: {c['accent']};
        }}
        QPushButton#apply_btn {{
            background-color: {c['accent']};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#apply_btn:hover {{
            background-color: #5a2e9a;
        }}
        QPushButton#apply_btn:pressed {{
            background-color: #321560;
        }}
        QPushButton#apply_btn:disabled {{
            background-color: {disabled_bg};
            color: #888888;
        }}
        QLabel#preview_label {{
            color: {c['text']};
            font-size: 11px;
        }}
        QFrame#preview_card {{
            background-color: {c['card']};
            border-radius: 8px;
        }}
        QFrame#status_bar {{
            background-color: {c['status_bg']};
            border-radius: 6px;
        }}
        QLabel#status_label {{
            background: transparent;
            color: {c['text']};
            font-size: 12px;
            font-family: 'Monospace', monospace;
            padding: 0 4px;
        }}
        QCheckBox {{
            color: {c['text']};
            spacing: 6px;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
            border: 1px solid {c['scrollbar']};
            background: {c['card']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c['accent']};
            border-color: {c['accent']};
        }}
        QLineEdit#password_input {{
            background-color: {c['card']};
            color: {c['text']};
            border: 1px solid {c['scrollbar']};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
        }}
        QLineEdit#password_input:focus {{
            border-color: {c['accent']};
        }}
        QLabel#password_label {{
            color: {c['text']};
            font-size: 12px;
            background: transparent;
        }}
    """


class ApplyWorker(QThread):
    line_output = pyqtSignal(str)
    finished    = pyqtSignal(bool)   # True = success

    def __init__(self, theme: str, post_flags: dict, password: str):
        super().__init__()
        self.theme      = theme
        self.post_flags = post_flags  # {label: bool}
        self.password   = password

    def _run_sudo(self, cmd: str) -> tuple[bool, str]:
        """Run a single command via sudo -S (password via stdin); return (ok, output)."""
        try:
            result = subprocess.run(
                ["sudo", "-S"] + shlex.split(cmd),
                input=self.password + "\n",
                capture_output=True,
                text=True,
            )
            # Filter out the sudo password prompt from stderr
            stderr_clean = "\n".join(
                line for line in result.stderr.splitlines()
                if not line.startswith("[sudo]")
            ).strip()
            out = (result.stdout + ("\n" + stderr_clean if stderr_clean else "")).strip()
            return result.returncode == 0, out
        except FileNotFoundError:
            return False, "sudo not found"

    def run(self):
        # 1. Main papirus-folders call
        main_cmd = f"papirus-folders -C {self.theme}"
        self.line_output.emit(f"$ {main_cmd}")
        ok, out = self._run_sudo(main_cmd)
        if out:
            self.line_output.emit(out)
        if not ok:
            self.line_output.emit("✗ Failed. Wrong password or papirus-folders not found.")
            self.finished.emit(False)
            return

        # 2. Post-action steps (no pkexec — run as current user)
        for label, cmd in POST_ACTIONS:
            if not self.post_flags.get(label, False):
                continue
            self.line_output.emit(f"$ {cmd}")
            try:
                result = subprocess.run(
                    shlex.split(cmd),
                    capture_output=True,
                    text=True,
                )
                out = (result.stdout + result.stderr).strip()
                if out:
                    self.line_output.emit(out)
            except FileNotFoundError:
                self.line_output.emit(f"  (skipped — {cmd.split()[0]} not found)")

        self.line_output.emit("✓ Done.")
        self.finished.emit(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mode           = "dark"
        self.selected_theme = THEMES[0]
        self.worker         = None

        self.setWindowTitle("SatellaOS Papirus Color Manager")
        self.setMinimumSize(720, 540)
        self.resize(820, 580)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        # ── Left: theme list ──────────────────────────────────────────
        self.theme_list = QListWidget()
        self.theme_list.setFixedWidth(180)
        for name in THEMES:
            self.theme_list.addItem(QListWidgetItem(name))
        self.theme_list.setCurrentRow(0)
        self.theme_list.currentTextChanged.connect(self._on_theme_change)
        outer.addWidget(self.theme_list)

        # ── Right panel ───────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(10)
        outer.addLayout(right)

        # Mode buttons (top-right)
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.dark_btn  = self._make_mode_btn("darkmode.png",  "Dark Mode",
                                              lambda: self._set_mode("dark"))
        self.light_btn = self._make_mode_btn("lightmode.png", "Light Mode",
                                              lambda: self._set_mode("light"))
        top_row.addWidget(self.dark_btn)
        top_row.addWidget(self.light_btn)
        right.addLayout(top_row)

        # Preview card
        self.preview_card = QFrame()
        self.preview_card.setObjectName("preview_card")
        preview_layout = QHBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(32)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.svg_folder   = self._make_svg_slot()
        self.svg_home     = self._make_svg_slot()
        self.svg_download = self._make_svg_slot()

        for widget in [self.svg_folder, self.svg_home, self.svg_download]:
            preview_layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)

        right.addWidget(self.preview_card, stretch=1)

        # Checkboxes
        cb_row = QHBoxLayout()
        cb_row.setSpacing(16)
        self.checkboxes: dict[str, QCheckBox] = {}
        for label, _ in POST_ACTIONS:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.checkboxes[label] = cb
            cb_row.addWidget(cb)
        cb_row.addStretch()
        right.addLayout(cb_row)

        # Status bar
        self.status_bar = QFrame()
        self.status_bar.setObjectName("status_bar")
        self.status_bar.setFixedHeight(64)
        status_layout = QVBoxLayout(self.status_bar)
        status_layout.setContentsMargins(8, 4, 8, 4)
        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        right.addWidget(self.status_bar)

        # Password input
        pw_row = QHBoxLayout()
        pw_row.setSpacing(8)
        pw_label = QLabel("sudo password:")
        pw_label.setObjectName("password_label")
        pw_row.addWidget(pw_label)
        self.password_input = QLineEdit()
        self.password_input.setObjectName("password_input")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter sudo password…")
        self.password_input.setFixedHeight(34)
        pw_row.addWidget(self.password_input)
        right.addLayout(pw_row)

        # Apply button
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.apply_btn = QPushButton("Apply to System")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.setFixedHeight(38)
        self.apply_btn.clicked.connect(self._apply)
        bottom_row.addWidget(self.apply_btn)
        right.addLayout(bottom_row)

        self._apply_style()
        self._refresh_preview()

    # ── widget factories ──────────────────────────────────────────────

    def _make_svg_slot(self) -> QSvgWidget:
        w = QSvgWidget()
        w.setFixedSize(96, 96)
        w.setStyleSheet("background: transparent;")
        return w

    def _make_mode_btn(self, icon_file: str, tooltip: str, slot) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("mode_btn")
        btn.setFixedSize(36, 36)
        btn.setIconSize(QSize(24, 24))
        btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        path = os.path.join(SCRIPT_DIR, "mode", icon_file)
        if os.path.exists(path):
            btn.setIcon(QIcon(path))
        else:
            btn.setText(icon_file[0].upper())
        return btn

    # ── style ─────────────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet(build_stylesheet(self.mode))

    def _set_mode(self, mode: str):
        self.mode = mode
        self._apply_style()

    # ── preview ───────────────────────────────────────────────────────

    def _on_theme_change(self, name: str):
        self.selected_theme = name
        self._refresh_preview()

    def _refresh_preview(self):
        t    = self.selected_theme
        base = os.path.join(SCRIPT_DIR, "papirus-folders", t)
        for widget, path in [
            (self.svg_folder,   os.path.join(base, f"folder-{t}.svg")),
            (self.svg_home,     os.path.join(base, f"user-{t}-home.svg")),
            (self.svg_download, os.path.join(base, f"folder-{t}-download.svg")),
        ]:
            widget.load(path if os.path.exists(path) else "")

    # ── apply ─────────────────────────────────────────────────────────

    def _apply(self):
        post_flags = {label: cb.isChecked() for label, cb in self.checkboxes.items()}
        password = self.password_input.text()

        if not password:
            self._set_status("✗ Please enter your sudo password.")
            return

        self.apply_btn.setEnabled(False)
        self.apply_btn.setText("Applying…")
        self._set_status("Starting…")

        self.worker = ApplyWorker(self.selected_theme, post_flags, password)
        self.worker.line_output.connect(self._set_status)
        self.worker.finished.connect(self._on_apply_done)
        self.worker.start()

    def _on_apply_done(self, success: bool):
        self.apply_btn.setEnabled(True)
        self.apply_btn.setText("Apply to System")
        self.password_input.clear()
        if not success:
            self._set_status("✗ Operation failed. Check output above.")

    def _set_status(self, msg: str):
        self.status_label.setText(msg)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SatellaOS Papirus Color Manager")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()