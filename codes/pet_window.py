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
    FLOATING_IMAGE,
    SLEEP_AFTER_SECONDS,     # 👈 新增
    SLEEP_BUBBLE_MS,
    STANDBY_MODE_IMAGE_DIR,
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

        window = self.window()
        if event.button() == Qt.LeftButton and hasattr(window, "_on_drag_press"):
            window._on_drag_press(event)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        window = self.window()
        if hasattr(window, "_on_drag_move"):
            window._on_drag_move(event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        window = self.window()
        dragged = False
        if hasattr(window, "_on_drag_release"):
            dragged = window._on_drag_release(event)

        if event.button() == Qt.LeftButton and not dragged:
            self.clicked.emit()

        super().mouseReleaseEvent(event)

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
            Qt.AlignLeft | Qt.AlignTop
        )

        self.setMinimumHeight(60)

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
        self.is_dragging = False
        self.api_client = api_client
        self._sleep_bubble = False
        self._standby_mode = False
        self._standby_image = None

        self.drag_position = QPoint()
        self._drag_press_pos = QPoint()
        self._drag_pressed = False

        self.always_on_top = ALWAYS_ON_TOP

        self.idle_enabled = IDLE_CHAT_ENABLED

        self._greeting_pending = False
        self._greeting_cancelled = False
        self._did_startup_greeting = False
        self._greeting_worker = None

        self._setup_window()
        self._setup_ui()
        self._setup_dialogue()
        self._setup_tray()
        self._setup_idle_timer()

        self._reset_idle_timer()

    def showEvent(self, event):

        super().showEvent(event)

        if self._did_startup_greeting:
            return

        self._did_startup_greeting = True
        QTimer.singleShot(200, self._start_startup_greeting)

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
        self.speech.setMaximumHeight(240)

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

        self.input_container = QWidget()

        input_layout = QHBoxLayout(
            self.input_container
        )

        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)

        self.input_box = QLineEdit()

        self.input_box.setPlaceholderText(
            self.api_client.persona.persona.input_placeholder
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

        main_layout.addWidget(
            self.input_container,
            0,
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

        self._wake_up()
        self.dialogue.click()

        self._reset_idle_timer()

    def _set_speech_text(self, text):

        # 正式对话开始后，睡眠台词让位给对话气泡
        if text and self._sleep_bubble:
            self._sleep_bubble = False
            self.sleep_bubble_timer.stop()

        self.speech.setText(text)

        self.speech.setVisible(
            bool(text)
        )

    def _set_speaking(self, speaking):

        if self.is_dragging or self._standby_mode:
            return

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

        if not self.is_dragging:
            self._restore_pose_image()

    # ========================================================
    # 图片
    # ========================================================

    def _restore_pose_image(self):

        if self._standby_mode and self._standby_image:
            self._set_pet_image(self._standby_image)
        elif self.is_sleeping:
            self._set_pet_image(SLEEPING_IMAGE)
        elif self.dialogue.is_typing:
            self._set_pet_image(SPEAKING_IMAGE)
        else:
            self._set_pet_image(STANDBY_IMAGE)

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

        if self._standby_mode:
            return

        self._cancel_startup_greeting()

        message = (
            self.input_box.text()
            .strip()
        )

        if not message:
            return

        self.input_box.clear()

        # 睡觉时也能直接发消息：先唤醒，避免睡着却切到说话图
        self._wake_up()
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

        # 待机模式下不显示对话内容
        if self._standby_mode:
            return

        if answer:
            self.dialogue.play(answer)

        self.input_box.setFocus()

    def _chat_error(self, error):

        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)

        if self._standby_mode:
            print("API Error（待机模式，已忽略）:", error)
            return

        self.dialogue.play(
            "抱歉呀，刚才和服务器的连接好像出了点问题。",
        )

        print("API Error:", error)

    # ========================================================
    # 桌宠互动
    # ========================================================

    def pet_clicked(self):

        self._cancel_startup_greeting()
        self._reset_idle_timer()
        self._wake_up()

        if not PET_CLICK_REACTION_ENABLED:
            return

        reactions = self.api_client.persona.persona.click_reactions
        if not reactions:
            return

        self.dialogue.play(
            random.choice(reactions)
        )

    def pet_double_clicked(self):

        self._cancel_startup_greeting()
        self._reset_idle_timer()
        self._wake_up()

        self.dialogue.play(
            self.api_client.persona.persona.double_click_line
        )

    # ========================================================
    # 睡眠计时器
    # ========================================================

    def _setup_sleep_timer(self):
        self.sleep_timer = QTimer(self)
        self.sleep_timer.setSingleShot(True)
        self.sleep_timer.timeout.connect(self._go_to_sleep)

        self.sleep_bubble_timer = QTimer(self)
        self.sleep_bubble_timer.setSingleShot(True)
        self.sleep_bubble_timer.timeout.connect(self._clear_sleep_bubble)

    def _reset_sleep_timer(self):
        """每次和桌宠互动时，重置睡眠倒计时"""
        if self.is_sleeping or self._standby_mode:
            return  # 已经睡了或处于待机模式，不重置
        self.sleep_timer.start(SLEEP_AFTER_SECONDS * 1000)

    def _go_to_sleep(self):
        """进入睡眠状态"""
        if self.is_sleeping or self._standby_mode:
            return

        # 正在说话、等回复或等开机问候时先不睡，等下一轮倒计时
        worker = getattr(self, "worker", None)
        if (
            self._greeting_pending
            or self.dialogue.is_active
            or (worker is not None and worker.isRunning())
        ):
            self._reset_sleep_timer()
            return

        self.is_sleeping = True

        # 停止自动聊天，避免睡着还说话
        self.idle_timer.stop()

        if not self.is_dragging:
            self._set_pet_image(SLEEPING_IMAGE)

        # 用气泡直接显示，不走 dialogue；过一会儿自动收起
        sleep_line = self.api_client.persona.persona.sleep_line
        if sleep_line:
            self.speech.setText(sleep_line)
            self.speech.setVisible(True)
            self._sleep_bubble = True
            self.sleep_bubble_timer.start(SLEEP_BUBBLE_MS)

    def _clear_sleep_bubble(self):
        """睡眠台词显示一会儿后自动收起，避免一直挂在桌上。"""
        if not self._sleep_bubble:
            return

        if not self.is_sleeping:
            self._sleep_bubble = False
            return

        if self.dialogue.is_typing:
            self.sleep_bubble_timer.start(SLEEP_BUBBLE_MS)
            return

        self._sleep_bubble = False
        self.speech.clear()
        self.speech.hide()

    def _wake_up(self):
        """从睡眠中唤醒"""
        if not self.is_sleeping:
            return
        self.is_sleeping = False

        self.sleep_bubble_timer.stop()
        if self._sleep_bubble:
            self._sleep_bubble = False
            self.speech.clear()
            self.speech.hide()

        # 切回待机图
        self._restore_pose_image()

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

        idle_messages = self.api_client.persona.persona.idle_messages
        if not idle_messages:
            self._reset_idle_timer()
            return

        self.dialogue.play(
            random.choice(idle_messages)
        )

        self._reset_idle_timer()

    # ========================================================
    # 待机模式
    # ========================================================

    def _pick_standby_image(self):

        suffixes = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".gif",
        }

        try:
            candidates = [
                path
                for path in STANDBY_MODE_IMAGE_DIR.iterdir()
                if path.is_file() and path.suffix.lower() in suffixes
            ]
        except OSError as e:
            print("待机模式图片目录读取失败:", e)
            candidates = []

        if not candidates:
            print(
                "待机模式没有可用图片，使用默认立绘：",
                STANDBY_MODE_IMAGE_DIR,
            )
            return STANDBY_IMAGE

        return random.choice(candidates)

    def _enter_standby_mode(self):

        if self._standby_mode:
            return

        self._standby_mode = True
        self._cancel_startup_greeting()

        # 待机模式不睡觉，保持随机立绘
        self.sleep_timer.stop()
        self.sleep_bubble_timer.stop()
        self._sleep_bubble = False
        self.is_sleeping = False

        self._standby_image = self._pick_standby_image()
        self.dialogue.stop()

        self._set_pet_image(self._standby_image)

        # 关闭对话入口
        self.input_container.hide()
        self.input_box.setEnabled(False)
        self.send_button.setEnabled(False)

        # 主动说话仍然保留
        self._reset_idle_timer()

    def _exit_standby_mode(self):

        if not self._standby_mode:
            return

        self._standby_mode = False
        self._standby_image = None

        self.input_container.show()
        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_box.setFocus()

        self._restore_pose_image()
        self._reset_idle_timer()

    def toggle_standby_mode(self, _checked=False):

        if self._standby_mode:
            self._exit_standby_mode()
        else:
            self._enter_standby_mode()

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
            "主动说一句话",
            self,
        )

        greet_action.triggered.connect(
            self._play_menu_greet
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

        # ----------------------------------------------------
        # 人设
        # ----------------------------------------------------

        scene_menu = menu.addMenu("切换场景")

        auto_action = QAction("自动（按时间）", self)
        auto_action.setCheckable(True)
        auto_action.setChecked(
            self.api_client.persona.is_auto_scene
        )
        auto_action.triggered.connect(
            lambda checked=False: self.switch_auto_scene()
        )
        scene_menu.addAction(auto_action)
        scene_menu.addSeparator()

        for scene_id, title in self.api_client.persona.list_scenes():
            scene_action = QAction(title, self)
            scene_action.setCheckable(True)
            scene_action.setChecked(
                not self.api_client.persona.is_auto_scene
                and scene_id == self.api_client.persona.active_scene
            )
            scene_action.triggered.connect(
                lambda checked=False, sid=scene_id: self.switch_scene(sid)
            )
            scene_menu.addAction(scene_action)

        reload_action = QAction(
            "重载人设",
            self,
        )
        reload_action.triggered.connect(
            self.reload_persona
        )
        menu.addAction(reload_action)

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

        # ----------------------------------------------------
        # 待机模式
        # ----------------------------------------------------

        standby_action = QAction(
            "待机模式",
            self,
        )

        standby_action.setCheckable(True)
        standby_action.setChecked(
            self._standby_mode
        )

        standby_action.triggered.connect(
            self.toggle_standby_mode
        )

        menu.addAction(
            standby_action
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

    def switch_scene(self, scene_id):

        try:
            self.api_client.set_scene(scene_id)
        except Exception as e:
            print("切换场景失败:", e)

    def switch_auto_scene(self):

        try:
            self.api_client.set_auto_scene()
        except Exception as e:
            print("切换自动场景失败:", e)

    def reload_persona(self):

        try:
            self.api_client.reload_persona()
            self.input_box.setPlaceholderText(
                self.api_client.persona.persona.input_placeholder
            )
        except Exception as e:
            print("重载人设失败:", e)

    def _play_menu_greet(self):

        self._cancel_startup_greeting()
        self.dialogue.play(
            self.api_client.persona.persona.greet_line
        )

    # ========================================================
    # 开机问候
    # ========================================================

    def _start_startup_greeting(self):

        if self._greeting_cancelled or self._standby_mode:
            return

        self._greeting_pending = True
        self._greeting_worker = GreetingWorker(self.api_client)
        self._greeting_worker.succeeded.connect(self._greeting_finished)
        self._greeting_worker.failed.connect(self._greeting_failed)
        self._greeting_worker.start()

    def _cancel_startup_greeting(self):

        if self._greeting_pending:
            self._greeting_cancelled = True
            self._greeting_pending = False

    def _greeting_finished(self, _prompt, answer):

        self._play_startup_greeting(answer)

    def _greeting_failed(self, _prompt, error):

        print("开机问候失败:", error)
        self._play_startup_greeting("")

    def _play_startup_greeting(self, answer):

        if self._greeting_cancelled or self._standby_mode:
            return

        self._greeting_pending = False

        text = (answer or "").strip() or (
            self.api_client.persona.persona.greet_line or ""
        ).strip()

        if not text:
            return

        # 只记录“已经问候过”，场景指令本身不进聊天历史
        if not self.api_client.commit_startup_greeting(text):
            return

        self.dialogue.play(text)
        self._reset_idle_timer()

    # ========================================================
    # 拖动
    # ========================================================

    def _on_drag_press(self, event):

        if event.button() != Qt.LeftButton:
            return

        self.drag_position = (
            event.globalPosition().toPoint()
            - self.frameGeometry().topLeft()
        )
        self._drag_press_pos = event.globalPosition().toPoint()
        self._drag_pressed = True
        self.is_dragging = False

    def _on_drag_move(self, event):

        if not self._drag_pressed or not (event.buttons() & Qt.LeftButton):
            return False

        current = event.globalPosition().toPoint()
        if not self.is_dragging:
            delta = current - self._drag_press_pos
            if delta.manhattanLength() < 8:
                return False
            self.is_dragging = True
            self._cancel_startup_greeting()
            self._wake_up()
            self._set_pet_image(FLOATING_IMAGE)

        self.move(current - self.drag_position)
        return True

    def _on_drag_release(self, event):

        if event.button() != Qt.LeftButton:
            return False

        dragged = self.is_dragging
        self.is_dragging = False
        self._drag_pressed = False
        self.drag_position = QPoint()
        self._drag_press_pos = QPoint()

        if dragged:
            self._restore_pose_image()
            self._reset_idle_timer()

        return dragged

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self._on_drag_press(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if event.buttons() & Qt.LeftButton:
            self._on_drag_move(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:
            self._on_drag_release(event)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

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


class GreetingWorker(QThread):

    succeeded = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def run(self):

        prompt = self.api_client.build_startup_greeting_prompt()

        try:
            prompt, answer = self.api_client.generate_startup_greeting()
            self.succeeded.emit(prompt, answer)
        except Exception as e:
            self.failed.emit(prompt, str(e))


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
