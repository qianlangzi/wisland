"""离屏验证贴边轮廓与空闲后台线程，不启动桌面窗口。"""

import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui

from wisland.ui.glass import Backdrop
from wisland.ui.shape import anchored_path, body_path, edge_corners, neck_path


class RenderingTests(unittest.TestCase):
    def test_direct_outline_preserves_all_four_edges(self):
        for edge in ("top", "bottom", "left", "right"):
            for expanded in (False, True):
                with self.subTest(edge=edge, expanded=expanded):
                    width, height = (320, 260) if expanded else (260, 50)
                    if edge in ("left", "right"):
                        width, height = height, width
                    rect = QtCore.QRectF(60, 60, width, height)
                    radius = min(width / 2, height / 2, 30)
                    radii = tuple(0 if near else radius for near in edge_corners(edge))
                    line = {
                        "top": rect.top(),
                        "bottom": rect.bottom(),
                        "left": rect.left(),
                        "right": rect.right(),
                    }[edge]
                    horiz = edge in ("top", "bottom")
                    center = rect.center().x() if horiz else rect.center().y()
                    length = width if horiz else height
                    old = body_path(rect, radii).united(neck_path(edge, line, center, length, 0, 0, 1, 13, 0))
                    new = anchored_path(rect, edge, 13, radius)
                    self.assertEqual(old.boundingRect(), new.boundingRect())
                    self.assertLess(new.elementCount(), old.elementCount())
                    images = []
                    for path in (old, new):
                        image = QtGui.QImage(450, 450, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
                        image.fill(0)
                        painter = QtGui.QPainter(image)
                        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
                        painter.fillPath(path, QtGui.QColor("white"))
                        painter.end()
                        images.append(bytes(image.constBits()))
                    difference = sum(abs(a - b) for a, b in zip(*images)) / len(images[0])
                    self.assertLess(difference, 0.25)

    def test_backdrop_waits_without_a_capture_request(self):
        backdrop = Backdrop()
        with patch.object(backdrop._wake, "wait", wraps=backdrop._wake.wait) as wait:
            backdrop.start()
            try:
                time.sleep(0.05)
            finally:
                backdrop.stop()
                backdrop._thread.join(timeout=1)
            self.assertFalse(backdrop._thread.is_alive())
            self.assertLessEqual(wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
