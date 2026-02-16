## Ryan's Trivia Maze Concept

#### Section A: The Theme (The Hook)

**Setting:** You are a graduate student navigating **The GCSDE Career Maze**—a mysterious building where each room represents a critical skill or challenge on your journey from your previous career into software engineering. The tech world is rapidly changing with AI, and you must prove you can adapt and learn.

**Why are you here?** You're halfway through the UW Tacoma Graduate Certificate program, and every room in this maze represents a technical interview question, a coding challenge, or a key concept you need to master. Answer trivia questions correctly to unlock doors and progress toward the exit: your dream job offer as a Software Engineer.

**The Experience:**
- Each room has a different color representing a tech domain (Blue = Databases, Green = Algorithms, Purple = Design Patterns, Orange = Testing)
- Locked doors block your path until you answer questions correctly
- Your score represents "Skills Mastered"
- The maze is randomly generated each game, so every playthrough is different
- Sometimes it feels like drinking from a fire hose—but you're determined to prove you can absorb it all

**Visual Style:** Clean, modern PyQt6 interface with a grid-based maze view. Professional aesthetic with clear visual feedback for locked/unlocked doors, player position, and progress. Color-coded rooms make navigation intuitive.

---

#### Section B: The Test Strategy (QA & Algorithms)

We practice Test Driven Development (TDD). Here's specifically how we will verify the system works next week.

**Coordinate system convention:** We use \((x,y)\) coordinates where **(0,0) is the top-left** room, **x increases to the East (right)**, and **y increases to the South (down)**. Therefore, moving **North** decreases \(y\), and moving **West** decreases \(x\).

**Testing approach:** Most automated tests will target **Model + Controller** logic (maze generation, BFS, movement validation, scoring, persistence). The PyQt GUI will be verified with manual smoke tests and a demo checklist.

1. **The Happy Path:**

   Player starts at position (0,0) in a 4x4 maze. Player clicks the "Move East" button. The system displays a trivia question: "What does SQL stand for?" Player selects the correct answer: "Structured Query Language." The door unlocks with visual feedback (color changes from red to green). Player's score increases by 10 points, and the HUD updates to show something like "Score: 10 (Skills Mastered: 1)". Player successfully moves to position (1,0). Game state is automatically saved to the SQLite database.

   **Test:** `test_correct_answer_unlocks_door_and_moves_player()` - Verify player position changes from (0,0) to (1,0), score increases by 10, and the correct door state changes to unlocked.

2. **The Edge Case:**

   Player is at position (0,0)—the top-left corner of a 4x4 maze. Player clicks the "Move North" button, which would move them to position (0,-1). The system detects this is an out-of-bounds move. The system displays message: "You've hit the career ceiling! Can't move that way." Player position remains at (0,0). No score penalty is applied. The North movement button is disabled or grayed out to provide visual feedback.

   **Test:** `test_boundary_movement_prevented()` - Place player at each edge position (top row, bottom row, left column, right column) and verify the system prevents invalid moves without crashing and without changing the player's coordinates.

3. **The Failure State:**

   Player clicks "Load Game" from the main menu. The system attempts to read from the SQLite database file. The database file is missing, corrupted, unreadable, or required tables/columns are missing. The system catches `sqlite3.Error` in the error handler, logs the error with a timestamp for debugging, and displays a user-friendly message: "No saved game found. Starting fresh career journey!" The system initializes a fresh database schema (if needed) and starts a new game at position (0,0) with score = 0. The game continues normally—no crash and graceful recovery.

   **Test:** `test_load_missing_or_corrupt_db_starts_new_game()` - Delete the DB file and also test with a corrupted DB. Verify the game recovers, shows the correct message, and starts a new game without crashing.

4. **The Solvability Check (Algorithm Selection):**

   - **Problem:** How do we ensure the randomly generated maze is solvable and the exit is reachable?

   - **Solution:** We will use **BFS (Breadth-First Search)** to traverse the graph.

   - **Logic:**
     Our maze generation decides the **topology** of the maze: for each pair of adjacent rooms, there is either a **wall** (no passage) or a **passage/doorway** (movement is possible). Doors may start "locked" for gameplay, but they are intended to be **unlockable** by answering questions, so solvability is about whether a path of *passages* exists in the maze topology.

     We represent the maze as a graph where:
     - Each room is a node
     - Each **passage** between adjacent rooms (no wall) is an edge

     We run BFS starting from (0,0):
     1. Initialize a queue with (0,0)
     2. Create a visited set and mark (0,0) as visited
     3. While the queue is not empty:
        - Dequeue the next room
        - For each adjacent room (N, S, E, W):
          - If there is a passage (no wall) and the adjacent room is not visited:
            - Mark it visited and enqueue it
     4. After BFS completes, check whether the exit room (3,3) is in `visited`

     If the exit is reachable, the maze topology is valid. If not, we regenerate the maze topology and run BFS again until it is solvable.

     **Difficulty sanity check (optional but simple):**
     BFS also gives us the **shortest path length** from start to exit. If the path is too short (e.g., trivially easy), we can regenerate until the shortest path length meets a minimum threshold.

     **Why BFS over DFS:**
     - BFS explores level-by-level and naturally finds the **shortest path**, which is useful for validating solvability and tuning difficulty
     - BFS is systematic and easier to debug in grid graphs
     - BFS handles cycles naturally
     - Time complexity is \(O(V+E)\); for a 4x4 grid, \(V=16\) and \(E \le 24\) (undirected adjacencies), so it's very efficient

