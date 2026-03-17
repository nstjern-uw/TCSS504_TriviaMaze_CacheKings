from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qt_controller import QtGameController
from qt_models import GameViewState
from widgets.maze_canvas import MazeCanvas


APP_STYLE = """
QMainWindow {
    background-color: #140f1d;
}

QWidget {
    color: #f7f3ff;
    font-family: Arial;
    font-size: 11pt;
}

QLabel#TitleLabel {
    font-size: 24pt;
    font-weight: 900;
    color: #ffe15c;
    letter-spacing: 1px;
}

QLabel#SubtitleLabel {
    font-size: 11pt;
    font-weight: 700;
    color: #2df0ff;
}

QLabel#FeedLabel {
    background-color: #20182a;
    border: 3px solid #ff4fd8;
    border-radius: 10px;
    padding: 10px;
    font-size: 11pt;
    font-weight: 700;
    color: #fff3c6;
}

QLabel#LegendLabel {
    background-color: #20182a;
    border: 2px solid #7c5cff;
    border-radius: 8px;
    padding: 8px;
    color: #d7d3ff;
    font-size: 10pt;
}

QGroupBox {
    background-color: #1a1423;
    border: 3px solid #2df0ff;
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 900;
    color: #ffe15c;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 0 6px;
    color: #ffe15c;
}

QPushButton {
    background-color: #2a2038;
    color: #f7f3ff;
    border: 3px solid #2df0ff;
    border-radius: 10px;
    padding: 10px;
    font-size: 11pt;
    font-weight: 900;
}

QPushButton:hover {
    background-color: #3a2a4b;
    border-color: #ffe15c;
}

QPushButton:pressed {
    background-color: #1a1524;
}

QPushButton:disabled {
    background-color: #221c2b;
    color: #786f88;
    border-color: #4b4257;
}

QLabel#ValueLabel {
    color: #ffffff;
    font-weight: 800;
}

QLabel#QuestionPrompt {
    background-color: #241a2f;
    border: 2px solid #ff7a59;
    border-radius: 8px;
    padding: 10px;
    color: #fff2da;
    font-weight: 700;
}
"""


