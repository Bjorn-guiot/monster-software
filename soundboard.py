
import json
import math
import re
import sys
import threading
import time
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


APP_DIR = Path(__file__).resolve().parent
HIGHSCORES_FILE = APP_DIR / "highscores.json"
EXPORT_DIR = APP_DIR / "daily_exports"
LOGO_FILE = APP_DIR / "logo-clean.png"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
NOISE_FLOOR_DBFS = -90.0
DISPLAY_MAX_DB = 132.0
SHURE_MV7_SAMPLE_RATE = 48_000
CALIBRATION_OFFSET_DB = 141.0


class AudioLevelReader:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dbfs = NOISE_FLOOR_DBFS
        self._stream: sd.InputStream | None = None
        self.device_name = ""

    @staticmethod
    def _find_mv7_input() -> tuple[int, str]:
        for index, device in enumerate(sd.query_devices()):
            name = str(device["name"])
            if "mv7" in name.lower() and device["max_input_channels"] >= 1:
                return index, name
        raise RuntimeError("Shure MV7 niet gevonden. Sluit de microfoon via USB aan en start de app opnieuw.")

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            pass
        rms = float(np.sqrt(np.mean(np.square(indata, dtype=np.float64))))
        dbfs = 20 * math.log10(max(rms, 1e-9))
        with self._lock:
            self._dbfs = max(NOISE_FLOOR_DBFS, min(0.0, dbfs))

    def start(self) -> None:
        device_index, self.device_name = self._find_mv7_input()
        self._stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=SHURE_MV7_SAMPLE_RATE,
            blocksize=1024,
            dtype="float32",
            latency="low",
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def level(self) -> float:
        with self._lock:
            return max(0.0, min(DISPLAY_MAX_DB, self._dbfs + CALIBRATION_OFFSET_DB))


