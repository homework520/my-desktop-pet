# codes/pet_window.py

import random


from PySide6.QtCore import (
    Qt,
    QSize,
    QTimer,
    QPoint,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QPixmap,
    QIcon,
    QImage
)
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMenu,
    QSystemTrayIcon,
    QApplication,
    QGraphicsOpacityEffect,
)

from config import (
    STANDBY_IMAGE,
    SPEAKING_IMAGE,
    SLEEPING_IMAGE,          # 👈 新增
    SLEEP_AFTER_SECONDS,     # 👈 新增
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    ALWAYS_ON_TOP,
    WINDOW_OPACITY,
    IDLE_CHAT_ENABLED,
    IDLE_CHAT_SECONDS,
    PET_CLICK_REACTION_ENABLED,
)

from dialogue import DialoguePlayer

from PIL import Image
import os

# folder = "pictures\\finally"
# for root, dirs, files in os.walk(folder):
#     for f in files:
#         if f.lower().endswith(".png"):
#             path = os.path.join(root, f)
#             img = Image.open(path).convert("RGBA")
#             img.save(path, "PNG")
#             print("已转换:", path)


class PetImage(QLabel):
    """
    桌宠图片。

    单独做成类，方便以后加入：
    - 鼠标悬停
    - 点击
    - 双击
    - 不同表情
    - 动画
    """

    clicked = Signal()
    double_clicked = Signal()

    def __init__(self, image_path=None, parent=None):
        super().__init__(parent)

        # ===== 关键：让这个 label 本身透明 =====
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")



        # 让图片按原始比例显示，不拉伸
        self.setScaledContents(False)

        if image_path:  # 👈 有路径才加载
            self.setPixmap(QPixmap(image_path))

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()

        super().mouseDoubleClickEvent(event)


class SpeechBubble(QLabel):
    """
    对话气泡。
    """

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWordWrap(True)

        self.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        self.setMinimumHeight(100)

        self.setStyleSheet(
            """
            QLabel {
                background-color: rgba(255, 250, 245, 235);
                color: #4A3F3A;
                border: 1px solid rgba(255, 210, 190, 220);
                border-radius: 18px;
                padding: 14px 18px;
                font-family: "Microsoft YaHei";
                font-size: 15px;
            }
            """
        )

        self.setText("")

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)


