"""PyInstaller entry point; keep package imports absolute."""

import json
from pathlib import Path
import sys


def verify_startup(path):
    from PySide6.QtCore import QTimer, qVersion
    from PySide6.QtWidgets import QApplication
    from zijinhua_tekla.gui.report_gui import ReportGUI

    app = QApplication([])
    window = ReportGUI()
    window.show()

    def finish():
        Path(path).write_text(json.dumps({
            "qt_version": qVersion(), "qt_platform": app.platformName(),
            "window_visible": window.isVisible(), "modules": window.tabs.count(),
        }), encoding="utf-8")
        window.close()
        app.quit()

    QTimer.singleShot(250, finish)
    return app.exec()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-startup":
        raise SystemExit(verify_startup(sys.argv[2]))
    from zijinhua_tekla.gui.report_gui import main
    raise SystemExit(main())
