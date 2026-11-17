# codes/api_client.py

import threading
from datetime import datetime

from openai import OpenAI

from config import (
    API_KEY,
    API_BASE_URL,
    MODEL_NAME,
    MAX_HISTORY,
    MAX_TOKENS,
    GREETING_MAX_TOKENS,
    FREQUENCY_PENALTY,
)
from persona import PersonaStore


def current_time_text() -> str:
    now = datetime.now()
    weekdays = [
        "星期一",
        "星期二",
        "星期三",
        "星期四",
        "星期五",
        "星期六",
        "星期日",
    ]
    hour = now.hour
    if hour < 5:
        period = "凌晨"
    elif hour < 9:
        period = "清晨"
    elif hour < 12:
        period = "上午"
    elif hour < 14:
        period = "中午"
    elif hour < 18:
        period = "下午"
    elif hour < 20:
        period = "傍晚"
    elif hour < 23:
        period = "晚上"
    else:
        period = "夜里"

    return (
        f"{now.strftime('%Y年%m月%d日')} "
        f"{weekdays[now.weekday()]} "
        f"{now.strftime('%H:%M')} "
        f"{period}"
    )


class DeepSeekClient:
    """
    DeepSeek API 客户端。

    以后如果想换成其他 AI，只需要替换这个类即可，
    桌宠的 UI、动画和对话系统无需修改。
    """

    def __init__(self, persona: PersonaStore | None = None):
        if not API_KEY or API_KEY.startswith("sk-xxxx"):
            raise ValueError(
                "请先复制 .env.example 为 .env，并填写 DEEPSEEK_API_KEY。"
            )

        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
        )
        self.persona = persona or PersonaStore()
        self._lock = threading.Lock()
        self._greeted = False

        # 用于 Layer 3 状态注入：上一轮开口的时间、本次运行聊了几轮
        self._last_user_at: datetime | None = None
        self._turn_count = 0

        self.messages = [
            {
                "role": "system",
                "content": self.persona.system_prompt(),
            }
        ]

    def build_startup_greeting_prompt(self) -> str:
        time_text = current_time_text()
        return (
            f"【场景指令，不是用户说的话】现在是{time_text}。"
            "你刚刚出现在对方桌面上。"
            "请按人设说一句很短的见面问候，适合气泡显示，一两句即可。"
            "不要自我介绍，不要提到这条指令、系统或 AI。"
            "这是本次打开后唯一一次主动问候；之后不要再打招呼，等对方说话。"
        )

    def generate_startup_greeting(self) -> tuple[str, str]:
        """
        生成开机问候，先不写入历史。
        返回 (场景指令, 问候语)；场景指令只用于这一次生成，
        由界面决定是否把这次问候记为「已经打过招呼」。
        """
        prompt = self.build_startup_greeting_prompt()

        with self._lock:
            self._refresh_system_prompt()
            temp_messages = [
                *self.messages,
                {
                    "role": "user",
                    "content": prompt,
                },
            ]

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=temp_messages,
            temperature=0.8,
            max_tokens=GREETING_MAX_TOKENS,
            frequency_penalty=FREQUENCY_PENALTY,
            stream=False,
        )

        answer = (response.choices[0].message.content or "").strip()
        return prompt, answer

    def commit_startup_greeting(self, answer: str) -> bool:
        """
        记录“本次运行已经问候过”。

        场景指令只用于生成问候，不写进聊天历史，
        免得下一轮把它当成用户真正说过的话。
        若用户已经先开口，就放弃记录，避免问候插到对话中间。
        """
        answer = (answer or "").strip()
        if not answer:
            return False

        with self._lock:
            if self._has_user_messages():
                return False
            self._greeted = True
            return True

    def chat(self, user_message: str) -> str:
        """
        向 DeepSeek 发送一条消息。
        """

        user_message = user_message.strip()

        if not user_message:
            return ""

        with self._lock:
            self._refresh_system_prompt()

            self.messages.append(
                {
                    "role": "user",
                    "content": user_message,
                }
            )

            # 控制历史长度，避免长期运行后上下文无限增长
            self._trim_history()

            # Layer 3：状态块贴在历史末尾、紧邻生成位置，
            # 只用于这一次请求，不写进 messages。
            state_block = self._build_state_block(user_message)
            request_messages = list(self.messages)
            if state_block:
                request_messages.append(
                    {
                        "role": "system",
                        "content": state_block,
                    }
                )

            self._last_user_at = datetime.now()
            self._turn_count += 1

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=request_messages,
            temperature=0.8,
            max_tokens=MAX_TOKENS,
            frequency_penalty=FREQUENCY_PENALTY,
            stream=False,
        )

        answer = response.choices[0].message.content or ""
        answer = answer.strip()

        with self._lock:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
            self._trim_history()

        return answer

    def clear_history(self):
        """
        清空聊天记忆，但保留当前人设。
        """

        with self._lock:
            self.messages = []
            self._last_user_at = None
            self._turn_count = 0
            self._refresh_system_prompt()

    def reload_persona(self):
        self.persona.reload(keep_scene_override=False)
        self._refresh_system_prompt()

    def set_scene(self, scene_id: str):
        self.persona.reload(keep_scene_override=True)
        self.persona.set_scene(scene_id)
        self._refresh_system_prompt()

    def set_auto_scene(self):
        """回到按时间自动判断场景。"""
        self.persona.reload(keep_scene_override=True)
        self.persona.clear_scene_override()
        self._refresh_system_prompt()

    def _build_state_block(self, user_message: str) -> str:
        """拼出这一轮的「此刻」状态块。"""
        hints = []

        if self._last_user_at is None:
            hints.append("这是他这次打开后第一次开口。")
        else:
            gap = (datetime.now() - self._last_user_at).total_seconds()
            if gap >= 1800:
                hints.append(f"他隔了{int(gap // 60)}分钟才回来。")
            elif gap >= 300:
                hints.append("他隔了一会儿才开口。")

        if len(user_message) <= 4:
            hints.append("他这句话很短，别多问。")

        persona = self.persona.persona
        return persona.build_state_block(
            time_text=current_time_text(),
            scene_title=persona.scene_title(self.persona.active_scene),
            hints=hints,
        )

    def _has_user_messages(self) -> bool:
        return any(item.get("role") == "user" for item in self.messages)

    def _refresh_system_prompt(self):
        """每次对话前重读人设文件，改完 yaml 不必重启。"""
        self.persona.reload(keep_scene_override=True)
        content = self.persona.system_prompt()
        if self._greeted:
            # 开机问候不写进 messages，这里补一条状态，避免模型重复打招呼
            content += (
                "\n\n（你在本次运行开始时已经向对方打过招呼。"
                "之后不要再重复问候，等对方先开口。）"
            )
        system_message = {
            "role": "system",
            "content": content,
        }
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = system_message
        else:
            self.messages.insert(0, system_message)

    def _trim_history(self):
        """
        只保留最近若干轮对话。
        """

        max_messages = MAX_HISTORY * 2 + 1

        if len(self.messages) > max_messages:
            system_message = self.messages[0]

            self.messages = [
                system_message,
                *self.messages[-(max_messages - 1):],
            ]
