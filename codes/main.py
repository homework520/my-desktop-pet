# codes/main.py

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from api_client import DeepSeekClient
from persona import PersonaStore
from pet_window import PetWindow


def main():

    app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(
        False
    )

    # --------------------------------------------------------
    # 创建人设与 AI
    # --------------------------------------------------------

    try:

        persona = PersonaStore()
        api_client = DeepSeekClient(persona)

    except Exception as e:

        print(e)
        QMessageBox.critical(
            None,
            "启动失败",
            str(e),
        )
        return 1

    app.setApplicationName(
        persona.persona.app_name
    )

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
