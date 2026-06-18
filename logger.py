import logging
import os
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QPlainTextEdit

import constants

_LOG_FORMAT = '%(asctime)s.%(msecs)03d | \t %(levelname)s:\t %(message)s'
_LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'
_configured = False


class _LogSignal(QObject):
    message = Signal(str, str)


class TextHandler(logging.Handler):
    def __init__(self, text: QPlainTextEdit):
        logging.Handler.__init__(self)
        self.text = text
        self._signal_bridge = _LogSignal()
        self._signal_bridge.message.connect(self._append)
        self.text.setMaximumBlockCount(800)
        self.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))

    @Slot(str, str)
    def _append(self, msg: str, level_name: str):
        color_map = {
            'DEBUG': '#808080', 'INFO': '#e0e0e0', 'WARNING': '#fca862',
            'ERROR': '#ff3333', 'CRITICAL': '#b30000',
        }
        color = color_map.get(level_name, '#e0e0e0')
        self.text.appendHtml(f'<span style="color:{color};">{msg}</span>')

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self._signal_bridge.message.emit(msg, record.levelname)


class Logger:
    def __init__(self, custom_handler: Optional[logging.Handler] = None):
        global _configured
        root = logging.getLogger()

        if not _configured:
            log_folder = os.path.join(constants.root_path, 'log')
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)
            file_handler = logging.FileHandler(
                os.path.join(log_folder, 'forza.log'), mode='w'
            )
            file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
            file_handler.setLevel(logging.DEBUG)
            root.setLevel(logging.DEBUG)
            root.addHandler(file_handler)
            _configured = True

        if custom_handler is not None:
            custom_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
            custom_handler.setLevel(logging.INFO)
            has_custom = any(isinstance(h, type(custom_handler)) for h in root.handlers)
            if not has_custom:
                root.addHandler(custom_handler)

    def __call__(self, name: str) -> logging.Logger:
        return logging.getLogger(name)
