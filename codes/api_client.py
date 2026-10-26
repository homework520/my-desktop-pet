# codes/api_client.py

import threading
from datetime import datetime

from openai import OpenAI

from config import (
    API_KEY,
    API_BASE_URL,
    MODEL_NAME,
    MAX_HISTORY,
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
        返回 (场景指令, 问候语)，由界面决定是否计入聊天。
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
            max_tokens=120,
            stream=False,
        )

        answer = (response.choices[0].message.content or "").strip()
        return prompt, answer

    def try_commit_exchange(self, user_message: str, answer: str) -> bool:
        """
        把一轮对话写入历史。
        若用户已经先开口，就放弃写入，避免问候插到对话中间。
        """
        user_message = (user_message or "").strip()
        answer = (answer or "").strip()
        if not user_message or not answer:
            return False

        with self._lock:
            if self._has_user_messages():
                return False
            self.messages.append(
                {
                    "role": "user",
                    "content": user_message,
                }
            )
            self.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
            self._trim_history()
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
            request_messages = list(self.messages)

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=request_messages,
            temperature=0.8,
            max_tokens=500,
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
            self._refresh_system_prompt()
            self.messages = [
                {
                    "role": "system",
                    "content": self.persona.system_prompt(),
                }
            ]

    def reload_persona(self):
        self.persona.reload(keep_scene_override=False)
        self._refresh_system_prompt()

    def set_scene(self, scene_id: str):
        self.persona.reload(keep_scene_override=True)
        self.persona.set_scene(scene_id)
        self._refresh_system_prompt()

    def _has_user_messages(self) -> bool:
        return any(item.get("role") == "user" for item in self.messages)

    def _refresh_system_prompt(self):
        """每次对话前重读人设文件，改完 yaml 不必重启。"""
        self.persona.reload(keep_scene_override=True)
        system_message = {
            "role": "system",
            "content": self.persona.system_prompt(),
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