---

#### Section C: The Architecture Map (Patterns)

#### MVC (Model-View-Controller) - Mandatory

**Model (Data & Logic):**
- `maze.py` - `Maze` class: Stores 2D grid structure, room connections, door/wall topology, and door lock states
- `player.py` - `Player` class: Tracks current position (x, y), score, rooms visited
- `question.py` - `Question` class: Stores question text, answer choices, correct answer, category
- `database.py` - `DatabaseManager` class: Handles SQLite operations (load questions, save/load game state)
- `maze_generator.py` - `MazeGenerator` class: Creates random maze layouts, runs BFS validation

**View (GUI):**
- **Library:** PyQt6
- `main_menu_view.py` - Main menu (New Game, Load Game, Quit)
- `game_window.py` - Main window that hosts the maze and HUD
- `maze_view.py` - Renders the 2D grid, player position, and door states
- `question_dialog.py` - Modal dialog showing trivia and answer buttons
- `hud_view.py` - Displays score and status messages

**Controller (Connects Model & View):**
- `game_controller.py` - Orchestrates game flow and high-level state transitions
- `movement_controller.py` - Handles move requests, validates bounds/walls/locks, and triggers questions
- `question_controller.py` - Displays questions, evaluates answers, unlocks doors, updates score
- `save_load_controller.py` - Saves and loads state via `DatabaseManager`, handles error recovery

---

#### Additional Design Patterns

**Singleton Pattern:**
- **Applied to:** `DatabaseManager` class
- **Rationale:** A single DB access layer reduces connection conflicts and centralizes schema initialization and error handling.

**Factory Pattern:**
- **Applied to:** `QuestionFactory` class
- **Rationale:** Creates `Question` objects from database rows so question construction is centralized and consistent.

**Observer Pattern:**
- **Applied to:** Score/state updates
- **Rationale:** PyQt’s signals/slots provide a natural observer mechanism. For example, when score changes, the HUD updates without tightly coupling the model to the GUI.

**Strategy Pattern (if time permits):**
- **Applied to:** Difficulty settings (if time permits)
- **Rationale:** Allows swapping difficulty behavior (maze size, time limit, question difficulty) without rewriting core logic.

---

#### AI Review Summary

I asked an AI model to review this proposal and provide feedback on technical feasibility, architecture decisions, and risks.

**Key AI Feedback (summary):**

- Keep the MVP tight given the timeline; cut animations/polish unless ahead of schedule.
- PyQt6 is a good fit for a professional GUI but has a learning curve (signals/slots, layouts).
- Save/Load is commonly more complex than expected; keep it minimal initially.
- BFS is a strong choice for solvability and can also be used to estimate difficulty.

**What I accepted:**
- Focus on MVP first; treat animations and other polish as stretch goals.
- Use BFS explicitly for solvability validation and (optionally) for minimum path-length difficulty checks.
- Keep save/load minimal and robust (handle missing/corrupted DB gracefully).

**What I modified:**
- Clarified coordinate conventions and what BFS is traversing (maze topology vs locks) to remove ambiguity.
- Clarified that unit tests primarily target Model/Controller logic; GUI is smoke-tested manually.

**What I rejected:**
- Over-complicating persistence with advanced versioning/migrations for Week 1; failure state will handle “missing/corrupt/missing tables” cleanly and start a new game.

---

#### Scope Considerations (3-Week Timeline)

**MVP Features (Must Complete):**
- 4x4 navigable maze with random generation
- BFS solvability validation
- 60 trivia questions stored in SQLite database
- Basic save/load functionality (position, score, maze seed or equivalent minimal state)
- PyQt6 GUI with clean, professional design
- Question-answer-unlock door flow
- Movement validation (boundary checks, walls/doors, locked doors)
- Score tracking and display
- MVC architecture with clear separation of concerns

**Stretch Goals (If Time Permits):**
- Difficulty levels (3x3 vs 5x5 maze options)
- Question timer with countdown
- Door unlock animations and visual effects
- Advanced save/load (full door states, question history)
- Hint system for difficult questions
- Achievement system
- Visual polish and custom styling

**Explicitly Out of Scope:**
- Multiplayer functionality
- Sound effects and background music
- Mobile version or web deployment
- Leaderboard with online sync
- Custom question editor

This scope definition ensures we deliver a complete, working game within the 3-week timeline while leaving room for enhancements if development proceeds ahead of schedule.
