# codes/dialogue.py

from PySide6.QtCore import QObject, Signal, QTimer, QPropertyAnimation
from PySide6.QtWidgets import QWidget


class DialoguePlayer(QObject):
    """
    Galgame 风格对话播放器。

    状态：

        TYPING
            ↓
        COMPLETE
            ↓
        WAITING_NEXT
            ↓
        FADE_OUT
    """

    text_changed = Signal(str)
    speaking_changed = Signal(bool)
    dialogue_finished = Signal()

    def __init__(
        self,
        parent=None,
        type_interval=45,
        next_lock_ms=500,
        stay_ms=2000,
        last_stay_ms=3000,
    ):
        super().__init__(parent)

        self.type_interval = type_interval
        self.next_lock_ms = next_lock_ms
        self.stay_ms = stay_ms
        self.last_stay_ms = last_stay_ms

        self.sentences = []
        self.current_index = 0

        self.current_text = ""
        self.current_position = 0

        self.is_typing = False
        self.can_next = False

        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self._type_next_character)

        self.unlock_timer = QTimer(self)
        self.unlock_timer.setSingleShot(True)
        self.unlock_timer.timeout.connect(self._unlock_next)

        self.stay_timer = QTimer(self)
        self.stay_timer.setSingleShot(True)
        self.stay_timer.timeout.connect(self._auto_fade)

    # --------------------------------------------------------
    # 开始播放
    # --------------------------------------------------------

    def play(self, text: str):
        sentences = self._split_sentences(text)

        if not sentences:
            return

        self.sentences = sentences
        self.current_index = 0

        self._start_current_sentence()

    # --------------------------------------------------------
    # 点击对话框
    # --------------------------------------------------------

    def click(self):
        """
        用户点击对话框。

        如果正在打字：
            立即显示完整内容。

        如果已经完成：
            必须等待500ms才能进入下一句。
        """

        if self.is_typing:
            self._finish_typing()
            return

        if not self.can_next:
            return

        if self.current_index < len(self.sentences) - 1:
            self.current_index += 1
            self._start_current_sentence()
        else:
            self._fade_out()

    # --------------------------------------------------------
    # 开始当前句
    # --------------------------------------------------------

    def _start_current_sentence(self):

        self.type_timer.stop()
        self.unlock_timer.stop()
        self.stay_timer.stop()

        self.current_text = self.sentences[self.current_index]
        self.current_position = 0

        self.is_typing = True
        self.can_next = False

        self.text_changed.emit("")
        self.speaking_changed.emit(True)

        self.type_timer.start(self.type_interval)

    # --------------------------------------------------------
    # 打字机
    # --------------------------------------------------------

    def _type_next_character(self):

        if self.current_position >= len(self.current_text):
            self._finish_typing()
            return

        self.current_position += 1

        visible_text = self.current_text[:self.current_position]

        self.text_changed.emit(visible_text)

        if self.current_position >= len(self.current_text):
            self._finish_typing()

    # --------------------------------------------------------
    # 立即完成
    # --------------------------------------------------------

    def _finish_typing(self):

        if not self.is_typing:
            return

        self.type_timer.stop()

        self.current_position = len(self.current_text)

        self.text_changed.emit(self.current_text)

        self.is_typing = False

        # 角色说完
        self.speaking_changed.emit(False)

        # 防止手滑
        self.can_next = False

        self.unlock_timer.start(self.next_lock_ms)

        # 最后一句等待3秒，
        # 其它句子等待2秒
        if self.current_index >= len(self.sentences) - 1:
            self.stay_timer.start(self.last_stay_ms)
        else:
            self.stay_timer.start(self.stay_ms)

    # --------------------------------------------------------
    # 解锁下一句
    # --------------------------------------------------------

    def _unlock_next(self):
        self.can_next = True

    # --------------------------------------------------------
    # 自动淡出
    # --------------------------------------------------------

    def _auto_fade(self):

        if self.current_index >= len(self.sentences) - 1:
            self._fade_out()

    # --------------------------------------------------------
    # 淡出
    # --------------------------------------------------------

    def _fade_out(self):

        self.type_timer.stop()
        self.unlock_timer.stop()
        self.stay_timer.stop()

        self.can_next = False
        self.is_typing = False

        self.text_changed.emit("")
        self.speaking_changed.emit(False)

        self.dialogue_finished.emit()

    # --------------------------------------------------------
    # 分句
    # --------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str):

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        lines = []

        for line in text.split("\n"):
            line = line.strip()

            if line:
                lines.append(line)

        # 如果模型没有换行，则按照中文标点进行简单切句
        if len(lines) == 1:
            import re

            result = re.split(
                r"(?<=[。！？!?；;])",
                lines[0],
            )

            lines = [
                x.strip()
                for x in result
                if x.strip()
            ]

        return lines
