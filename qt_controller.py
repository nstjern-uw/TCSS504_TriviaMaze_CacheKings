from __future__ import annotations

from main import EnginePhase, GameEngine
from maze import GameStatus, get_section, get_visibility_map
from qt_bridge_view import QtPipeView
from qt_models import GameViewState, QuestionState, VisibleCell


class QtGameController:
    """
    Thin controller between the Qt window and the existing GameEngine.

    The engine remains the source of truth.
    The controller:
    - sends commands into GameEngine
    - reads engine state
    - converts domain data into GameViewState for the GUI
    """

    def __init__(self, save_slot: str = "default", seed: int | None = None) -> None:
        self.view = QtPipeView()
        self.engine = GameEngine(save_path=save_slot, view=self.view)
        self._seed = seed
        self._state_cache: GameViewState | None = None

        self.engine.start_new_game(seed=seed)
        self.view.render_welcome()
        self.view.render_help()
        self._sync_question_bridge()
        self._state_cache = self.build_view_state()

    @property
    def state(self) -> GameViewState:
        if self._state_cache is None:
            self._state_cache = self.build_view_state()
        return self._state_cache

    @property
    def help_text(self) -> str:
        return self.view.last_help_text

    def new_game(self) -> GameViewState:
        self.engine.start_new_game(seed=self._seed)
        self.view.render_welcome()
        self.view.render_help()
        self._sync_question_bridge()
        self._state_cache = self.build_view_state()
        return self._state_cache

    def move_north(self) -> GameViewState:
        return self._run_command("north")

    def move_south(self) -> GameViewState:
        return self._run_command("south")

    def move_east(self) -> GameViewState:
        return self._run_command("east")

    def move_west(self) -> GameViewState:
        return self._run_command("west")

    def answer_question(self, choice_index: int) -> GameViewState:
        letters = ["a", "b", "c", "d"]
        if 0 <= choice_index < len(letters):
            return self._run_command(letters[choice_index])
        return self.state

    def blast(self) -> GameViewState:
        return self._run_command("blast")

    def save_game(self) -> GameViewState:
        return self._run_command("save")

    def load_game(self) -> GameViewState:
        return self._run_command("load")

    def quit_game(self) -> GameViewState:
        return self._run_command("quit")

    def build_view_state(self) -> GameViewState:
        state = self.engine.state
        if state is None:
            return GameViewState(
                title="NUOVO FRESCO // PIPE STRIKE",
                status_message="System offline.",
                rows=0,
                cols=0,
                cells=[],
                player_row=0,
                player_col=0,
                pressure=0,
                clogs_cleared=0,
                current_level=0,
                questions_answered=0,
                questions_correct=0,
                phase="offline",
                game_status="offline",
                can_move_north=False,
                can_move_south=False,
                can_move_east=False,
                can_move_west=False,
                can_answer=False,
                can_blast=False,
                can_save=False,
                can_load=False,
                question=None,
            )

        visibility_map = get_visibility_map(
            state.pipe_network,
            state.player.position,
            state.visited_positions,
        )

        cells: list[list[VisibleCell]] = []
        for row in visibility_map:
            gui_row: list[VisibleCell] = []
            for vis in row:
                open_dirs = set(vis.open_directions or [])
                gui_row.append(
                    VisibleCell(
                        row=vis.position.row,
                        col=vis.position.col,
                        is_current=vis.is_current,
                        is_visited=vis.is_visited,
                        is_visible=vis.is_visible,
                        is_entry_valve=(vis.position == state.pipe_network.entry_valve),
                        is_exit_drain=(vis.position == state.pipe_network.exit_drain),
                        has_clog=vis.has_clog,
                        north_open=("north" in open_dirs) if vis.is_visible else None,
                        south_open=("south" in open_dirs) if vis.is_visible else None,
                        east_open=("east" in open_dirs) if vis.is_visible else None,
                        west_open=("west" in open_dirs) if vis.is_visible else None,
                    )
                )
            cells.append(gui_row)

        current_section = get_section(state.pipe_network, state.player.position)

        navigating = (
            self.engine.phase == EnginePhase.NAVIGATING
            and state.status == GameStatus.IN_PROGRESS
        )
        blocked = (
            self.engine.phase == EnginePhase.BLOCKED
            and state.status == GameStatus.IN_PROGRESS
        )

        current_question = getattr(self.engine, "_current_question", None)
        question_state = None
        if blocked and current_question is not None:
            question_state = QuestionState(
                prompt=current_question.prompt,
                choices=list(current_question.choices),
            )

        return GameViewState(
            title="NUOVO FRESCO // PIPE STRIKE",
            status_message=self.view.last_message,
            rows=state.pipe_network.rows,
            cols=state.pipe_network.cols,
            cells=cells,
            player_row=state.player.position.row,
            player_col=state.player.position.col,
            pressure=state.player.pressure,
            clogs_cleared=state.player.clogs_cleared,
            current_level=state.player.current_level,
            questions_answered=state.questions_answered,
            questions_correct=state.questions_correct,
            phase=self.engine.phase.value,
            game_status=state.status.value,
            can_move_north=navigating and not current_section.connections["north"],
            can_move_south=navigating and not current_section.connections["south"],
            can_move_east=navigating and not current_section.connections["east"],
            can_move_west=navigating and not current_section.connections["west"],
            can_answer=blocked and current_question is not None,
            can_blast=blocked,
            can_save=(state.status == GameStatus.IN_PROGRESS),
            can_load=navigating,
            question=question_state,
        )

    def _run_command(self, command: str) -> GameViewState:
        self.engine.process_command(command)
        self._sync_question_bridge()
        self._state_cache = self.build_view_state()
        return self._state_cache

    def _sync_question_bridge(self) -> None:
        """
        Keep the bridge view's question text in sync with the engine state.

        In CLI mode, render_question() is called inside the main loop.
        In the Qt flow, we do not use that loop, so the controller mirrors
        the active question into the bridge after each command.
        """
        current_question = getattr(self.engine, "_current_question", None)
        if self.engine.phase == EnginePhase.BLOCKED and current_question is not None:
            self.view.render_question(
                current_question.prompt,
                list(current_question.choices),
            )
        else:
            self.view.clear_question()