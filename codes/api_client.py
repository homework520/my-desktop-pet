# codes/api_client.py

from openai import OpenAI

from config import (
    API_KEY,
    API_BASE_URL,
    MODEL_NAME,
    SYSTEM_PROMPT,
    MAX_HISTORY,
)


class DeepSeekClient:
    """
    DeepSeek API 客户端。

    以后如果想换成其他 AI，只需要替换这个类即可，
    桌宠的 UI、动画和对话系统无需修改。
    """

    def __init__(self):
        if not API_KEY or API_KEY.startswith("sk-xxxx"):
            raise ValueError(
                "请先在 codes/config.py 中填写 DeepSeek API Key。"
            )

        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
        )

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def chat(self, user_message: str) -> str:
        """
        向 DeepSeek 发送一条消息。
        """

        user_message = user_message.strip()

        if not user_message:
            return ""

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
        清空聊天记忆。
        """

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

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
