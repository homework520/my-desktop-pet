# 桌宠

Windows 桌面宠物。无边框透明窗口停在桌面上，可以用 DeepSeek 聊天，也有点击、闲聊和睡觉等本地互动。

人设和 API 密钥都不写在代码里：密钥放 `.env`，人设放 `persona/`，改完保存即可。

## 功能

- 无边框透明窗口，可拖动、置顶、藏进托盘
- DeepSeek 多轮对话，气泡按 Galgame 打字机效果逐句显示
- 单击 / 双击角色、超时主动说话、超时睡觉
- 人设用标签拼接：身份、性格、执念、说话风格、人物关系
- 场景模块可切换，规则写「遇到什么情况怎么做」
- 长期记忆可写在 `persona/memory.md`

## 安装与运行

需要 Python 3.10 或更高版本。

1. 双击 `install.bat`，创建虚拟环境并安装依赖。
2. 复制 `.env.example` 为 `.env`，填上自己的 DeepSeek 密钥：

```env
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

3. 双击 `run.bat` 启动。

打包成 exe 可以双击 `pack.bat`。输出在 `dist/温柔姐姐桌宠/`。把 `.env` 放到 exe 同级目录；若要改人设，把 `persona` 文件夹也放到 exe 同级，程序会优先读这一份。

## API 密钥

密钥只从环境变量 / `.env` 读取，不要写进 `codes/config.py`。

- `.env` 已被 `.gitignore` 忽略，不要提交，也不要发给别人。
- 如果这把密钥曾经出现在源码或聊天记录里，建议到 DeepSeek 控制台轮换一把新的。

## 怎么改人设

主要改这两个文件：

| 文件 | 作用 |
|---|---|
| `persona/character.yaml` | 基础人设、场景、规则、本地台词 |
| `persona/memory.md` | 长期记忆（模块 C） |

保存后不必重启。下次对话会自动重读；也可以右键桌宠选「重载人设」。右键「切换场景」只对当前这次运行生效，重启后仍以 yaml 里的 `current_scene` 为准。

写法按「给标签，不给流水账」：不要写「六岁丧母，十岁进贾府……」，改成几条能让模型自己脑补的锚点。

### 模块 A：基础人设（每次必带）

在 `character.yaml` 里改这些字段：

- `identity`：身份锚点
- `personality`：性格底色
- `core_obsessions`：核心执念
- `speech_style`：说话风格
- `relationships`：已知人物关系

### 世界观：地理与背景（每次必带）

写在 `character.yaml` 的 `world`，不要塞进身份或场景。

- 这里写「世界长什么样」：时代格局、几个地名、彼此方位
- 仍用标签，不要写成地理志
- 「现在人在哪、在干什么」留给 `scenes`

```yaml
world:
  - 格局：……
  - 陇平：西陲边郡，世子封地
  - 京城：朝堂所在
  - 地理：陇平在西，入京东行
```

地点多了以后，也可以按组写：

```yaml
world:
  overview:
    - 格局：……
  places:
    陇平:
      - 西陲边郡
    京城:
      - 朝堂所在
  geography:
    - 陇平在西，入京东行
```

### 模块 B：当前场景（按需替换）

在 `scenes` 下准备多套场景，用 `current_scene` 指定默认那一套。例如桌面陪伴、夜深了、歇一会儿。每次对话只带当前这一份，不用把人生经历一次塞完。

### 模块 C：动态记忆

两层一起用：

1. 最近若干轮对话由程序自动带着（`MAX_HISTORY` 在 `codes/config.py`）。
2. 想额外钉住的事写进 `persona/memory.md`，或以 `#` 开头的行不会发给模型。也可以在 yaml 里加一段 `memory:`。

### 规则：写「怎么做」，不要写百科

与其告诉模型发生过什么，不如告诉它遇到什么情况该怎么做。例如：

```yaml
rules:
  - 用户心情低落时：先接住情绪，少讲大道理。
  - 用户夸你时：不要急着客套致谢，自然、带一点从容地接住。
  - 不要输出 Markdown。
```

### 本地台词

单击反应、闲聊、睡觉、输入框提示等不走 API，同样写在 `character.yaml`：

- `click_reactions`
- `idle_messages`
- `sleep_line`
- `double_click_line`
- `greet_line`
- `input_placeholder`

## 项目结构

```text
table_pet/
  .env.example          # 密钥模板
  install.bat           # 安装依赖
  run.bat               # 启动
  pack.bat              # 打包
  persona/
    character.yaml      # 人设、场景、规则、本地台词
    memory.md           # 长期记忆
  pictures/finally/     # 待机 / 说话 / 睡觉立绘
  codes/
    main.py             # 入口
    pet_window.py       # 窗口、托盘、互动
    dialogue.py         # 打字机气泡
    api_client.py       # DeepSeek 客户端
    persona.py          # 人设读取与模块拼接
    config.py           # 路径和界面参数（不含密钥）
```

右键菜单还可以清空聊天记忆、切换置顶和自动陪伴、隐藏或退出桌宠。
