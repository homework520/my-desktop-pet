# codes/api_client.py

from openai import OpenAI

from config import (
    API_KEY,
    API_BASE_URL,
    MODEL_NAME,
    MAX_HISTORY,
)
from persona import PersonaStore


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

        self.messages = [
            {
                "role": "system",
                "content": self.persona.system_prompt(),
            }
        ]

    def chat(self, user_message: str) -> str:
        """
        向 DeepSeek 发送一条消息。
        """

        user_message = user_message.strip()

        if not user_message:
            return ""

        self._refresh_system_prompt()

        self.messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        # 控制历史长度，避免长期运行后上下文无限增长
        self._trim_history()

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=self.messages,
            temperature=0.8,
            max_tokens=500,
            stream=False,
        )

        answer = response.choices[0].message.content or ""
        answer = answer.strip()

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