class MainWindow(QMainWindow):
    def __init__(self, controller: QtGameController) -> None:
        super().__init__()
        self.controller = controller
        self._last_end_state: str | None = None

        self.setWindowTitle("Nuovo Fresco // Pipe Strike")
        self.resize(1280, 820)

        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        self.move(x, 50)
        self.setStyleSheet(APP_STYLE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.title_label = QLabel("NUOVO FRESCO // PIPE STRIKE")
        self.title_label.setObjectName("TitleLabel")

        self.subtitle_label = QLabel(
            "Retro sewer action for the toughest plumber in town."
        )
        self.subtitle_label.setObjectName("SubtitleLabel")

        self.feed_label = QLabel("City pressure is unstable. Time to hit the pipes.")
        self.feed_label.setObjectName("FeedLabel")
        self.feed_label.setWordWrap(True)

        self.legend_label = QLabel(self.controller.help_text)
        self.legend_label.setObjectName("LegendLabel")
        self.legend_label.setWordWrap(True)

        self.canvas = MazeCanvas()

        self.phase_value = self._make_value_label()
        self.status_value = self._make_value_label()
        self.position_value = self._make_value_label()
        self.pressure_value = self._make_value_label()
        self.clogs_value = self._make_value_label()
        self.level_value = self._make_value_label()
        self.questions_value = self._make_value_label()
        self.accuracy_value = self._make_value_label()

        self.north_button = QPushButton("NORTH")
        self.south_button = QPushButton("SOUTH")
        self.east_button = QPushButton("EAST")
        self.west_button = QPushButton("WEST")

        self.answer_buttons = [
            QPushButton("A"),
            QPushButton("B"),
            QPushButton("C"),
            QPushButton("D"),
        ]
        self.blast_button = QPushButton("HYDRO BLAST")

        self.new_game_button = QPushButton("NEW SHIFT")
        self.save_button = QPushButton("SAVE")
        self.load_button = QPushButton("LOAD")
        self.help_button = QPushButton("HELP")
        self.retreat_button = QPushButton("RETREAT")

        self.question_prompt = QLabel("No active pipe hazard.")
        self.question_prompt.setObjectName("QuestionPrompt")
        self.question_prompt.setWordWrap(True)

        self._build_layout()
        self._wire_events()
        self.refresh_from_state(self.controller.state)

    def _make_value_label(self) -> QLabel:
        label = QLabel("--")
        label.setObjectName("ValueLabel")
        return label

    def _build_layout(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)
        left_layout.addWidget(self.title_label)
        left_layout.addWidget(self.subtitle_label)
        left_layout.addWidget(self.feed_label)
        left_layout.addWidget(self.canvas, stretch=1)
        left_layout.addWidget(self.legend_label)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        right_layout.addWidget(self._build_status_box())
        right_layout.addWidget(self._build_navigation_box())
        right_layout.addWidget(self._build_question_box())
        right_layout.addWidget(self._build_operations_box())
        right_layout.addStretch(1)

        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addLayout(right_layout, stretch=2)

    def _build_status_box(self) -> QGroupBox:
        box = QGroupBox("TACTICAL READOUT")
        layout = QGridLayout(box)

        layout.addWidget(QLabel("Phase"), 0, 0)
        layout.addWidget(self.phase_value, 0, 1)

        layout.addWidget(QLabel("Status"), 1, 0)
        layout.addWidget(self.status_value, 1, 1)

        layout.addWidget(QLabel("Position"), 2, 0)
        layout.addWidget(self.position_value, 2, 1)

        layout.addWidget(QLabel("Pressure"), 3, 0)
        layout.addWidget(self.pressure_value, 3, 1)

        layout.addWidget(QLabel("Clogs Cleared"), 4, 0)
        layout.addWidget(self.clogs_value, 4, 1)

        layout.addWidget(QLabel("Level"), 5, 0)
        layout.addWidget(self.level_value, 5, 1)

        layout.addWidget(QLabel("Questions"), 6, 0)
        layout.addWidget(self.questions_value, 6, 1)

        layout.addWidget(QLabel("Accuracy"), 7, 0)
        layout.addWidget(self.accuracy_value, 7, 1)

        return box

    def _build_navigation_box(self) -> QGroupBox:
        box = QGroupBox("PIPE COMMAND")
        layout = QGridLayout(box)

        layout.addWidget(self.north_button, 0, 1)
        layout.addWidget(self.west_button, 1, 0)
        layout.addWidget(self.east_button, 1, 2)
        layout.addWidget(self.south_button, 2, 1)

        blast_hint = QLabel("B: HYDRO BLAST")
        blast_hint.setObjectName("ValueLabel")
        blast_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(blast_hint, 3, 0, 1, 3)

        return box

    def _build_question_box(self) -> QGroupBox:
        box = QGroupBox("HAZARD CHECK")
        layout = QVBoxLayout(box)

        layout.addWidget(self.question_prompt)

        answer_grid = QGridLayout()
        answer_grid.addWidget(self.answer_buttons[0], 0, 0)
        answer_grid.addWidget(self.answer_buttons[1], 0, 1)
        answer_grid.addWidget(self.answer_buttons[2], 1, 0)
        answer_grid.addWidget(self.answer_buttons[3], 1, 1)

        layout.addLayout(answer_grid)
        layout.addWidget(self.blast_button)

        return box

    def _build_operations_box(self) -> QGroupBox:
        box = QGroupBox("OPERATIONS")
        layout = QGridLayout(box)

        layout.addWidget(self.new_game_button, 0, 0)
        layout.addWidget(self.save_button, 0, 1)
        layout.addWidget(self.load_button, 1, 0)
        layout.addWidget(self.help_button, 1, 1)
        layout.addWidget(self.retreat_button, 2, 0, 1, 2)

        return box

    def _wire_events(self) -> None:
        self.north_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.move_north())
        )
        self.south_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.move_south())
        )
        self.east_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.move_east())
        )
        self.west_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.move_west())
        )

        for index, button in enumerate(self.answer_buttons):
            button.clicked.connect(
                lambda _checked=False, idx=index: self.refresh_from_state(
                    self.controller.answer_question(idx)
                )
            )

        self.blast_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.blast())
        )
        self.new_game_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.new_game())
        )
        self.save_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.save_game())
        )
        self.load_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.load_game())
        )
        self.retreat_button.clicked.connect(
            lambda: self.refresh_from_state(self.controller.quit_game())
        )
        self.help_button.clicked.connect(self._show_help_dialog)

    def _show_help_dialog(self) -> None:
        QMessageBox.information(self, "Pipe Commands", self.controller.help_text)

    def refresh_from_state(self, state: GameViewState) -> None:
        self.feed_label.setText(state.status_message)
        self.canvas.set_cells(state.cells)

        self.phase_value.setText(state.phase.upper())
        self.status_value.setText(state.game_status.upper())
        self.position_value.setText(f"R{state.player_row} / C{state.player_col}")
        self.pressure_value.setText(str(state.pressure))
        self.clogs_value.setText(str(state.clogs_cleared))
        self.level_value.setText(str(state.current_level))
        self.questions_value.setText(
            f"{state.questions_correct} / {state.questions_answered}"
        )

        if state.questions_answered > 0:
            accuracy = round(
                (state.questions_correct / state.questions_answered) * 100
            )
            self.accuracy_value.setText(f"{accuracy}%")
        else:
            self.accuracy_value.setText("--")

        self.north_button.setEnabled(state.can_move_north)
        self.south_button.setEnabled(state.can_move_south)
        self.east_button.setEnabled(state.can_move_east)
        self.west_button.setEnabled(state.can_move_west)

        self.save_button.setEnabled(state.can_save)
        self.load_button.setEnabled(state.can_load)
        self.blast_button.setEnabled(state.can_blast)

        if state.question is None:
            self.question_prompt.setText("No active pipe hazard.")
            for button in self.answer_buttons:
                button.setVisible(False)
                button.setEnabled(False)
        else:
            self.question_prompt.setText(
                f"{state.question.prompt}\n\nUse 1-4 or click an answer."
            )
            for i, button in enumerate(self.answer_buttons):
                if i < len(state.question.choices):
                    number = i + 1
                    button.setText(f"{number}: {state.question.choices[i]}")
                    button.setVisible(True)
                    button.setEnabled(state.can_answer)
                else:
                    button.setVisible(False)
                    button.setEnabled(False)

        self._show_end_state_once(state)

    def _show_end_state_once(self, state: GameViewState) -> None:
        if state.game_status == self._last_end_state:
            return

        if state.game_status == "cleared":
            QMessageBox.information(
                self,
                "Shift Complete",
                "All clogs cleared. Nuovo Fresco flows again.",
            )
            self._last_end_state = state.game_status
        elif state.game_status == "quit":
            QMessageBox.information(
                self,
                "Retreat",
                "The city can wait. Shift ended.",
            )
            self._last_end_state = state.game_status
            self.close()
        else:
            self._last_end_state = state.game_status

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        text = event.text().lower()
        state = self.controller.state

        if key == Qt.Key.Key_F1:
            self._show_help_dialog()
            return
        if key == Qt.Key.Key_F5:
            self.refresh_from_state(self.controller.save_game())
            return
        if key == Qt.Key.Key_F9:
            self.refresh_from_state(self.controller.load_game())
            return
        if key == Qt.Key.Key_Escape:
            self.refresh_from_state(self.controller.quit_game())
            return

        if state.question is not None:
            if key == Qt.Key.Key_1:
                self.refresh_from_state(self.controller.answer_question(0))
                return
            if key == Qt.Key.Key_2:
                self.refresh_from_state(self.controller.answer_question(1))
                return
            if key == Qt.Key.Key_3:
                self.refresh_from_state(self.controller.answer_question(2))
                return
            if key == Qt.Key.Key_4:
                self.refresh_from_state(self.controller.answer_question(3))
                return
            if key == Qt.Key.Key_B:
                self.refresh_from_state(self.controller.blast())
                return

        if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.refresh_from_state(self.controller.move_north())
            return
        if key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.refresh_from_state(self.controller.move_south())
            return
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.refresh_from_state(self.controller.move_west())
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.refresh_from_state(self.controller.move_east())
            return
        if key == Qt.Key.Key_N:
            self.refresh_from_state(self.controller.new_game())
            return

        super().keyPressEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    controller = QtGameController()
    window = MainWindow(controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())