class LogoMeter(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(245)
        self._target = 0.0
        self._shown = 0.0
        self._logo = QPixmap(str(LOGO_FILE))

    def set_level(self, decibels: float) -> None:
        self._target = max(0.0, min(1.0, decibels / DISPLAY_MAX_DB))
        self._shown += (self._target - self._shown) * 0.28
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._logo.isNull():
            painter.setPen(QColor("#3CD070"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Logo niet gevonden")
            return
        available = self.rect().adjusted(12, 6, -12, -6)
        ratio = self._logo.width() / self._logo.height()
        height = min(available.height(), int(available.width() / ratio))
        width = int(height * ratio)
        x = available.x() + (available.width() - width) // 2
        y = available.y() + (available.height() - height) // 2
        target = QRect(x, y, width, height)

        # De donkere vorm toont de volledige meter; het heldere logo groeit omhoog.
        painter.setOpacity(0.16)
        painter.drawPixmap(target, self._logo)
        painter.save()
        filled_height = int(target.height() * self._shown)
        painter.setClipRect(target.x(), target.bottom() - filled_height + 1, target.width(), filled_height)
        painter.setOpacity(1.0)
        painter.drawPixmap(target, self._logo)
        painter.restore()


class SoundboardWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Monster Energy Scream Challenge")
        self.setMinimumSize(1000, 620)
        self.resize(1180, 720)
        self.audio = AudioLevelReader()
        self.measurement_timer = QTimer(self)
        self.measurement_timer.setInterval(40)
        self.measurement_timer.timeout.connect(self.update_measurement)
        self.daily_export_timer = QTimer(self)
        self.daily_export_timer.setSingleShot(True)
        self.daily_export_timer.timeout.connect(self.export_at_end_of_day)
        self.started_at = 0.0
        self.max_db = 0.0
        self.is_measuring = False
        self._build_ui()
        self.load_highscores()
        self.schedule_daily_export()

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111111; color: #f0f0f0; }
            QLineEdit { background: #1e1e1e; border: 1px solid #444; border-radius: 5px;
                        padding: 10px; color: white; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #3CD070; }
            QPushButton { background: #3CD070; color: #07160c; border: none; border-radius: 6px;
                          padding: 12px 18px; font-weight: bold; font-size: 15px; }
            QPushButton:hover { background: #54e786; }
            QPushButton:disabled { background: #2b573c; color: #94a79a; }
            QTableWidget { background: #181818; gridline-color: #333; border: 1px solid #333;
                           border-radius: 6px; color: #eee; }
            QHeaderView::section { background: #242424; color: #3CD070; padding: 8px;
                                   border: none; font-weight: bold; }
        """)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        header_panel = QFrame()
        header_panel.setMinimumHeight(78)
        header_panel.setStyleSheet("QFrame { background: #181818; border: 1px solid #306b45; border-radius: 8px; }")
        header_row = QHBoxLayout(header_panel)
        header_row.setContentsMargins(22, 10, 22, 10)
        header_row.setSpacing(14)
        header_row.addStretch(1)
        header_row.addWidget(self._make_logo_label(header_panel, 48))
        header = QLabel("MONSTER ENERGY SCREAM CHALLENGE")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 26, QFont.Weight.Black))
        header.setStyleSheet("background: transparent; color: #3CD070; border: none; letter-spacing: 2px;")
        header_row.addWidget(header)
        header_row.addWidget(self._make_logo_label(header_panel, 48))
        header_row.addStretch(1)
        layout.addWidget(header_panel)

        content = QHBoxLayout()
        content.setSpacing(24)
        layout.addLayout(content, 1)

        left = QVBoxLayout()
        left.setSpacing(16)
        content.addLayout(left, 3)

        registration = QFrame()
        registration.setStyleSheet("QFrame { background: #181818; border: 1px solid #303030; border-radius: 8px; }")
        form = QFormLayout(registration)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Voor- en achternaam")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("naam@voorbeeld.nl")
        self.name_input.textChanged.connect(self.validate_form)
        self.email_input.textChanged.connect(self.validate_form)
        form.addRow("Volledige naam", self.name_input)
        form.addRow("E-mailadres", self.email_input)
        left.addWidget(registration)

        self.db_label = QLabel("0.0 dB")
        self.db_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.db_label.setFont(QFont("Arial", 43, QFont.Weight.Bold))
        self.db_label.setStyleSheet("color: #3CD070; margin-top: 10px;")
        left.addWidget(self.db_label)
        self.status_label = QLabel("Sluit de Shure MV7 via USB aan en vul je gegevens in.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #bdbdbd; font-size: 14px;")
        left.addWidget(self.status_label)
        export_note = QLabel("Dagelijkse Top 10-export: daily_exports")
        export_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        export_note.setStyleSheet("color: #777; font-size: 11px;")
        left.addWidget(export_note)
        self.meter = LogoMeter()
        left.addWidget(self.meter)
        self.start_button = QPushButton("START SCHREEUW TEST")
        self.start_button.setMinimumHeight(54)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_test)
        left.addWidget(self.start_button)
        left.addStretch()

        ranking_box = QFrame()
        ranking_box.setStyleSheet("QFrame { background: #181818; border: 1px solid #303030; border-radius: 8px; }")
        ranking_layout = QVBoxLayout(ranking_box)
        ranking_title = QLabel("TOP 10 RANKINGBOARD")
        ranking_title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        ranking_title.setStyleSheet("color: #3CD070; border: none;")
        ranking_layout.addWidget(ranking_title)
        self.ranking_table = QTableWidget(0, 3)
        self.ranking_table.setHorizontalHeaderLabels(["Rank", "Naam", "Max Score (dB)"])
        self.ranking_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ranking_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.ranking_table.verticalHeader().setVisible(False)
        self.ranking_table.setColumnWidth(0, 55)
        self.ranking_table.setColumnWidth(1, 145)
        self.ranking_table.horizontalHeader().setStretchLastSection(True)
        ranking_layout.addWidget(self.ranking_table)
        content.addWidget(ranking_box, 2)

    @staticmethod
    def _make_logo_label(parent: QWidget, size: int) -> QLabel:
        """Maakt een transparant, schaalbaar label voor het aangeleverde Monster-logo."""
        logo = QLabel(parent)
        logo.setPixmap(QPixmap(str(LOGO_FILE)))
        logo.setFixedSize(size, size)
        logo.setScaledContents(True)
        logo.setStyleSheet("background: transparent; border: none;")
        return logo

    def validate_form(self) -> None:
        name_parts = self.name_input.text().strip().split()
        valid_full_name = len(name_parts) >= 2
        valid = valid_full_name and bool(EMAIL_PATTERN.match(self.email_input.text().strip()))
        self.start_button.setEnabled(valid and not self.is_measuring)

    def start_test(self) -> None:
        try:
            self.audio.start()
        except Exception as error:
            QMessageBox.critical(self, "Microfoon niet beschikbaar", f"De microfoon kon niet worden geopend.\n\n{error}")
            return
        self.is_measuring = True
        self.max_db = 0.0
        self.started_at = time.monotonic()
        self.start_button.setEnabled(False)
        self.name_input.setEnabled(False)
        self.email_input.setEnabled(False)
        self.status_label.setText(f"METING ACTIEF — {self.audio.device_name} — nog 5.0 s")
        self.measurement_timer.start()

    def update_measurement(self) -> None:
        current_db = self.audio.level()
        self.max_db = max(self.max_db, current_db)
        self.db_label.setText(f"{current_db:.1f} dB")
        self.meter.set_level(current_db)
        remaining = max(0.0, 5.0 - (time.monotonic() - self.started_at))
        self.status_label.setText(f"METING ACTIEF — nog {remaining:.1f} s")
        if remaining <= 0:
            self.finish_test()

    def finish_test(self) -> None:
        self.measurement_timer.stop()
        self.audio.stop()
        self.is_measuring = False
        score = {"name": self.name_input.text().strip(), "email": self.email_input.text().strip(), "max_db": round(self.max_db, 1)}
        scores = self.read_scores()
        scores.append(score)
        scores.sort(key=lambda entry: entry.get("max_db", 0), reverse=True)
        self.write_scores(scores)
        self.populate_ranking(scores)
        self.status_label.setText(f"TEST KLAAR — jouw piek: {self.max_db:.1f} dB SPL")
        self.name_input.clear()
        self.email_input.clear()
        self.name_input.setEnabled(True)
        self.email_input.setEnabled(True)
        self.validate_form()

    def read_scores(self) -> list[dict]:
        try:
            with HIGHSCORES_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def write_scores(self, scores: list[dict]) -> None:
        with HIGHSCORES_FILE.open("w", encoding="utf-8") as file:
            json.dump(scores, file, ensure_ascii=False, indent=2)

    def load_highscores(self) -> None:
        scores = self.read_scores()
        scores.sort(key=lambda entry: entry.get("max_db", 0), reverse=True)
        self.populate_ranking(scores)

    def populate_ranking(self, scores: list[dict]) -> None:
        top_ten = scores[:10]
        self.ranking_table.setRowCount(len(top_ten))
        for row, score in enumerate(top_ten):
            # De volledige naam blijft privé in het JSON-bestand; toon alleen de voornaam.
            full_name = str(score.get("name", "Onbekend")).strip()
            first_name = full_name.split()[0] if full_name else "Onbekend"
            values = [str(row + 1), first_name, f"{float(score.get('max_db', 0)):.1f}"]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if column != 1 else Qt.AlignmentFlag.AlignVCenter)
                self.ranking_table.setItem(row, column, item)

    def schedule_daily_export(self) -> None:
        now = datetime.now()
        next_midnight = datetime.combine(now.date() + timedelta(days=1), clock_time.min)
        milliseconds = max(1, int((next_midnight - now).total_seconds() * 1000))
        self.daily_export_timer.start(milliseconds)

    def export_at_end_of_day(self) -> None:
        export_date = date.today() - timedelta(days=1)
        try:
            self.export_top_ten_to_excel(export_date)
            self.status_label.setText(f"Dagelijkse Top 10 geëxporteerd: {export_date.isoformat()}")
        except (OSError, RuntimeError) as error:
            self.status_label.setText(f"Dagelijkse export mislukt: {error}")
        finally:
            self.schedule_daily_export()

    def export_top_ten_to_excel(self, export_date: date) -> Path:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ModuleNotFoundError as error:
            raise RuntimeError("Installeer openpyxl met: py -m pip install openpyxl") from error
        scores = self.read_scores()
        scores.sort(key=lambda entry: entry.get("max_db", 0), reverse=True)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Top 10"
        sheet.append(["MONSTER ENERGY SCREAM CHALLENGE"])
        sheet.merge_cells("A1:C1")
        sheet["A1"].font = Font(bold=True, size=16, color="3CD070")
        sheet["A1"].fill = PatternFill("solid", fgColor="111111")
        sheet["A1"].alignment = Alignment(horizontal="center")
        sheet.append([f"Dagelijkse Top 10 — {export_date.isoformat()}"])
        sheet.merge_cells("A2:C2")
        sheet["A2"].alignment = Alignment(horizontal="center")
        sheet.append([])
        sheet.append(["Rank", "Naam", "Max Score (dB)"])
        for cell in sheet[4]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="267A45")
            cell.alignment = Alignment(horizontal="center")
        for rank, score in enumerate(scores[:10], start=1):
            full_name = str(score.get("name", "Onbekend")).strip()
            first_name = full_name.split()[0] if full_name else "Onbekend"
            sheet.append([rank, first_name, round(float(score.get("max_db", 0)), 1)])
        sheet.column_dimensions["A"].width = 12
        sheet.column_dimensions["B"].width = 24
        sheet.column_dimensions["C"].width = 20
        for row in sheet.iter_rows(min_row=5, max_col=3):
            for cell in row:
                cell.alignment = Alignment(horizontal="center")
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = EXPORT_DIR / f"top_10_{export_date.isoformat()}.xlsx"
        workbook.save(output_file)
        return output_file

    def closeEvent(self, event) -> None:
        self.measurement_timer.stop()
        self.daily_export_timer.stop()
        self.audio.stop()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SoundboardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
