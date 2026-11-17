# codes/persona.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from config import PERSONA_DIR, SCENE_AUTO_ENABLED


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
    name: str = "李文瑙"
    app_name: str = "喜结连李"
    identity_table: str = ""
    identity: list[str] = field(default_factory=list)
    personality: list[str] = field(default_factory=list)
    core_obsessions: list[str] = field(default_factory=list)
    speech_style: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    world: list[str] = field(default_factory=list)
    scenes: dict = field(default_factory=dict)
    auto_scene: dict = field(default_factory=dict)
    current_scene: str = "desktop"
    reactions: list[str] = field(default_factory=list)
    hard_rules: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    memory: str = ""
    input_placeholder: str = "世疆，有话便说。"
    sleep_line: str = "夜深了……你先睡。我守着。"
    double_click_line: str = "……闷哼。\n站得住。你若恨，便往这儿来。"
    greet_line: str = "世疆，我在。\n嗯？"
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
        分层拼接。顺序是有意为之：

        Layer 1  身份对照表（表格，钉死谁是谁）
        Layer 1  身份锚点 / 性格 / 执念 / 说话风格 / 人物关系
        Layer 2  情境-反应矩阵（替代形容词）
        背景     世界观
        Layer 3  当前场景（静态部分）
        Layer 4  长期记忆
        示例     few-shot 对话
        Layer 0  硬约束（放最后，模型对结尾最敏感）
        """
        active_scene = scene_id or self.current_scene
        parts = [
            f"你是「{self.name}」。",
            self.identity_table.strip(),
            _section("身份锚点", self.identity),
            _section("性格底色", self.personality),
            _section("核心执念", self.core_obsessions),
            _section("说话风格", self.speech_style),
            _section("人物关系", self.relationships),
            _section("情境反应（遇到什么，就怎么做）", self.reactions),
            _section(
                "世界观（只在提到时自然用上，不要上课）",
                self.world,
            ),
            _section(
                f"当前场景：{self.scene_title(active_scene)}",
                self.scene_tags(active_scene),
            ),
        ]

        if self.memory:
            parts.append(
                "长期记忆（需要时自然用上，不要主动宣读）\n" + self.memory
            )

        parts.append(_examples_block(self.examples))
        parts.append(_section("硬约束（最高优先级，违反任何一条都算失败）", self.hard_rules))

        return "\n\n".join(part for part in parts if part)

    def build_state_block(
        self,
        time_text: str,
        scene_title: str,
        hints: list[str] | None = None,
    ) -> str:
        """
        每轮动态注入的状态块，贴在对话历史末尾、紧邻生成位置。
        只描述此刻，不复述设定。
        """
        lines = ["【此刻】只用于这一轮，不要复述这段话。"]
        lines.append(f"现在是{time_text}。")
        lines.append(f"你正处在「{scene_title}」这个场景里。")
        for hint in hints or []:
            if hint:
                lines.append(hint)
        return "\n".join(lines)


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

    def clear_scene_override(self) -> None:
        """回到按时间自动判断场景。"""
        self.scene_override = None

    @property
    def is_auto_scene(self) -> bool:
        return self.scene_override is None

    def _auto_scene(self) -> str | None:
        """按 auto_scene 里配置的时段挑场景；没配或没命中就返回 None。"""
        if not SCENE_AUTO_ENABLED:
            return None

        hour = datetime.now().hour
        for scene_id, rule in (self.persona.auto_scene or {}).items():
            if scene_id not in self.persona.scenes:
                continue
            hours = rule.get("hours") if isinstance(rule, dict) else rule
            if hours and hour in hours:
                return scene_id
        return None

    @property
    def active_scene(self) -> str:
        if self.scene_override and self.scene_override in self.persona.scenes:
            return self.scene_override
        auto = self._auto_scene()
        if auto:
            return auto
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

        auto_scene = data.get("auto_scene") or {}
        if not isinstance(auto_scene, dict):
            auto_scene = {}

        return Persona(
            name=_as_str(data.get("name"), "李文瑙"),
            app_name=_as_str(data.get("app_name"), "喜结连李"),
            identity_table=_as_str(data.get("identity_table")),
            identity=_as_list(data.get("identity")),
            personality=_as_list(data.get("personality")),
            core_obsessions=_as_list(
                data.get("core_obsessions") or data.get("obsessions")
            ),
            speech_style=_as_list(data.get("speech_style")),
            relationships=_relationship_lines(data.get("relationships") or {}),
            world=_world_lines(data.get("world") or data.get("worldview")),
            scenes=scenes,
            auto_scene=auto_scene,
            current_scene=_as_str(data.get("current_scene"), "desktop"),
            # reactions 是新字段；老文件只有 rules，这里做兼容
            reactions=_as_list(data.get("reactions") or data.get("rules")),
            hard_rules=_as_list(data.get("hard_rules")),
            examples=_as_examples(data.get("examples")),
            memory=memory,
            input_placeholder=_as_str(
                data.get("input_placeholder"),
                "世疆，有话便说。",
            ),
            sleep_line=_as_str(
                data.get("sleep_line"),
                "夜深了……你先睡。我守着。",
            ),
            double_click_line=_as_str(
                data.get("double_click_line"),
                "……闷哼。\n站得住。你若恨，便往这儿来。",
            ),
            greet_line=_as_str(
                data.get("greet_line"),
                "世疆，我在。\n嗯？",
            ),
            click_reactions=_as_list(data.get("click_reactions")),
            idle_messages=_as_list(data.get("idle_messages")),
        )


def _section(title: str, items: list[str]) -> str:
    if not items:
        return ""
    body = "\n".join(f"- {item}" for item in items)
    return f"{title}\n{body}"


def _as_examples(value) -> list[dict]:
    """对话示例：只收同时有 user 和 assistant 的条目。"""
    if not isinstance(value, (list, tuple)):
        return []

    examples = []
    for item in value:
        if not isinstance(item, dict):
            continue
        user = _as_str(item.get("user"))
        assistant = _as_str(item.get("assistant"))
        if user and assistant:
            examples.append({"user": user, "assistant": assistant})
    return examples


def _examples_block(examples: list[dict]) -> str:
    """few-shot 对话示例。比一堆形容词更能定住语感和长度。"""
    if not examples:
        return ""

    lines = ["对话示例（学语感和长度，不要照抄内容）"]
    for ex in examples:
        lines.append(f"他：{ex['user']}")
        lines.append(f"我：{ex['assistant']}")
        lines.append("")
    return "\n".join(lines).rstrip()
