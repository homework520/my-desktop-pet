# codes/config.py
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# 项目路径
# ============================================================

def _project_dir() -> Path:
    """开发时是仓库根目录；打包后是 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _resource_dir() -> Path:
    """图片等随程序分发的资源目录。"""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        internal = exe_dir / "_internal"
        if (internal / "pictures").exists():
            return internal
        return exe_dir
    return _project_dir()


def _persona_dir() -> Path:
    """
    人设目录。

    打包后优先读 exe 同级的 persona，方便改完立刻生效；
    没有的话再回退到程序内置的那一份。
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        user_persona = exe_dir / "persona"
        if user_persona.exists():
            return user_persona
        internal = exe_dir / "_internal" / "persona"
        if internal.exists():
            return internal
        return user_persona
    return _project_dir() / "persona"


BASE_DIR = _project_dir()
RESOURCE_DIR = _resource_dir()
PERSONA_DIR = _persona_dir()

# 密钥只从环境变量 / .env 读取，不要写进源码
load_dotenv(BASE_DIR / ".env")

PICTURE_DIR = RESOURCE_DIR / "pictures" / "finally"

# 待机模式使用的随机立绘目录
STANDBY_MODE_IMAGE_DIR = RESOURCE_DIR / "pictures" / "see"

STANDBY_IMAGE = PICTURE_DIR / "standby.png"
SPEAKING_IMAGE = PICTURE_DIR / "speaking.png"
SLEEPING_IMAGE = PICTURE_DIR / "sleeping.png"
FLOATING_IMAGE = PICTURE_DIR / "float.png"


# ============================================================
# DeepSeek 配置（密钥放在项目根目录的 .env）
# ============================================================

API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
API_BASE_URL = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com").strip()
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()


# ============================================================
# 对话参数
# ============================================================

# 单次回复的最大 token 数。约 100~140 汉字，
# 和气泡的打字机速度对齐，避免说太久用户已经点掉了。
MAX_TOKENS = 200

# 开机问候的最大 token 数
GREETING_MAX_TOKENS = 100

# 频率惩罚：压制「这条命是你的」这类口头禅反复循环
FREQUENCY_PENALTY = 0.4

# 是否按时间自动切换场景。手动切换过场景后，以手动为准。
SCENE_AUTO_ENABLED = True

# 打字速度：每个字符多少毫秒
TYPEWRITER_INTERVAL = 45

# 一句话完整显示后，存在下一句话时至少等待多久才能点击下一句
NEXT_SENTENCE_LOCK_MS = 500

# 有下一句话时，完整显示后的最长等待时间
# 这里不自动跳下一句，只允许用户点击
SENTENCE_STAY_MS = 2000

# 最后一条话显示多久后自动消失
LAST_SENTENCE_STAY_MS = 3000

# 淡出动画
FADE_OUT_DURATION_MS = 500


# ============================================================
# 桌宠界面
# ============================================================

PET_WIDTH = 360
PET_HEIGHT = 620

IMAGE_WIDTH = 360
IMAGE_HEIGHT = 360

WINDOW_OPACITY = 1.0

# 是否启动时置顶
ALWAYS_ON_TOP = True


# ============================================================
# 扩展功能
# ============================================================

# 开启后，长时间没有互动会主动说话
IDLE_CHAT_ENABLED = True

# 多久没有操作后触发主动聊天
IDLE_CHAT_SECONDS = 60

# 点击角色时是否产生互动
PET_CLICK_REACTION_ENABLED = True

# 最多保存多少轮聊天。窗口太长，模型会模仿自己前面的腔调，越聊越腻。
MAX_HISTORY = 14

# 多久没有互动后睡觉
SLEEP_AFTER_SECONDS = 200

# 睡眠台词显示多久后自动收起
SLEEP_BUBBLE_MS = 6000
