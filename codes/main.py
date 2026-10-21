# codes/main.py

import sys

from PySide6.QtWidgets import QApplication

from api_client import DeepSeekClient
from pet_window import PetWindow


def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "温柔姐姐桌宠"
    )

    app.setQuitOnLastWindowClosed(
        False
    )

    # --------------------------------------------------------
    # 创建 AI
    # --------------------------------------------------------

    try:

        api_client = DeepSeekClient()

    except Exception as e:

        print(e)

        return 1

    # --------------------------------------------------------
    # 创建桌宠
    # --------------------------------------------------------

    window = PetWindow(
        api_client
    )

    # 默认放到屏幕右下角
    screen = (
        app.primaryScreen()
        .availableGeometry()
    )

    x = (
        screen.right()
        - window.width()
        - 30
    )

    y = (
        screen.bottom()
        - window.height()
        - 30
    )

    window.move(
        x,
        y,
    )

    window.show()

    # --------------------------------------------------------
    # 启动
    # --------------------------------------------------------

    return app.exec()


if __name__ == "__main__":
    sys.exit(
        main()
    )