class PetWindow(QWidget):

    def __init__(self, api_client):

        super().__init__()

        # ===== 关键：窗口整体透明 =====
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.is_sleeping = False
        self.api_client = api_client

        self.drag_position = QPoint()

        self.always_on_top = ALWAYS_ON_TOP

        self.idle_enabled = IDLE_CHAT_ENABLED

        self._setup_window()
        self._setup_ui()
        self._setup_dialogue()
        self._setup_tray()
        self._setup_idle_timer()

        self._reset_idle_timer()



    # ========================================================
    # Window
    # ========================================================

    def _setup_window(self):

        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowSystemMenuHint
        )

        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint

        self.setWindowFlags(flags)

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.setWindowOpacity(WINDOW_OPACITY)

        self.setFixedSize(390, 540)
        self._setup_sleep_timer()

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self):

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            10, 10, 10, 10
        )

        main_layout.setSpacing(0)

        # ----------------------------------------------------
        # 对话框
        # ----------------------------------------------------

        self.speech = SpeechBubble(self)

        self.speech.setMinimumHeight(60)
        self.speech.setMaximumHeight(120)

        self.speech.clicked.connect(
            self.dialogue_click
        )

        main_layout.addWidget(self.speech,0)

        # ----------------------------------------------------
        # 桌宠
        # ----------------------------------------------------

        self.pet = PetImage(parent=self)

        self.pet.setAlignment(Qt.AlignCenter)

        self.pet.setFixedSize(
            IMAGE_WIDTH,
            IMAGE_HEIGHT,
        )

        self.pet.setScaledContents(False)

        self._set_pet_image(
            STANDBY_IMAGE
        )

        self.pet.clicked.connect(
            self.pet_clicked
        )

        self.pet.double_clicked.connect(
            self.pet_double_clicked
        )

        pet_container = QWidget()

        pet_layout = QHBoxLayout(
            pet_container
        )

        pet_layout.setContentsMargins(
            0, 0, 0, 0
        )

        pet_layout.addStretch()
        pet_layout.addWidget(self.pet)
        pet_layout.addStretch()

        main_layout.addWidget(
            pet_container,
            stretch=1
        )

        # ----------------------------------------------------
        # 输入区域
        # ----------------------------------------------------

        input_layout = QHBoxLayout()

        input_layout.setSpacing(6)

        self.input_box = QLineEdit()

        self.input_box.setPlaceholderText(
            "和姐姐说点什么吧……"
        )

        self.input_box.setMinimumHeight(42)

        self.input_box.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(255,255,255,235);
                border: 1px solid rgba(230,190,180,220);
                border-radius: 18px;
                padding: 0 15px;
                color: #51433E;
                font-size: 14px;
                font-family: "Microsoft YaHei";
            }

            QLineEdit:focus {
                border: 1px solid #E8A88E;
            }
            """
        )

        self.input_box.returnPressed.connect(
            self.send_message
        )

        self.send_button = QPushButton("发送")

        self.send_button.setFixedSize(
            60,
            42
        )

        self.send_button.setStyleSheet(
            """
            QPushButton {
                background-color: #E9A78D;
                color: white;
                border: none;
                border-radius: 18px;
                font-family: "Microsoft YaHei";
            }

            QPushButton:hover {
                background-color: #DF9276;
            }

            QPushButton:pressed {
                background-color: #CD8066;
            }
            """
        )

        self.send_button.clicked.connect(
            self.send_message
        )

        input_layout.addWidget(
            self.input_box
        )

        input_layout.addWidget(
            self.send_button
        )

        main_layout.addLayout(
            input_layout,0
        )

    # ========================================================
    # Dialogue
    # ========================================================

    def _setup_dialogue(self):

        self.dialogue = DialoguePlayer(
            self,
            type_interval=45,
            next_lock_ms=500,
            stay_ms=2000,
            last_stay_ms=3000,
        )

        self.dialogue.text_changed.connect(
            self._set_speech_text
        )

        self.dialogue.speaking_changed.connect(
            self._set_speaking
        )

        self.dialogue.dialogue_finished.connect(
            self._dialogue_finished
        )

    def dialogue_click(self):

        self.dialogue.click()

        self._reset_idle_timer()

    def _set_speech_text(self, text):

        self.speech.setText(text)

        self.speech.setVisible(
            bool(text)
        )

    def _set_speaking(self, speaking):

        if speaking:
            self._set_pet_image(
                SPEAKING_IMAGE
            )
        else:
            self._set_pet_image(
                STANDBY_IMAGE
            )

    def _dialogue_finished(self):

        self.speech.clear()

        self.speech.hide()

        self._set_pet_image(
            STANDBY_IMAGE
        )

    # ========================================================
    # 图片
    # ========================================================

    def _set_pet_image(self, path):

        image = QImage(str(path))
        if image.isNull():
            print("❌ 图片加载失败：", path)
            return

        # 确保有 alpha 通道
        image = image.convertToFormat(QImage.Format_ARGB32)

        scaled = image.scaled(
            IMAGE_WIDTH,
            IMAGE_HEIGHT,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.pet.setPixmap(QPixmap.fromImage(scaled))

    # ========================================================
    # 发送消息
    # ========================================================

    def send_message(self):

        message = (
            self.input_box.text()
            .strip()
        )

        if not message:
            return

        self.input_box.clear()

        self._reset_idle_timer()

        # 禁止重复发送
        self.input_box.setEnabled(False)
        self.send_button.setEnabled(False)

        # API 请求放到后台线程
        from PySide6.QtCore import QThread, Signal

        self.worker = ChatWorker(
            self.api_client,
            message,
        )

        self.worker.finished.connect(
            self._chat_finished
        )

        self.worker.error.connect(
            self._chat_error
        )

        self.worker.start()

    def _chat_finished(self, answer):

        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)

        if answer:
            self.dialogue.play(answer)

        self.input_box.setFocus()

    def _chat_error(self, error):

        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)

        self.dialogue.play(
            "抱歉呀，刚才和服务器的连接好像出了点问题。",
        )

        print("API Error:", error)

    # ========================================================
    # 桌宠互动
    # ========================================================

    def pet_clicked(self):

        self._reset_idle_timer()
        self._wake_up()

        if not PET_CLICK_REACTION_ENABLED:
            return

        reactions = [
            "嗯？是在叫我吗？",
            "怎么啦？姐姐在这里哦。",
            "摸摸我吗？",
            "今天也要好好照顾自己哦。",
            "我一直都有在看着你呢。",
        ]

        self.dialogue.play(
            random.choice(reactions)
        )

    def pet_double_clicked(self):

        self._reset_idle_timer()
        self._wake_up()

        self.dialogue.play(
            "双击我做什么呀？\n"
            "难道是想和姐姐多待一会儿？"
        )

    # ========================================================
    # 睡眠计时器
    # ========================================================

    def _setup_sleep_timer(self):
        self.sleep_timer = QTimer(self)
        self.sleep_timer.setSingleShot(True)
        self.sleep_timer.timeout.connect(self._go_to_sleep)

    def _reset_sleep_timer(self):
        """每次和桌宠互动时，重置睡眠倒计时"""
        if self.is_sleeping:
            return  # 已经睡了，不重置
        self.sleep_timer.start(SLEEP_AFTER_SECONDS * 1000)

    def _go_to_sleep(self):
        """进入睡眠状态"""
        if self.is_sleeping:
            return
        self.is_sleeping = True

        # 停止自动聊天，避免睡着还说话
        self.idle_timer.stop()

        # 切睡眠图
        self._set_pet_image(SLEEPING_IMAGE)

        # 用气泡直接显示，不走 dialogue
        self.speech.setText("呼……先睡一会儿……")
        self.speech.setVisible(True)



    def _wake_up(self):
        """从睡眠中唤醒"""
        if not self.is_sleeping:
            return
        self.is_sleeping = False

        # 切回待机图
        self._set_pet_image(STANDBY_IMAGE)

        # 重新开始自动聊天和睡眠计时
        self._reset_idle_timer()
        self._reset_sleep_timer()


    # ========================================================
    # 自动聊天
    # ========================================================

    def _setup_idle_timer(self):

        self.idle_timer = QTimer(self)

        self.idle_timer.setSingleShot(True)

        self.idle_timer.timeout.connect(
            self._idle_chat
        )

    def _reset_idle_timer(self):

        # 重置自动聊天计时器
        if self.idle_enabled and not self.is_sleeping:
            self.idle_timer.start(IDLE_CHAT_SECONDS * 1000)

        # 重置睡眠计时器
        self._reset_sleep_timer()

    def _idle_chat(self):

        if self.dialogue.is_typing:
            self._reset_idle_timer()
            return

        idle_messages = [
            "刚才好安静呀，你在忙什么呢？",
            "已经过了一会儿啦，记得稍微休息一下哦。",
            "偷偷看你一眼……还好吗？",
            "如果累了的话，可以稍微放松一下。",
        ]

        self.dialogue.play(
            random.choice(idle_messages)
        )

        self._reset_idle_timer()

    # ========================================================
    # 右键菜单
    # ========================================================

    def contextMenuEvent(self, event):

        menu = QMenu(self)

        menu.setStyleSheet(
            """
            QMenu {
                background: #FFF9F6;
                border: 1px solid #E8D5CE;
                padding: 5px;
            }

            QMenu::item {
                padding: 8px 25px;
                color: #51433E;
            }

            QMenu::item:selected {
                background: #F4DED5;
                border-radius: 5px;
            }
            """
        )

        # ----------------------------------------------------
        # 主动说话
        # ----------------------------------------------------

        greet_action = QAction(
            "让姐姐说句话",
            self,
        )

        greet_action.triggered.connect(
            lambda: self.dialogue.play(
                "今天也辛苦啦，有什么想和姐姐聊聊的吗？"
            )
        )

        menu.addAction(
            greet_action
        )

        # ----------------------------------------------------
        # 清空记忆
        # ----------------------------------------------------

        clear_action = QAction(
            "清空聊天记忆",
            self,
        )

        clear_action.triggered.connect(
            self.api_client.clear_history
        )

        menu.addAction(
            clear_action
        )

        menu.addSeparator()

        # ----------------------------------------------------
        # 置顶
        # ----------------------------------------------------

        top_action = QAction(
            "窗口置顶",
            self,
        )

        top_action.setCheckable(True)
        top_action.setChecked(
            self.always_on_top
        )

        top_action.triggered.connect(
            self.toggle_always_on_top
        )

        menu.addAction(
            top_action
        )

        # ----------------------------------------------------
        # 自动陪伴
        # ----------------------------------------------------

        idle_action = QAction(
            "自动陪伴",
            self,
        )

        idle_action.setCheckable(True)
        idle_action.setChecked(
            self.idle_enabled
        )

        idle_action.triggered.connect(
            self.toggle_idle
        )

        menu.addAction(
            idle_action
        )

        menu.addSeparator()

        # ----------------------------------------------------
        # 隐藏
        # ----------------------------------------------------

        hide_action = QAction(
            "隐藏桌宠",
            self,
        )

        hide_action.triggered.connect(
            self.hide
        )

        menu.addAction(
            hide_action
        )

        # ----------------------------------------------------
        # 退出
        # ----------------------------------------------------

        exit_action = QAction(
            "退出",
            self,
        )

        exit_action.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            exit_action
        )

        menu.exec(
            event.globalPos()
        )

    # ========================================================
    # 菜单操作
    # ========================================================

    def toggle_always_on_top(self):

        self.always_on_top = not self.always_on_top

        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowSystemMenuHint
        )

        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint

        self.setWindowFlags(flags)

        self.show()

    def toggle_idle(self):

        self.idle_enabled = not self.idle_enabled

        if self.idle_enabled:
            self._reset_idle_timer()
        else:
            self.idle_timer.stop()

    # ========================================================
    # 拖动
    # ========================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            event.accept()

        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if (
            event.buttons()
            & Qt.LeftButton
        ):

            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )

            event.accept()

        else:
            super().mouseMoveEvent(event)

    # ========================================================
    # 托盘
    # ========================================================

    def _setup_tray(self):

        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return

        self.tray = QSystemTrayIcon(
            self
        )

        icon = QIcon(
            str(STANDBY_IMAGE)
        )

        self.tray.setIcon(icon)

        tray_menu = QMenu()

        show_action = QAction(
            "显示桌宠",
            self,
        )

        show_action.triggered.connect(
            self.showNormal
        )

        tray_menu.addAction(
            show_action
        )

        exit_action = QAction(
            "退出",
            self,
        )

        exit_action.triggered.connect(
            QApplication.quit
        )

        tray_menu.addAction(
            exit_action
        )

        self.tray.setContextMenu(
            tray_menu
        )

        self.tray.show()


from PySide6.QtCore import QThread, Signal


class ChatWorker(QThread):

    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        api_client,
        message,
    ):
        super().__init__()

        self.api_client = api_client
        self.message = message

    def run(self):

        try:

            answer = self.api_client.chat(
                self.message
            )

            self.finished.emit(
                answer
            )

        except Exception as e:

            self.error.emit(
                str(e)
            )
