from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from qt_models import VisibleCell


class MazeCanvas(QWidget):
    """
    Arcade-styled maze renderer for the Nuovo Fresco pipe network.

    This widget is pure presentation:
    - it does not know about GameEngine
    - it does not know about db.py
    - it does not compute maze logic
    - it only draws the VisibleCell grid it receives
    """

    BG_COLOR = QColor("#140f1d")
    GRID_FRAME = QColor("#2df0ff")
    FRAME_ACCENT = QColor("#7c5cff")
    SIDE_GLOW_LEFT = QColor("#2df0ff")
    SIDE_GLOW_RIGHT = QColor("#ff4fd8")

    HIDDEN_FILL = QColor("#2b2436")
    HIDDEN_INNER = QColor("#1c1724")

    FLOOR_FILL = QColor("#1f3b2e")
    FLOOR_INNER = QColor("#29543f")

    VISITED_FILL = QColor("#245e7a")
    VISITED_INNER = QColor("#2f86a8")

    CURRENT_FILL = QColor("#ffd33d")
    CURRENT_INNER = QColor("#ffe97a")

    EXIT_FILL = QColor("#36d96f")
    EXIT_INNER = QColor("#7df5a6")

    ENTRY_FILL = QColor("#8c52ff")
    ENTRY_INNER = QColor("#b084ff")

    CLOG_FILL = QColor("#d64747")
    CLOG_INNER = QColor("#ff7a59")

    WALL_COLOR = QColor("#0b0b0f")
    TEXT_COLOR = QColor("#f7f3ff")
    SHADOW_COLOR = QColor(0, 0, 0, 90)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cells: list[list[VisibleCell]] = []
        self.setMinimumSize(520, 520)
        self.setAutoFillBackground(False)

    def set_cells(self, cells: list[list[VisibleCell]]) -> None:
        self._cells = cells
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(self.rect(), self.BG_COLOR)
        self._draw_backdrop(painter)

        if not self._cells or not self._cells[0]:
            self._draw_empty_state(painter)
            return

        rows = len(self._cells)
        cols = len(self._cells[0])

        margin = 24
        usable_width = max(1, self.width() - (2 * margin))
        usable_height = max(1, self.height() - (2 * margin))
        cell_size = min(usable_width / cols, usable_height / rows)

        grid_width = cols * cell_size
        grid_height = rows * cell_size
        origin_x = (self.width() - grid_width) / 2.0
        origin_y = (self.height() - grid_height) / 2.0

        frame_rect = QRectF(
            origin_x - 8,
            origin_y - 8,
            grid_width + 16,
            grid_height + 16,
        )
        self._draw_grid_frame(painter, frame_rect)

        for row_index, row in enumerate(self._cells):
            for col_index, cell in enumerate(row):
                x = origin_x + (col_index * cell_size)
                y = origin_y + (row_index * cell_size)
                rect = QRectF(x, y, cell_size, cell_size)
                self._draw_cell(painter, rect, cell)

        self._draw_corner_fills(painter, origin_x, origin_y, cell_size)

    def _cell_stripe_thickness(self, cell: VisibleCell, cell_size: float) -> float:
        """Compute the highlight stripe thickness for a cell, matching _draw_cell."""
        pad = 5.0
        closed_n = cell.north_open is False or not cell.is_visible
        closed_s = cell.south_open is False or not cell.is_visible
        inset_h = cell_size - (pad if closed_n else 0) - (pad if closed_s else 0)
        return max(4.0, inset_h * 0.14)

    def _draw_corner_fills(
        self,
        painter: QPainter,
        origin_x: float,
        origin_y: float,
        cell_size: float,
    ) -> None:
        """Fill corner highlights where walls from neighboring cells meet.

        Positioned 5px inward from the shared edges so the highlight
        aligns with the neighbor stripe positions, with border lines
        on the two outward-facing sides to match the wall framing.
        """
        rows = len(self._cells)
        cols = len(self._cells[0])
        highlight_color = QColor(255, 255, 255, 55)
        border_pen = QPen(QColor("#050507"), 2)
        pad = 5.0

        for r in range(rows):
            for c in range(cols):
                cell = self._cells[r][c]
                if not cell.is_visible:
                    continue

                cx = origin_x + c * cell_size
                cy = origin_y + r * cell_size

                # NW corner: passage goes west and north
                if cell.north_open is True and cell.west_open is True:
                    if c > 0 and r > 0:
                        w_cell = self._cells[r][c - 1]
                        n_cell = self._cells[r - 1][c]
                        if w_cell.north_open is False and n_cell.west_open is False:
                            cw = self._cell_stripe_thickness(n_cell, cell_size)
                            ch = self._cell_stripe_thickness(w_cell, cell_size)
                            w_outer, _ = self._cell_colors(w_cell)
                            n_outer, _ = self._cell_colors(n_cell)
                            painter.fillRect(QRectF(cx, cy, pad, pad + ch), w_outer)
                            painter.fillRect(QRectF(cx, cy, pad + cw, pad), n_outer)
                            painter.fillRect(QRectF(cx + pad, cy + pad, cw, ch), highlight_color)
                            painter.setPen(border_pen)
                            painter.drawLine(QPointF(cx, cy), QPointF(cx, cy + pad))
                            painter.drawLine(QPointF(cx, cy), QPointF(cx + pad, cy))

                # NE corner: passage goes east and north
                if cell.north_open is True and cell.east_open is True:
                    if c < cols - 1 and r > 0:
                        e_cell = self._cells[r][c + 1]
                        n_cell = self._cells[r - 1][c]
                        if e_cell.north_open is False and n_cell.east_open is False:
                            cw = self._cell_stripe_thickness(n_cell, cell_size)
                            ch = self._cell_stripe_thickness(e_cell, cell_size)
                            e_outer, _ = self._cell_colors(e_cell)
                            n_outer, _ = self._cell_colors(n_cell)
                            rx = cx + cell_size - pad
                            painter.fillRect(QRectF(rx, cy, pad, pad + ch), e_outer)
                            painter.fillRect(QRectF(rx - cw, cy, pad + cw, pad), n_outer)
                            painter.fillRect(QRectF(rx - cw, cy + pad, cw, ch), highlight_color)
                            painter.setPen(border_pen)
                            painter.drawLine(
                                QPointF(cx + cell_size, cy),
                                QPointF(cx + cell_size, cy + pad),
                            )
                            painter.drawLine(
                                QPointF(cx + cell_size - pad, cy),
                                QPointF(cx + cell_size, cy),
                            )

                # SW corner: passage goes west and south
                if cell.south_open is True and cell.west_open is True:
                    if c > 0 and r < rows - 1:
                        w_cell = self._cells[r][c - 1]
                        s_cell = self._cells[r + 1][c]
                        if w_cell.south_open is False and s_cell.west_open is False:
                            cw = self._cell_stripe_thickness(s_cell, cell_size)
                            ch = self._cell_stripe_thickness(w_cell, cell_size)
                            w_outer, _ = self._cell_colors(w_cell)
                            s_outer, _ = self._cell_colors(s_cell)
                            by = cy + cell_size - pad
                            painter.fillRect(QRectF(cx, by - ch, pad, pad + ch), w_outer)
                            painter.fillRect(QRectF(cx, by, pad + cw, pad), s_outer)
                            painter.fillRect(QRectF(cx + pad, by - ch, cw, ch), highlight_color)
                            painter.setPen(border_pen)
                            painter.drawLine(
                                QPointF(cx, cy + cell_size - pad),
                                QPointF(cx, cy + cell_size),
                            )
                            painter.drawLine(
                                QPointF(cx, cy + cell_size),
                                QPointF(cx + pad, cy + cell_size),
                            )

                # SE corner: passage goes east and south
                if cell.south_open is True and cell.east_open is True:
                    if c < cols - 1 and r < rows - 1:
                        e_cell = self._cells[r][c + 1]
                        s_cell = self._cells[r + 1][c]
                        if e_cell.south_open is False and s_cell.east_open is False:
                            cw = self._cell_stripe_thickness(s_cell, cell_size)
                            ch = self._cell_stripe_thickness(e_cell, cell_size)
                            e_outer, _ = self._cell_colors(e_cell)
                            s_outer, _ = self._cell_colors(s_cell)
                            rx = cx + cell_size - pad
                            by = cy + cell_size - pad
                            painter.fillRect(QRectF(rx, by - ch, pad, pad + ch), e_outer)
                            painter.fillRect(QRectF(rx - cw, by, pad + cw, pad), s_outer)
                            painter.fillRect(QRectF(rx - cw, by - ch, cw, ch), highlight_color)
                            painter.setPen(border_pen)
                            painter.drawLine(
                                QPointF(cx + cell_size, cy + cell_size - pad),
                                QPointF(cx + cell_size, cy + cell_size),
                            )
                            painter.drawLine(
                                QPointF(cx + cell_size - pad, cy + cell_size),
                                QPointF(cx + cell_size, cy + cell_size),
                            )

    def _draw_backdrop(self, painter: QPainter) -> None:
        painter.save()

        rail_pen = QPen(QColor("#251d31"), 3)
        painter.setPen(rail_pen)
        for y in range(20, self.height(), 36):
            painter.drawLine(0, y, self.width(), y)

        painter.fillRect(0, 0, 12, self.height(), self.SIDE_GLOW_LEFT)
        painter.fillRect(self.width() - 12, 0, 12, self.height(), self.SIDE_GLOW_RIGHT)

        painter.restore()

    def _draw_grid_frame(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()

        shadow_rect = QRectF(rect.left() + 6, rect.top() + 6, rect.width(), rect.height())
        painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 10, 10)

        painter.setBrush(QBrush(QColor("#20182a")))
        painter.setPen(QPen(self.GRID_FRAME, 4))
        painter.drawRoundedRect(rect, 10, 10)

        inner = rect.adjusted(6, 6, -6, -6)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self.FRAME_ACCENT, 2))
        painter.drawRoundedRect(inner, 8, 8)

        painter.restore()

    def _draw_empty_state(self, painter: QPainter) -> None:
        painter.save()

        rect = self.rect().adjusted(40, 40, -40, -40)
        painter.setBrush(QBrush(QColor("#20182a")))
        painter.setPen(QPen(self.GRID_FRAME, 3))
        painter.drawRoundedRect(rect, 12, 12)

        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(self.TEXT_COLOR, 1))
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            "PIPE GRID LOADING...",
        )

        painter.restore()

    def _draw_cell(self, painter: QPainter, rect: QRectF, cell: VisibleCell) -> None:
        painter.save()
        painter.setClipRect(rect)

        outer_fill, inner_fill = self._cell_colors(cell)

        painter.setBrush(QBrush(outer_fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)

        closed_n = cell.north_open is False or not cell.is_visible
        closed_s = cell.south_open is False or not cell.is_visible
        closed_w = cell.west_open is False or not cell.is_visible
        closed_e = cell.east_open is False or not cell.is_visible

        inset = rect.adjusted(
            5 if closed_w else 0,
            5 if closed_n else 0,
            -5 if closed_e else 0,
            -5 if closed_s else 0,
        )
        painter.setBrush(QBrush(inner_fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(inset)

        border_pen = QPen(QColor("#050507"), 2)
        painter.setPen(border_pen)
        if closed_n:
            painter.drawLine(QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.top()))
        if closed_s:
            painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
        if closed_w:
            painter.drawLine(QPointF(rect.left(), rect.top()), QPointF(rect.left(), rect.bottom()))
        if closed_e:
            painter.drawLine(QPointF(rect.right(), rect.top()), QPointF(rect.right(), rect.bottom()))

        if cell.is_visible:
            highlight_color = QColor(255, 255, 255, 55)
            thickness = max(4.0, inset.height() * 0.14)
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            if cell.north_open is False:
                path.addRect(QRectF(
                    inset.left(), inset.top(),
                    inset.width(), thickness,
                ))
            if cell.south_open is False:
                path.addRect(QRectF(
                    inset.left(), inset.bottom() - thickness,
                    inset.width(), thickness,
                ))
            if cell.west_open is False:
                path.addRect(QRectF(
                    inset.left(), inset.top(),
                    thickness, inset.height(),
                ))
            if cell.east_open is False:
                path.addRect(QRectF(
                    inset.right() - thickness, inset.top(),
                    thickness, inset.height(),
                ))
            if not path.isEmpty():
                painter.fillPath(path, highlight_color)

        if cell.is_visible and cell.has_clog:
            self._draw_hazard_stripes(painter, inset)

        self._draw_walls(painter, rect, cell)
        self._draw_player_marker(painter, rect, cell)
        self._draw_label(painter, rect, cell)

        painter.restore()

    def _cell_colors(self, cell: VisibleCell) -> tuple[QColor, QColor]:
        if not cell.is_visible:
            return self.HIDDEN_FILL, self.HIDDEN_INNER
        if cell.is_current:
            return self.CURRENT_FILL, self.CURRENT_INNER
        if cell.is_exit_drain:
            return self.EXIT_FILL, self.EXIT_INNER
        if cell.is_entry_valve:
            return self.ENTRY_FILL, self.ENTRY_INNER
        if cell.has_clog:
            return self.CLOG_FILL, self.CLOG_INNER
        if cell.is_visited:
            return self.VISITED_FILL, self.VISITED_INNER
        return self.FLOOR_FILL, self.FLOOR_INNER

    def _draw_hazard_stripes(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()

        stripe_pen = QPen(QColor("#2a120f"), 3)
        painter.setPen(stripe_pen)

        step = max(8, int(rect.width() / 5))
        x = int(rect.left()) - int(rect.height())
        while x < int(rect.right()) + int(rect.height()):
            painter.drawLine(
                QPointF(x, rect.bottom()),
                QPointF(x + rect.height(), rect.top()),
            )
            x += step

        painter.restore()

    def _draw_walls(self, painter: QPainter, rect: QRectF, cell: VisibleCell) -> None:
        if not cell.is_visible:
            return

        wall_pen = QPen(self.WALL_COLOR, 5)
        painter.setPen(wall_pen)

        left = rect.left()
        right = rect.right()
        top = rect.top()
        bottom = rect.bottom()

        if cell.north_open is False:
            painter.drawLine(QPointF(left, top), QPointF(right, top))
        if cell.south_open is False:
            painter.drawLine(QPointF(left, bottom), QPointF(right, bottom))
        if cell.west_open is False:
            painter.drawLine(QPointF(left, top), QPointF(left, bottom))
        if cell.east_open is False:
            painter.drawLine(QPointF(right, top), QPointF(right, bottom))

    def _draw_player_marker(self, painter: QPainter, rect: QRectF, cell: VisibleCell) -> None:
        if not cell.is_current:
            return

        painter.save()

        radius = min(rect.width(), rect.height()) * 0.16
        center = rect.center()

        shadow_rect = QRectF(
            center.x() - radius + 2,
            center.y() - radius + 3,
            radius * 2,
            radius * 2,
        )
        painter.setBrush(QBrush(self.SHADOW_COLOR))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(shadow_rect)

        marker_rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
        painter.setBrush(QBrush(QColor("#1f5fff")))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(marker_rect)

        painter.restore()

    def _draw_label(self, painter: QPainter, rect: QRectF, cell: VisibleCell) -> None:
        if not cell.is_visible:
            return

        label = ""
        if cell.is_entry_valve:
            label = "IN"
        elif cell.is_exit_drain:
            label = "OUT"
        elif cell.has_clog:
            label = "X"

        if not label:
            return

        painter.save()

        font_size = max(7, int(rect.width() / 6))
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        painter.setFont(font)

        shadow_rect = rect.adjusted(2, 2, 2, 2)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.setPen(QPen(self.TEXT_COLOR, 1))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.restore()