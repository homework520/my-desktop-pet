# codes/utils.py

from pathlib import Path


def load_image_path(path: Path):
    """
    检查图片是否存在。
    """

    if not path.exists():
        raise FileNotFoundError(
            f"找不到桌宠图片：{path}"
        )

    return str(path)
