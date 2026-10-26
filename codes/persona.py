# codes/persona.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from config import PERSONA_DIR


def _as_str(value, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _relationship_lines(value) -> list[str]:
    if not isinstance(value, dict):
        return _as_list(value)

    lines = []
    for name, detail in value.items():
        if isinstance(detail, (list, tuple)):
            body = "；".join(str(item).strip() for item in detail if str(item).strip())
        else:
            body = _as_str(detail)
        if body:
            lines.append(f"{name}：{body}")
        else:
            lines.append(str(name))
    return lines


def _world_lines(value) -> list[str]:
    """
    世界观可以写成标签列表，也可以按地点分组：

    world:
      - 格局：……
      - 陇平：西陲边郡

    world:
      overview:
        - 格局：……
      places:
        陇平:
          - 西陲边郡
      geography:
        - 陇平在西，京城在东
    """
    if not value:
        return []
    if not isinstance(value, dict):
        return _as_list(value)

    lines = []
    for key, detail in value.items():
        if key in {"overview", "era", "notes", "geography", "relations"}:
            lines.extend(_as_list(detail))
            continue
        if key == "places" and isinstance(detail, dict):
            lines.extend(_relationship_lines(detail))
            continue
        if isinstance(detail, (list, tuple, dict)):
            body = "；".join(_as_list(detail) if not isinstance(detail, dict) else _relationship_lines(detail))
            lines.append(f"{key}：{body}" if body else str(key))
        else:
            text = _as_str(detail)
            lines.append(f"{key}：{text}" if text else str(key))
    return lines


def _read_memory_file(path: Path) -> str:
    if not path.exists():
        return ""

    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        lines.append(text)
    return "\n".join(lines)


@dataclass
class Persona:
    name: str = "姐姐"
    app_name: str = "温柔姐姐桌宠"
    identity: list[str] = field(default_factory=list)
    personality: list[str] = field(default_factory=list)
    core_obsessions: list[str] = field(default_factory=list)
    speech_style: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    world: list[str] = field(default_factory=list)
    scenes: dict = field(default_factory=dict)
    current_scene: str = "desktop"
    rules: list[str] = field(default_factory=list)
    memory: str = ""
    input_placeholder: str = "和姐姐说点什么吧……"
    sleep_line: str = "呼……先睡一会儿……"
    double_click_line: str = "双击我做什么呀？\n难道是想和姐姐多待一会儿？"
    greet_line: str = "今天也辛苦啦，有什么想和姐姐聊聊的吗？"
    click_reactions: list[str] = field(default_factory=list)
    idle_messages: list[str] = field(default_factory=list)

    def scene_title(self, scene_id: str) -> str:
        data = self.scenes.get(scene_id)
        if isinstance(data, dict):
            return _as_str(data.get("title"), scene_id)
        return scene_id

    def scene_tags(self, scene_id: str) -> list[str]:
        data = self.scenes.get(scene_id)
        if data is None:
            return []
        if isinstance(data, dict):
            return _as_list(data.get("tags") or data.get("setting"))
        return _as_list(data)

    def list_scenes(self) -> list[tuple[str, str]]:
        return [
            (scene_id, self.scene_title(scene_id))
            for scene_id in self.scenes
        ]

    def build_system_prompt(self, scene_id: str | None = None) -> str:
        """
        模块化拼接：
        A 基础人设 + 世界观 + B 当前场景 + 规则 + C 长期记忆
        """
        active_scene = scene_id or self.current_scene
        parts = [
            f"你是「{self.name}」。",
            "下面是浓缩后的设定标签，请按标签自己脑补细节，不要把标签念给用户听。",
            _section("模块A：身份锚点", self.identity),
            _section("模块A：性格底色", self.personality),
            _section("模块A：核心执念", self.core_obsessions),
            _section("模块A：说话风格", self.speech_style),
            _section("模块A：已知人物关系", self.relationships),
            _section("世界观：地理与背景（只在提到时自然用上，不要上课）", self.world),
            _section(
                f"模块B：当前场景（{self.scene_title(active_scene)}）",
                self.scene_tags(active_scene),
            ),
            _section("规则：遇到什么情况怎么做", self.rules),
        ]

        if self.memory:
            parts.append("模块C：长期记忆（需要时自然用上，不要主动宣读）\n" + self.memory)

        parts.append(
            "你是长期陪伴用户的桌面宠物，回复时保持前后连贯。"
        )
        return "\n\n".join(part for part in parts if part)


class PersonaStore:
    """
    从 persona/character.yaml 和 persona/memory.md 读取人设。
    每次对话前可以 reload，改文件后不必重启。
    """

    def __init__(self, directory: Path | None = None):
        self.directory = Path(directory) if directory else Path(PERSONA_DIR)
        self.character_path = self.directory / "character.yaml"
        self.memory_path = self.directory / "memory.md"
        self.scene_override: str | None = None
        self.persona = self._load()

    def reload(self, keep_scene_override: bool = True) -> Persona:
        self.persona = self._load()
        if (
            not keep_scene_override
            or self.scene_override not in self.persona.scenes
        ):
            self.scene_override = None
        return self.persona

    def set_scene(self, scene_id: str) -> None:
        if scene_id not in self.persona.scenes:
            raise ValueError(f"没有这个场景：{scene_id}")
        self.scene_override = scene_id

    @property
    def active_scene(self) -> str:
        if self.scene_override and self.scene_override in self.persona.scenes:
            return self.scene_override
        if self.persona.current_scene in self.persona.scenes:
            return self.persona.current_scene
        if self.persona.scenes:
            return next(iter(self.persona.scenes))
        return self.persona.current_scene

    def system_prompt(self) -> str:
        return self.persona.build_system_prompt(self.active_scene)

    def list_scenes(self) -> list[tuple[str, str]]:
        return self.persona.list_scenes()

    def _load(self) -> Persona:
        if not self.character_path.exists():
            raise FileNotFoundError(
                f"找不到人设文件：{self.character_path}"
            )

        data = yaml.safe_load(
            self.character_path.read_text(encoding="utf-8")
        ) or {}

        if not isinstance(data, dict):
            raise ValueError("character.yaml 格式不对，最外层应当是一组字段。")

        yaml_memory = _as_str(data.get("memory"))
        file_memory = _read_memory_file(self.memory_path)
        memory = "\n".join(
            part for part in (yaml_memory, file_memory) if part
        )

        scenes = data.get("scenes") or {}
        if not isinstance(scenes, dict):
            raise ValueError("character.yaml 里的 scenes 应当是一组场景。")

        return Persona(
            name=_as_str(data.get("name"), "姐姐"),
            app_name=_as_str(data.get("app_name"), "温柔姐姐桌宠"),
            identity=_as_list(data.get("identity")),
            personality=_as_list(data.get("personality")),
            core_obsessions=_as_list(
                data.get("core_obsessions") or data.get("obsessions")
            ),
            speech_style=_as_list(data.get("speech_style")),
            relationships=_relationship_lines(data.get("relationships") or {}),
            world=_world_lines(data.get("world") or data.get("worldview")),
            scenes=scenes,
            current_scene=_as_str(data.get("current_scene"), "desktop"),
            rules=_as_list(data.get("rules")),
            memory=memory,
            input_placeholder=_as_str(
                data.get("input_placeholder"),
                "和姐姐说点什么吧……",
            ),
            sleep_line=_as_str(
                data.get("sleep_line"),
                "呼……先睡一会儿……",
            ),
            double_click_line=_as_str(
                data.get("double_click_line"),
                "双击我做什么呀？\n难道是想和姐姐多待一会儿？",
            ),
            greet_line=_as_str(
                data.get("greet_line"),
                "今天也辛苦啦，有什么想和姐姐聊聊的吗？",
            ),
            click_reactions=_as_list(data.get("click_reactions")),
            idle_messages=_as_list(data.get("idle_messages")),
        )


def _section(title: str, items: list[str]) -> str:
    if not items:
        return ""
    body = "\n".join(f"- {item}" for item in items)
    return f"{title}\n{body}"
