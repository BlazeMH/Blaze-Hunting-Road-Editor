# ui/utils.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPalette, QBrush
from core.paths import resource_path

def apply_dialog_background(dialog, image_name="bg3.jpg", opacity=0.65):
    """
    Paint a scaled background image on a QDialog (resizes with the dialog).
    """
    # enable palette painting
    dialog.setAutoFillBackground(True)

    # load & scale
    pix = QPixmap(str(resource_path("asset", image_name)))
    if pix.isNull():
        return  # silently skip if missing

    scaled = pix.scaled(dialog.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    # optional opacity: precompose onto a temp pixmap
    if 0.0 <= opacity < 1.0:
        tmp = QPixmap(scaled.size())
        tmp.fill(Qt.transparent)
        from PySide6.QtGui import QPainter
        p = QPainter(tmp)
        p.setOpacity(opacity)
        p.drawPixmap(0, 0, scaled)
        p.end()
        scaled = tmp

    pal = dialog.palette()
    pal.setBrush(QPalette.Window, QBrush(scaled))
    dialog.setPalette(pal)

    # attach a lightweight resize handler so it keeps fitting
    if not hasattr(dialog, "_bg_resize_installed"):
        dialog._bg_resize_installed = True
        orig_resize = dialog.resizeEvent
        def _resizeEvent(e):
            apply_dialog_background(dialog, image_name=image_name, opacity=opacity)
            if callable(orig_resize):
                orig_resize(e)
        dialog.resizeEvent = _resizeEvent
