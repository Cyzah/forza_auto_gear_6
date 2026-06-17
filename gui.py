import os
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
    bin_dir = os.path.join(app_dir, '_bin')
    if os.path.isdir(bin_dir):
        os.add_dll_directory(bin_dir)

from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QPlainTextEdit, QCheckBox, QComboBox,
    QGraphicsDropShadowEffect,
)
import matplotlib.colors as mcolors

CHECKBOX_STYLE = """
    QCheckBox { font-size: 16px; margin: 0px; }
    QCheckBox::indicator { width: 16px; height: 16px; }
    QCheckBox::indicator:hover { border: 1px solid #4ade80; }
"""


def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_icon_path():
    return os.path.join(_get_app_dir(), 'icon', '3.ico')
from pynput.keyboard import Listener

import constants
import helper
from forza import Forza
from logger import Logger, TextHandler

warnings.filterwarnings("ignore", category=UserWarning)

STYLESHEET = """
QMainWindow { background-color: #1a1a2e; }
QFrame#panel {
    background-color: #16213e; border: 1px solid #0f3460; border-radius: 10px;
}
QLabel { color: #e0e0e0; background: transparent; }
QLabel#small-label { color: #a0a0b0; font-size: 14px; }
QPushButton#action-btn {
    background-color: #0f3460; color: #e0e0e0; border: 1px solid #1a1a4e;
    border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: bold;
    min-height: 28px;
}
QPushButton#action-btn:hover { background-color: #4ade80; border-color: #4ade80; color: #ffffff; }
QPushButton#action-btn:pressed { background-color: #c81e45; }
QPushButton#small-btn {
    background-color: #0f3460; color: #e0e0e0; border: 1px solid #1a1a4e;
    border-radius: 4px; padding: 3px 8px; font-size: 11px;
}
QPushButton#small-btn:hover { background-color: #4ade80; border-color: #4ade80; }
QCheckBox { color: #e0e0e0; spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 2px solid #0f3460;
    border-radius: 4px; background-color: #1a1a2e;
}
QCheckBox::indicator:checked { background-color: #4ade80; border-color: #4ade80; }
QComboBox {
    background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #0f3460;
    border-radius: 4px; padding: 4px 8px; min-height: 22px;
}
QComboBox::drop-down {
    subcontrol-origin: margin; subcontrol-position: center right;
    width: 24px; border: none;
}
QComboBox QAbstractItemView {
    background-color: #1a1a2e; color: #e0e0e0;
    border: 1px solid #0f3460;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 6px 12px; min-height: 24px;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #0f3460;
}
QTreeWidget {
    background-color: #1a1a2e; color: #e0e0e0; border: none;
    font-size: 13px; outline: none;
}
QTreeWidget::item { padding: 2px 0; border-bottom: 1px solid #0f346020; }
QTreeWidget::item:selected { background-color: #0f3460; color: #ffffff; }
QHeaderView::section {
    background-color: #0f3460; color: #e0e0e0; border: none; border-right: 1px solid #1a1a2e;
    padding: 4px; font-weight: bold; font-size: 13px;
    qproperty-alignment: AlignCenter;
}
QPlainTextEdit {
    background-color: #0d1117; color: #e0e0e0; border: none;
    font-family: 'Consolas', 'Courier New', monospace; font-size: 13px;
    selection-background-color: #0f3460;
}
QScrollBar:vertical { background-color: #1a1a2e; width: 8px; margin: 0; }
QScrollBar::handle:vertical {
    background-color: #0f3460; min-height: 30px; border-radius: 4px;
}
QScrollBar::handle:vertical:hover { background-color: #4ade80; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 8px; }
QScrollBar::handle:horizontal { background-color: #0f3460; border-radius: 4px; }
"""


def _make_panel(parent=None):
    frame = QFrame(parent)
    frame.setObjectName("panel")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(16)
    shadow.setXOffset(0)
    shadow.setYOffset(2)
    shadow.setColor(QColor(0, 0, 0, 80))
    frame.setGraphicsEffect(shadow)
    return frame


class PerfCardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 220)
        self._car_id = "None"
        self._car_perf = 0
        self._car_class_idx = 8
        self._drivetrain = "N"
        self._accel = "0%"
        self._brake = "0%"
        self._clutch = "0%"
        self._lang = 0
        self._tire_colors = {pos: QColor(constants.background_color) for pos in ("FL", "FR", "RL", "RR")}
        self._slip_labels = {pos: "" for pos in ("FL", "FR", "RL", "RR")}
        self._tire_cmap = mcolors.LinearSegmentedColormap.from_list("", [(0, "green"), (1, "red")])
        self._init_fonts()

    def _init_fonts(self):
        self._fonts = {
            'label_bold': QFont("SimHei", 14, QFont.Weight.Bold),
            'value_large': QFont("Segoe UI", 24, QFont.Weight.Bold),
            'badge': QFont("Segoe UI", 12, QFont.Weight.Bold),
            'item_label': QFont("Segoe UI", 12),
            'item_value': QFont("Segoe UI", 20, QFont.Weight.Bold),
            'tire_pos': QFont("SimHei", 10, QFont.Weight.Bold),
            'tire_slip': QFont("Consolas", 9),
            'tire_title': QFont("SimHei", 14, QFont.Weight.Bold),
        }

    def update_info(self, car_id, car_perf, car_class_idx, drivetrain, accel, brake, clutch="0%"):
        self._car_id = str(car_id)
        self._car_perf = car_perf
        self._car_class_idx = min(car_class_idx, 8)
        self._drivetrain = drivetrain
        self._accel = accel
        self._brake = brake
        self._clutch = clutch
        self.update()

    def reset_info(self):
        self._car_id = "None"
        self._car_perf = 0
        self._car_class_idx = 8
        self._drivetrain = "N"
        self._accel = "0%"
        self._brake = "0%"
        self.update()

    def set_tire_slip(self, position, slip_ratio):
        val = abs(slip_ratio) if abs(slip_ratio) < 1 else 1
        norm = val / 0.8 * 0.5 if val < 0.8 else (1 - val) / 0.2 * 0.5 + 0.5
        norm = max(0, min(1, norm))
        color = self._tire_cmap(norm)
        self._tire_colors[position] = QColor(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self._slip_labels[position] = f"{val:.0%}"
        self.update()

    def reset_tires(self):
        for pos in self._tire_colors:
            self._tire_colors[pos] = QColor(constants.background_color)
            self._slip_labels[pos] = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = int(w * 0.06)
        fm = painter.fontMetrics()

        # Top: Car ID (left) + Drivetrain (right)
        painter.setPen(QColor(constants.text_secondary))
        painter.setFont(self._fonts['label_bold'])
        painter.drawText(pad, int(h * 0.06), 240, 24, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, constants.car_id[self._lang])
        painter.setPen(QColor(constants.text_color))
        painter.setFont(self._fonts['value_large'])
        painter.drawText(pad, int(h * 0.06) + 24, 300, 42, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self._car_id)

        painter.setPen(QColor(constants.text_secondary))
        painter.setFont(self._fonts['label_bold'])
        painter.drawText(pad, int(h * 0.06), w - pad * 2, 24, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, constants.car_drivetrain[self._lang])
        painter.setPen(QColor(constants.text_color))
        painter.setFont(self._fonts['value_large'])
        painter.drawText(pad, int(h * 0.06) + 24, w - pad * 2, 42, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, self._drivetrain)

        # Middle: Class badge + Perf index
        row2_y = int(h * 0.06) + 66 + 4
        class_color = QColor(constants.car_class_color[self._car_class_idx])
        class_label = constants.car_class_list[self._car_class_idx]
        badge_w = max(50, fm.boundingRect(class_label).width() + 16)
        badge_h = 26
        badge_path = QPainterPath()
        badge_path.addRoundedRect(pad, row2_y, badge_w, badge_h, 5, 5)
        painter.setBrush(QBrush(class_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(badge_path)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(self._fonts['badge'])
        painter.drawText(pad, row2_y, badge_w, badge_h, Qt.AlignmentFlag.AlignCenter, class_label)

        perf_str = str(self._car_perf)
        perf_w = max(42, fm.horizontalAdvance(perf_str) + 12)
        px = pad + badge_w + 6
        perf_path = QPainterPath()
        perf_path.addRoundedRect(px, row2_y, perf_w, badge_h, 5, 5)
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(perf_path)
        painter.setPen(QColor(constants.background_color))
        painter.setFont(self._fonts['badge'])
        painter.drawText(px, row2_y, perf_w, badge_h, Qt.AlignmentFlag.AlignCenter, perf_str)

        # Divider
        div_y = row2_y + badge_h + 16
        painter.setPen(QPen(QColor(constants.accent_color), 1))
        painter.drawLine(pad, div_y, w - pad, div_y)

        inner_pad = int(w * 0.16)
        total_w = w - inner_pad * 2
        half_w = int(total_w * 0.6)
        gap = max(12, int(h * 0.015))
        items = [
            (constants.accel_txt[self._lang], self._accel, QColor("#4ade80"), QColor("#1a2e1a")),
            (constants.brake_txt[self._lang], self._brake, QColor(constants.highlight_color), QColor("#2e1a1a")),
            (constants.clutch_status_txt[self._lang], self._clutch, QColor("#60a5fa"), QColor("#1a1a2e")),
        ]
        block_y = div_y + int(h * 0.03)
        block_x = inner_pad
        block_h = (h - block_y - int(h * 0.06) - gap * 2) // 3
        block_w = half_w - gap
        bar_h = 6
        bar_r = 3

        for i, (label, value, color, bg_bar) in enumerate(items):
            by = block_y + i * (block_h + gap)
            bp = QPainterPath()
            bp.addRoundedRect(block_x, by, block_w, block_h, 6, 6)
            painter.setBrush(QBrush(QColor(constants.background_color)))
            painter.setPen(QPen(QColor(constants.accent_color), 1))
            painter.drawPath(bp)
            painter.setPen(QColor(constants.text_secondary))
            painter.setFont(self._fonts['item_label'])
            painter.drawText(block_x + 10, by + 6, block_w - 20, 18, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, label)
            painter.setPen(color)
            painter.setFont(self._fonts['item_value'])
            painter.drawText(block_x + 10, by + 24, block_w - 20, 32, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, value)
            bar_x = block_x + 10
            bar_y = by + block_h - 12
            bar_w = block_w - 20
            bg_path = QPainterPath()
            bg_path.addRoundedRect(bar_x, bar_y, bar_w, bar_h, bar_r, bar_r)
            painter.setBrush(QBrush(bg_bar))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(bg_path)
            try:
                pct = float(value.replace('%', '')) / 100.0
            except (ValueError, AttributeError):
                pct = 0.0
            fill_w = max(0, int(bar_w * min(pct, 1.0)))
            if fill_w > 0:
                fp = QPainterPath()
                fp.addRoundedRect(bar_x, bar_y, fill_w, bar_h, bar_r, bar_r)
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPath(fp)

        tire_x = inner_pad + half_w + gap // 2
        tire_w_area = total_w - half_w - gap
        tire_y = block_y
        tire_h = h - tire_y - int(h * 0.06)
        tire_gap = 10

        painter.setPen(QColor(constants.text_color))
        painter.setFont(self._fonts['tire_title'])
        painter.drawText(tire_x, tire_y, tire_w_area, 22, Qt.AlignmentFlag.AlignCenter, constants.tire_information_txt[self._lang])

        tire_title_h = 32
        tire_start_y = tire_y + tire_title_h
        tire_grid_h = tire_h - tire_title_h
        tw = (tire_w_area - tire_gap) / 2
        th = (tire_grid_h - tire_gap) / 2
        start_x = tire_x + (tire_w_area - tw * 2 - tire_gap) // 2

        positions = [
            ("FL", start_x, tire_start_y),
            ("FR", start_x + tw + tire_gap, tire_start_y),
            ("RL", start_x, tire_start_y + th + tire_gap),
            ("RR", start_x + tw + tire_gap, tire_start_y + th + tire_gap),
        ]
        for pos, x, y in positions:
            color_t = self._tire_colors.get(pos, QColor(constants.background_color))
            path = QPainterPath()
            path.addRoundedRect(x, y, tw, th, 8, 8)
            painter.setBrush(QBrush(color_t))
            painter.setPen(QPen(QColor(constants.text_secondary), 1))
            painter.drawPath(path)
            painter.setPen(QColor(255, 255, 255) if color_t.lightness() > 80 else QColor(240, 240, 240))
            painter.setFont(self._fonts['tire_pos'])
            painter.drawText(int(x), int(y), int(tw), int(th * 0.6), Qt.AlignmentFlag.AlignCenter, pos)
            slip_text = self._slip_labels.get(pos, "")
            if slip_text:
                painter.setFont(self._fonts['tire_slip'])
                painter.drawText(int(x), int(y + th * 0.55), int(tw), int(th * 0.4), Qt.AlignmentFlag.AlignCenter, slip_text)



class LiveDataWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 320)
        self._gear = "-"
        self._speed = "0.0"
        self._rpm = "0"
        self._lang = 0
        self._last_valid_gear = "-"
        self._init_fonts()

    def _init_fonts(self):
        self._fonts = {
            'title': QFont("SimHei", 16, QFont.Weight.Bold),
            'gear': QFont("Segoe UI", 72, QFont.Weight.Bold),
            'speed_value': QFont("Segoe UI", 32, QFont.Weight.Bold),
            'speed_unit': QFont("SimHei", 14),
            'rpm_value': QFont("Segoe UI", 28, QFont.Weight.Bold),
            'rpm_unit': QFont("SimHei", 14),
        }

    def update_data(self, gear, speed_kmh, rpm):
        if isinstance(gear, int) and 1 <= gear <= 10:
            self._last_valid_gear = str(gear)
        self._gear = self._last_valid_gear
        self._speed = f"{speed_kmh:.1f}"
        self._rpm = f"{rpm:.0f}"
        self.update()

    def reset_data(self):
        self._gear = "-"
        self._last_valid_gear = "-"
        self._speed = "0.0"
        self._rpm = "0"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        painter.setPen(QColor(constants.text_secondary))
        painter.setFont(self._fonts['title'])
        title = constants.live_data_txt[self._lang]
        painter.drawText(0, 16, w, 30, Qt.AlignmentFlag.AlignCenter, title)

        painter.setPen(QColor(constants.text_color))
        painter.setFont(self._fonts['gear'])
        painter.drawText(0, 60, w, 90, Qt.AlignmentFlag.AlignCenter, self._gear)

        painter.setPen(QColor("#4ade80"))
        painter.setFont(self._fonts['speed_value'])
        painter.drawText(0, 160, w, 40, Qt.AlignmentFlag.AlignCenter, self._speed)
        painter.setPen(QColor(constants.text_secondary))
        painter.setFont(self._fonts['speed_unit'])
        unit_speed = "km/h" if self._lang == 0 else "公里/小时"
        painter.drawText(0, 200, w, 22, Qt.AlignmentFlag.AlignCenter, unit_speed)

        painter.setPen(QColor("#60a5fa"))
        painter.setFont(self._fonts['rpm_value'])
        painter.drawText(0, 240, w, 36, Qt.AlignmentFlag.AlignCenter, self._rpm)
        painter.setPen(QColor(constants.text_secondary))
        painter.setFont(self._fonts['rpm_unit'])
        painter.drawText(0, 280, w, 22, Qt.AlignmentFlag.AlignCenter, "RPM")

class MainWindow(QMainWindow):
    _update_car_signal = Signal(object)
    _update_tree_signal = Signal()
    _clutch_change_signal = Signal(bool)
    _exit_signal = Signal()
    _collect_signal = Signal()
    _analysis_signal = Signal()
    _run_signal = Signal()
    _pause_signal = Signal()

    def __init__(self):
        super().__init__()
        self._update_car_signal.connect(self._on_update_car)
        self._update_tree_signal.connect(self._on_update_tree)
        self._clutch_change_signal.connect(self._on_clutch_change_ui)
        self._exit_signal.connect(self._exit_handler)
        self._collect_signal.connect(self._collect_data_handler)
        self._analysis_signal.connect(self._analysis_handler)
        self._run_signal.connect(self._run_handler)
        self._pause_signal.connect(self._pause_handler)
        self.language = helper.get_sys_lang()
        self._texts = {}
        self._init_texts()
        self.threadPool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="exec")
        self.forza5 = Forza(
            self.threadPool, None,
            constants.packet_format, enable_clutch=constants.enable_clutch,
        )
        self._apply_text(self.language)
        self.listener = Listener(on_press=self._on_press)
        self.setWindowTitle("Forza Horizon 6: Auto Gear Shifting")
        self.setMinimumSize(1200, 800)
        self.resize(1380, 950)
        icon_path = _get_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # Set dark title bar on Windows 10/11
        try:
            import ctypes
            hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
            # Set title bar background color to match window
            DWMWA_CAPTION_COLOR = 35
            caption_color = 0x2e1a1a  # #1a1a2e in BGR
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR,
                ctypes.byref(ctypes.c_int(caption_color)), ctypes.sizeof(ctypes.c_int)
            )
            # Set title bar text color to white
            DWMWA_TEXT_COLOR = 36
            white = 0x00FFFFFF
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_TEXT_COLOR,
                ctypes.byref(ctypes.c_int(white)), ctypes.sizeof(ctypes.c_int)
            )
            # Set window border color to match dark theme
            DWMWA_BORDER_COLOR = 34
            border_color = 0x2e1a1a  # #1a1a2e in BGR
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_BORDER_COLOR,
                ctypes.byref(ctypes.c_int(border_color)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._build_buttons()
        self.logger.info('Forza Horizon 6: Auto Gear Shifting Started!!!')
        self.listener.start()
        self._start_bg_listener()

    def _init_texts(self):
        attr_map = {
            'select_language': 'select_language_txt', 'language': 'language_txt',
            'clutch_shortcut': 'clutch_shortcut_txt', 'upshift_shortcut': 'upshift_shortcut_txt',
            'downshift_shortcut': 'downshift_shortcut_txt', 'clutch': 'clutch_txt',
            'farm': 'farm_txt', 'offroad_rally': 'offroad_rally_txt',
            'car_id': 'car_id', 'car_perf': 'car_perf', 'car_drivetrain': 'car_drivetrain',
            'tire_information': 'tire_information_txt', 'accel': 'accel_txt',
            'brake': 'brake_txt', 'shift_point': 'shift_point_txt',
            'tree_value': 'tree_value_txt', 'speed': 'speed_txt', 'rpm': 'rpm_txt',
            'collect_button': 'collect_button_txt', 'analysis_button': 'analysis_button_txt',
            'run_button': 'run_button_txt', 'pause_button': 'pause_button_txt',
            'exit_button': 'exit_button_txt', 'clear_log': 'clear_log_txt',
            'save_shift': 'save_shift_txt',
            'program_info': 'program_info_txt',
            'live_data': 'live_data_txt',
        }
        for k, v in attr_map.items():
            self._texts[k] = getattr(constants, v, k)

    def _apply_text(self, lang_idx):
        self._lang_idx = lang_idx
        for k in list(self._texts.keys()):
            attr_name = k + '_txt'
            vals = getattr(constants, attr_name, None)
            if vals is None:
                vals = self._texts.get(k)
            if isinstance(vals, (list, tuple)) and len(vals) > lang_idx:
                self._texts[k] = vals[lang_idx]
        self._update_dynamic_labels()

    def _update_dynamic_labels(self):
        label_map = {
            '_lbl_select_lang': 'select_language',
            '_chk_clutch': 'clutch',
            '_chk_farm': 'farm',
            '_chk_offroad': 'offroad_rally',
        }
        for attr, key in label_map.items():
            if hasattr(self, attr):
                getattr(self, attr).setText(self._texts.get(key, ''))
        # Update IP/Port labels on language change
        if hasattr(self, '_lbl_ip'):
            ip_txt = "IP地址:" if self._lang_idx == 1 else "IP:"
            self._lbl_ip.setText(f"{ip_txt} {self.forza5.ip}")
        if hasattr(self, '_lbl_port'):
            port_txt = "IP端口:" if self._lang_idx == 1 else "Port:"
            self._lbl_port.setText(f"{port_txt} {self.forza5.port}")
        btn_shortcuts = {
            '_btn_collect': ('collect_button', 'F10'),
            '_btn_analysis': ('analysis_button', 'F8'),
            '_btn_run': ('run_button', 'F7'),
            '_btn_pause': ('pause_button', 'Pause'),
            '_btn_exit': ('exit_button', 'End'),
        }
        for attr, (key, shortcut) in btn_shortcuts.items():
            if hasattr(self, attr):
                getattr(self, attr).setText(f"{self._texts.get(key, '')}  [{shortcut}]")
        # Update shortcut hint labels
        hint_map = {
            '_clutch_hint': 'clutch_shortcut',
            '_upshift_hint': 'upshift_shortcut',
            '_downshift_hint': 'downshift_shortcut',
        }
        keys_map = {
            '_clutch_hint': self.forza5.clutch,
            '_upshift_hint': self.forza5.upshift,
            '_downshift_hint': self.forza5.downshift,
        }
        for attr, key in hint_map.items():
            if hasattr(self, attr):
                getattr(self, attr).setText(f'{self._texts.get(key, "")} {keys_map[attr].upper()}')
        # Update program info
        if hasattr(self, '_info_text'):
            self._info_text.setText(self._texts.get('program_info', ''))
        # Update perf card language
        if hasattr(self, '_perf_card'):
            self._perf_card._lang = self._lang_idx
            self._perf_card.repaint()
        # Update live data language
        if hasattr(self, '_live_data'):
            self._live_data._lang = self._lang_idx
            self._live_data.update()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QGridLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Settings panel (col 0, row 0)
        settings_panel = _make_panel()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setSpacing(10)
        settings_layout.setContentsMargins(12, 12, 12, 12)

        lang_row = QHBoxLayout()
        self._lbl_select_lang = QLabel(self._texts["select_language"])
        self._lbl_select_lang.setObjectName("small-label")
        lang_row.addWidget(self._lbl_select_lang)
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(constants.language_txt)
        self._lang_combo.setCurrentIndex(self.language)
        self._lang_combo.currentIndexChanged.connect(self._on_language_change)
        self._lang_combo.setMaxVisibleItems(5)
        lang_row.addWidget(self._lang_combo)
        settings_layout.addLayout(lang_row)

        ip_txt = "IP地址:" if self.language == 1 else "IP:"
        self._lbl_ip = QLabel(f"{ip_txt} {self.forza5.ip}")
        self._lbl_ip.setStyleSheet("color: #c0c0d0; font-size: 18px; font-weight: bold; background: transparent;")
        settings_layout.addWidget(self._lbl_ip)
        port_txt = "IP端口:" if self.language == 1 else "Port:"
        self._lbl_port = QLabel(f"{port_txt} {self.forza5.port}")
        self._lbl_port.setStyleSheet("color: #c0c0d0; font-size: 18px; font-weight: bold; background: transparent;")
        settings_layout.addWidget(self._lbl_port)

        # Shortcut hints (read-only display)
        hint_style = "color: #c0c0d0; font-size: 18px; font-weight: bold; background: transparent;"
        self._upshift_hint = QLabel(f'{self._texts["upshift_shortcut"]} {self.forza5.upshift.upper()}')
        self._upshift_hint.setStyleSheet(hint_style)
        settings_layout.addWidget(self._upshift_hint)
        self._downshift_hint = QLabel(f'{self._texts["downshift_shortcut"]} {self.forza5.downshift.upper()}')
        self._downshift_hint.setStyleSheet(hint_style)
        settings_layout.addWidget(self._downshift_hint)
        self._clutch_hint = QLabel(f'{self._texts["clutch_shortcut"]} {self.forza5.clutch.upper()}')
        self._clutch_hint.setStyleSheet(hint_style)
        settings_layout.addWidget(self._clutch_hint)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #0f3460;")
        settings_layout.addWidget(sep1)

        self._chk_clutch = QCheckBox(self._texts["clutch"])
        self._chk_clutch.setChecked(self.forza5.enable_clutch)
        self._chk_clutch.setStyleSheet(CHECKBOX_STYLE)
        self._chk_clutch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chk_clutch.setToolTip("启用离合器模拟，换挡时自动控制离合" if self.language == 1 else "Enable clutch simulation, auto control clutch during shift")
        self._chk_clutch.toggled.connect(lambda v: setattr(self.forza5, 'enable_clutch', v))
        settings_layout.addWidget(self._chk_clutch, alignment=Qt.AlignmentFlag.AlignLeft)

        self._chk_farm = QCheckBox(self._texts["farm"])
        self._chk_farm.setChecked(self.forza5.farming)
        self._chk_farm.setStyleSheet(CHECKBOX_STYLE)
        self._chk_farm.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chk_farm.setToolTip("开启刷图模式，自动按住油门并处理卡住情况" if self.language == 1 else "Enable farming mode, auto hold throttle and handle stuck situations")
        self._chk_farm.toggled.connect(lambda v: setattr(self.forza5, 'farming', v))
        settings_layout.addWidget(self._chk_farm, alignment=Qt.AlignmentFlag.AlignLeft)

        self._chk_offroad = QCheckBox(self._texts["offroad_rally"])
        self._chk_offroad.setChecked(self.forza5.shift_point_factor == constants.offroad_rally_shift_factor)
        self._chk_offroad.setStyleSheet(CHECKBOX_STYLE)
        self._chk_offroad.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chk_offroad.setToolTip("越野/拉力模式，提前换挡防止打滑" if self.language == 1 else "Offroad/Rally mode, shift earlier to prevent wheel slip")
        self._chk_offroad.toggled.connect(
            lambda v: setattr(self.forza5, 'shift_point_factor',
                              constants.offroad_rally_shift_factor if v else constants.shift_factor)
        )
        settings_layout.addWidget(self._chk_offroad, alignment=Qt.AlignmentFlag.AlignLeft)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #0f3460;")
        settings_layout.addWidget(sep2)

        self._info_text = QLabel(self._texts.get('program_info', ''))
        self._info_text.setWordWrap(True)
        self._info_text.setObjectName("small-label")
        settings_layout.addWidget(self._info_text)
        settings_layout.addStretch()
        link_label = QLabel()
        link_label.setObjectName("small-label")
        link_label.setOpenExternalLinks(True)
        link_label.setText('<a href="https://github.com/Cyzah/forza_auto_gear_6" style="color:#4ade80;">GitHub Repository</a>')
        settings_layout.addWidget(link_label)
        settings_panel.setFixedWidth(220)
        main_layout.addWidget(settings_panel, 0, 0)

        # Car perf panel (col 1, row 0)
        perf_panel = _make_panel()
        perf_layout = QVBoxLayout(perf_panel)
        perf_layout.setContentsMargins(0, 0, 0, 0)
        perf_layout.setSpacing(0)
        self._perf_card = PerfCardWidget()
        self._perf_card._lang = self._lang_idx
        self._perf_card.repaint()
        perf_layout.addWidget(self._perf_card)

        main_layout.addWidget(perf_panel, 0, 1)

        # Shift point tree (col 2, row 0)
        shift_panel = _make_panel()
        shift_layout = QVBoxLayout(shift_panel)
        shift_layout.setContentsMargins(4, 4, 4, 4)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels([self._texts['shift_point'], self._texts['tree_value']])
        self._tree.setColumnCount(2)
        self._tree.setRootIsDecorated(True)
        self._tree.setEditTriggers(QTreeWidget.EditTrigger.DoubleClicked | QTreeWidget.EditTrigger.SelectedClicked)
        self._tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._tree.headerItem().setTextAlignment(0, Qt.AlignmentFlag.AlignHCenter)
        self._tree.headerItem().setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
        self._speed_parent = QTreeWidgetItem(self._tree)
        self._speed_parent.setText(0, self._texts['speed'])
        self._speed_parent.setExpanded(True)
        self._speed_parent.setFont(0, QFont("SimHei", 11, QFont.Weight.Bold))
        sh = self._speed_parent.sizeHint(0)
        self._speed_parent.setSizeHint(0, QSize(sh.width(), sh.height() + 1))
        self._rpm_parent = QTreeWidgetItem(self._tree)
        self._rpm_parent.setText(0, self._texts['rpm'])
        self._rpm_parent.setExpanded(True)
        self._rpm_parent.setFont(0, QFont("SimHei", 11, QFont.Weight.Bold))
        sh = self._rpm_parent.sizeHint(0)
        self._rpm_parent.setSizeHint(0, QSize(sh.width(), sh.height() + 1))
        self._speed_items = {}
        self._rpm_items = {}
        for i in range(1, 11):
            spd = QTreeWidgetItem(self._speed_parent)
            spd.setText(0, str(i)); spd.setText(1, "-")
            spd.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            spd.setFlags(spd.flags() | Qt.ItemFlag.ItemIsEditable)
            self._speed_items[i] = spd
            rpm = QTreeWidgetItem(self._rpm_parent)
            rpm.setText(0, str(i)); rpm.setText(1, "-")
            rpm.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            rpm.setFlags(rpm.flags() | Qt.ItemFlag.ItemIsEditable)
            self._rpm_items[i] = rpm
        shift_layout.addWidget(self._tree)

        self._btn_save_shift = QPushButton(self._texts['save_shift'])
        self._btn_save_shift.setObjectName("action-btn")
        self._btn_save_shift.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save_shift.clicked.connect(self._save_shift_points)
        shift_layout.addWidget(self._btn_save_shift)

        main_layout.addWidget(shift_panel, 0, 2)

        # Buttons (col 0, row 1)
        self._btn_frame = _make_panel()
        self._btn_layout = QVBoxLayout(self._btn_frame)
        self._btn_layout.setSpacing(6)
        self._btn_layout.setContentsMargins(12, 12, 12, 12)
        self._btn_frame.setFixedWidth(220)
        main_layout.addWidget(self._btn_frame, 1, 0)

        # Log panel (col 1, row 1)
        log_panel = _make_panel()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(4, 4, 4, 4)
        log_layout.setSpacing(4)
        log_header = QHBoxLayout()
        log_header.addStretch()
        self._btn_clear_log = QPushButton(self._texts["clear_log"])
        self._btn_clear_log.setObjectName("small-btn")
        self._btn_clear_log.clicked.connect(lambda: self._log_text.clear())
        log_header.addWidget(self._btn_clear_log)
        log_layout.addLayout(log_header)
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        log_layout.addWidget(self._log_text)
        log_handler = TextHandler(self._log_text)
        self.logger = Logger(log_handler)('ForzaHorizon5')
        self.forza5.logger = self.logger
        main_layout.addWidget(log_panel, 1, 1)

        # Live data panel (col 2, row 1)
        live_panel = _make_panel()
        live_layout = QVBoxLayout(live_panel)
        live_layout.setContentsMargins(0, 0, 0, 0)
        self._live_data = LiveDataWidget()
        self._live_data._lang = self._lang_idx
        live_layout.addWidget(self._live_data)
        main_layout.addWidget(live_panel, 1, 2)

        main_layout.setRowStretch(0, 3)
        main_layout.setRowStretch(1, 2)
        main_layout.setColumnStretch(0, 0)
        main_layout.setColumnStretch(1, 5)
        main_layout.setColumnStretch(2, 2)


        self._update_dynamic_labels()

    def _build_buttons(self):
        buttons = [
            (self._texts['collect_button'], self._collect_data_handler, 'F10'),
            (self._texts['analysis_button'], self._analysis_handler, 'F8'),
            (self._texts['run_button'], self._run_handler, 'F7'),
            (self._texts['pause_button'], self._pause_handler, 'Pause'),
            (self._texts['exit_button'], self._exit_handler, 'End'),
        ]
        self._action_btns = []
        for text, handler, shortcut in buttons:
            btn = QPushButton(f"{text}  [{shortcut}]")
            btn.setObjectName("action-btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Keyboard shortcut: {shortcut}")
            btn.clicked.connect(handler)
            self._btn_layout.addWidget(btn)
            self._action_btns.append(btn)
        self._btn_collect = self._action_btns[0]
        self._btn_analysis = self._action_btns[1]
        self._btn_run = self._action_btns[2]
        self._btn_pause = self._action_btns[3]
        self._btn_exit = self._action_btns[4]
        self._btn_layout.addStretch()

    def _start_bg_listener(self):
        self._bg_listener_stop = threading.Event()
        try:
            helper.create_socket(self.forza5)
        except Exception:
            return

        def _listen():
            while not self._bg_listener_stop.is_set():
                try:
                    fdp = helper.nextFdp(self.forza5.server_socket, self.forza5.packet_format)
                    if fdp is not None and fdp.car_ordinal > 0:
                        self.forza5._latest_fdp = fdp
                        self.forza5._fdp_event.set()
                        self._update_car_signal.emit(fdp)
                except Exception:
                    if not self._bg_listener_stop.is_set():
                        pass

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

    def _on_language_change(self, index):
        self.language = index
        self._apply_text(index)
        self._tree.setHeaderLabels([self._texts['shift_point'], self._texts['tree_value']])
        self._perf_card._lang = self._lang_idx

    def _on_clutch_change(self, pressed: bool):
        self._clutch_change_signal.emit(pressed)

    def _on_clutch_change_ui(self, pressed: bool):
        clutch_val = 255 if pressed else 0
        clutch_pct = f"{round(clutch_val / 255 * 100, 1)}%"
        self._perf_card._clutch = clutch_pct
        self._perf_card.repaint()

    def _collect_data_handler(self):
        if self.forza5.isRunning:
            self.logger.info('stopping gear test')
            def stopping():
                self.forza5.isRunning = False
                self._update_car_signal.emit(None)
            self.threadPool.submit(stopping)
        else:
            self.logger.info('starting gear test')
            def starting():
                self.forza5.isRunning = True
                self.forza5.on_clutch_change = self._on_clutch_change
                self.forza5.test_gear(self._emit_car_update)
            self.threadPool.submit(starting)

    def _analysis_handler(self):
        if len(self.forza5.records) <= 0:
            self.logger.info(f'load config {constants.example_car_ordinal}.json for analysis as an example')
            helper.load_config(self.forza5, os.path.join(constants.root_path, 'example', f'{constants.example_car_ordinal}.json'))
        self.logger.info('Analysis')

        def run_analysis():
            self.forza5.analyze_data()
            self._update_tree_signal.emit()

        self.threadPool.submit(run_analysis)

    def _run_handler(self):
        if self.forza5.isRunning:
            self.forza5.logger.info('stopping auto gear')
            def stopping():
                self.forza5.isRunning = False
                self._update_car_signal.emit(None)
            self.threadPool.submit(stopping)
        else:
            self.forza5.logger.info('starting auto gear')
            def starting():
                self.forza5.isRunning = True
                self.forza5.on_clutch_change = self._on_clutch_change
                self.forza5.run(lambda: self._update_tree_signal.emit(), self._emit_car_update)
            self.threadPool.submit(starting)

    def _pause_handler(self):
        old_listener = self.listener
        self.listener = None
        if old_listener is not None:
            old_listener.stop()
            if hasattr(old_listener, '_thread') and old_listener._thread.is_alive():
                old_listener._thread.join(timeout=0.5)
        self.forza5.isRunning = False
        if self.threadPool is not None:
            self.threadPool.shutdown(wait=False)
        self._perf_card.reset_info()
        self._perf_card.reset_tires()
        self.threadPool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="exec")
        self.forza5.threadPool = self.threadPool
        self.listener = Listener(on_press=self._on_press)
        self.listener.start()
        self.forza5.logger.info('stopped')

    def _exit_handler(self):
        self._bg_listener_stop.set()
        _shutdown(self.forza5, self.threadPool, self.listener)
        helper.close_socket(self.forza5)
        helper.dump_settings(self.forza5)
        self.forza5.logger.info('bye~')
        QApplication.quit()

    def _on_press(self, key):
        try:
            if key == constants.collect_data:
                self._collect_signal.emit()
            elif key == constants.analysis:
                self._analysis_signal.emit()
            elif key == constants.auto_shift:
                self._run_signal.emit()
            elif key == constants.stop:
                self._pause_signal.emit()
            elif key == constants.close:
                self._exit_signal.emit()
        except BaseException as e:
            self.forza5.logger.exception(e)

    def _emit_car_update(self, fdp):
        self._update_car_signal.emit(fdp)

    @Slot(object)
    def _on_update_car(self, fdp):
        if fdp is None:
            self._perf_card.reset_info()
            self._perf_card.reset_tires()
            self._live_data.reset_data()
            return
        # always update center card when FDP data is available
        drivetrain_text = constants.car_drivetrain_list[fdp.drivetrain_type][self._lang_idx]
        accel_pct = f"{round(fdp.accel / 255 * 100, 1)}%"
        brake_pct = f"{round(fdp.brake / 255 * 100, 1)}%"
        clutch_pct = f"{round(fdp.clutch / 255 * 100, 1)}%"
        self._perf_card.update_info(fdp.car_ordinal, fdp.car_performance_index, fdp.car_class, drivetrain_text, accel_pct, brake_pct, clutch_pct)
        self._perf_card.set_tire_slip('FL', fdp.tire_combined_slip_FL)
        self._perf_card.set_tire_slip('FR', fdp.tire_combined_slip_FR)
        self._perf_card.set_tire_slip('RL', fdp.tire_combined_slip_RL)
        self._perf_card.set_tire_slip('RR', fdp.tire_combined_slip_RR)
        self._live_data.update_data(fdp.gear, fdp.speed * 3.6, fdp.current_engine_rpm)

    @Slot()
    def _on_update_tree(self):
        for key, value in self.forza5.shift_point.items():
            if key in self._speed_items:
                self._speed_items[key].setText(1, str(round(value['speed'], 3)))
            if key in self._rpm_items:
                self._rpm_items[key].setText(1, str(round(value['rpmo'], 3)))
        for i in range(1, 11):
            if i not in self.forza5.shift_point:
                if i in self._speed_items:
                    self._speed_items[i].setText(1, "-")
                if i in self._rpm_items:
                    self._rpm_items[i].setText(1, "-")

    def _save_shift_points(self):
        try:
            new_shift_point = {}
            for i in range(1, 11):
                speed_text = self._speed_items[i].text(1)
                rpm_text = self._rpm_items[i].text(1)
                if speed_text != "-" and rpm_text != "-":
                    try:
                        speed_val = float(speed_text)
                        rpm_val = float(rpm_text)
                        new_shift_point[i] = {'rpmo': rpm_val, 'speed': speed_val}
                    except ValueError:
                        self.logger.warning(f'Invalid shift point for gear {i}: speed={speed_text}, rpm={rpm_text}')
                        continue
            if new_shift_point:
                self.forza5.shift_point = new_shift_point
                if new_shift_point:
                    self.forza5.min_gear = min(new_shift_point.keys())
                    self.forza5.max_gear = max(new_shift_point.keys())
                helper.dump_config(self.forza5)
                self.logger.info(f'Saved shift points: {len(new_shift_point)} gears')
            else:
                self.logger.warning('No valid shift points to save')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Failed to save shift points')

    def closeEvent(self, event):
        self._bg_listener_stop.set()
        _shutdown(self.forza5, self.threadPool, self.listener)
        helper.dump_settings(self.forza5)
        helper.close_socket(self.forza5)
        event.accept()


def _shutdown(forza, threadPool, listener):
    forza.isRunning = False
    threadPool.shutdown(wait=False)
    listener.stop()


def main():
    # Set AppUserModelID before window creation so taskbar icon is correct on first launch
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ForzaHorizon6.AutoGear')
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Set application icon before window creation
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(app_dir, 'icon', '3.ico')
    app_icon = QIcon(icon_path) if os.path.exists(icon_path) else None
    if app_icon is not None:
        app.setWindowIcon(app_icon)
    window = MainWindow()
    window.show()
    if app_icon is not None:
        window.setWindowIcon(app_icon)
        app.processEvents()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
