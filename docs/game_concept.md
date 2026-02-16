## Ryan's Trivia Maze Concept

### Section A: The Theme (The Hook)

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

### Section B: The Test Strategy (QA & Algorithms)

We practice Test Driven Development (TDD). Here's specifically how we will verify the system works next week:

#### **1. The Happy Path:**

Player starts at position (0,0) in a 4x4 maze. Player clicks the "Move East" button. System displays a trivia question: "What does SQL stand for?" Player selects the correct answer: "Structured Query Language." The door unlocks with visual feedback (color changes from red to green). Player's score increases by 10 points, and the HUD updates to show "Skills Mastered: 1/20." Player successfully moves to position (1,0). Game state is automatically saved to the SQLite database.

**Test:** `test_correct_answer_unlocks_door_and_moves_player()` - Verify player position changes from (0,0) to (1,0), score increases by 10, and door state changes to unlocked.

#### **2. The Edge Case:**

Player is at position (0,0)—the top-left corner of a 4x4 maze. Player clicks the "Move North" button, which would move them to position (0,-1). System detects this is an out-of-bounds move. System displays message: "You've hit the career ceiling! Can't move that way." Player position remains at (0,0). No score penalty is applied. The North movement button is disabled or grayed out to provide visual feedback.

**Test:** `test_boundary_movement_prevented()` - Place player at each edge position (top, bottom, left, right) and verify system prevents invalid moves without crashing. Verify appropriate error messages display.

#### **3. The Failure State:**

Player clicks "Load Game" button from the main menu. System attempts to read from the SQLite database file. The database file is missing, corrupted, or has an incompatible schema version. System catches `sqlite3.Error` exception in the error handler. Error handler logs the error with timestamp for debugging. GUI displays user-friendly message: "No saved game found. Starting fresh career journey!" System creates a fresh database with the correct schema. Player starts a new game at position (0,0) with score = 0. Game continues normally—no crash, graceful degradation.

**Test:** `test_corrupted_save_file_handled_gracefully()` - Delete database file, corrupt it with random bytes, or use an old schema version. Verify game handles each scenario gracefully without crashing.

#### **4. The Solvability Check (Algorithm Selection):**

**Problem:** How do we ensure the randomly generated maze is solvable and the exit is reachable from the starting position?

**Solution:** We will use **BFS (Breadth-First Search)** to traverse the graph.

**Logic:** 

After generating the maze with randomized door configurations, we represent it as a graph where each room is a node and each unlocked (or unlockable) door is an edge connecting two rooms.

We run BFS starting from the starting position (0,0):

1. Initialize a queue with the starting room (0,0)
2. Create a visited set and mark the starting room as visited
3. While the queue is not empty:
   - Dequeue a room from the front
   - Check all four adjacent rooms (North, South, East, West)
   - For each adjacent room:
     - If a door exists (or can exist) and the room hasn't been visited
     - Add it to the queue and mark as visited
4. After BFS completes, check if the exit room (3,3) is in the visited set

If the exit is reachable, the maze is valid and we proceed. If not, we regenerate the door configuration and re-run BFS until we get a solvable maze.

**Why BFS over DFS:**
- BFS explores level-by-level, guaranteeing we find the shortest path first
- This helps us verify the maze isn't trivially easy (too direct) or impossibly hard (requires visiting every room)
- BFS is easier to debug because it explores systematically by distance
- BFS handles cycles naturally (player might revisit rooms for different questions)
- Time complexity O(V+E) is efficient for our small grid sizes (4x4 = 16 rooms, maximum ~64 edges)
- BFS allows us to calculate minimum required moves, helping balance difficulty

---

### Section C: The Architecture Map (Patterns)

#### **MVC (Model-View-Controller) - Mandatory**

**Model (Data & Logic):**
- `maze.py` - `Maze` class: Stores 2D grid structure, room connections, door states (locked/unlocked)
- `player.py` - `Player` class: Tracks current position (x, y), score, rooms visited
- `question.py` - `Question` class: Stores question text, answer choices, correct answer, category
- `database.py` - `DatabaseManager` class: Handles all SQLite operations (save/load game state, retrieve questions)
- `maze_generator.py` - `MazeGenerator` class: Creates random maze layouts, runs BFS validation

**View (GUI):**
- **Library:** PyQt6 (professional, feature-rich, good documentation)
- `main_menu_view.py` - Main menu screen with New Game, Load Game, Settings, and Quit buttons
- `maze_view.py` - Displays 2D grid with visual representation of rooms, player position, and door states
- `question_dialog.py` - Modal dialog that shows trivia question with multiple choice buttons
- `game_window.py` - Main game window containing maze view, HUD (score, position), and movement controls
- `hud_view.py` - Heads-up display showing score, current position, skills mastered counter

**Controller (Connects Model & View):**
- `game_controller.py` - Main game loop, coordinates all components, manages game state
- `movement_controller.py` - Handles player movement requests, validates moves, triggers question events
- `question_controller.py` - Loads questions from database, checks player answers, unlocks doors on correct answers
- `save_load_controller.py` - Manages saving and loading game state to/from SQLite, handles errors

---

#### **Additional Design Patterns**

**Singleton Pattern:**
- **Applied to:** `DatabaseManager` class
- **Rationale:** We need exactly one database connection shared across the entire application to prevent conflicts, race conditions, and locked database errors. Multiple instances could cause data corruption or concurrent access issues.

**Factory Pattern:**
- **Applied to:** `QuestionFactory` class
- **Rationale:** Creates `Question` objects from database rows. Centralizes question creation logic so we can easily add new question types, categories, or difficulty levels later without modifying existing code. Supports extensibility.

**Observer Pattern:**
- **Applied to:** Score and game state updates
- **Rationale:** When player score changes, multiple UI elements need to update (score display, progress bar, achievements). Observer pattern allows these components to react automatically without tight coupling between the model and view layers.
- **Example:** `ScoreObserver` watches `Player.score` and notifies `HUDView` to update display when it changes.

**Strategy Pattern:**
- **Applied to:** Difficulty settings (if time permits)
- **Rationale:** Different difficulty levels change maze size, question difficulty, and time limits. Strategy pattern lets us swap difficulty behaviors without changing core game logic.
- **Example:** `EasyStrategy` (3x3 maze, 60s per question), `HardStrategy` (5x5 maze, 30s per question)

---

### AI Review Summary

I asked AI (Claude) to review this proposal and provide feedback on technical feasibility, architecture decisions, and potential risks.

**Key AI Feedback:**

1. **Timeline Concern:** "3-week timeline is aggressive but achievable if you focus on MVP features and cut non-essential elements like animations and difficulty levels."

2. **PyQt6 Learning Curve:** "PyQt6 is more powerful than tkinter but has a steeper learning curve. Budget extra time for the GUI developer to learn signals/slots and layout management."

3. **Save/Load Complexity:** "Serializing full game state (maze structure, door states, question history) is complex. Consider saving just position, score, and maze seed to regenerate the maze."

4. **BFS Implementation:** "BFS choice is solid. Consider also checking minimum path length to ensure maze isn't trivially easy (direct path to exit)."

5. **Question Database:** "60-100 quality questions take time to write. Start this immediately, don't wait for Week 2."

**What I Accepted:**
- ✅ Focus on MVP features—cut animations, sound effects, and advanced polish
- ✅ Simplify save/load to position, score, and maze seed (regenerate maze on load)
- ✅ Add minimum path length check to BFS validation
- ✅ Start writing questions immediately (each team member contributes 20)

**What I Modified:**
- 🔄 Keep PyQt6 (required by team decision) but acknowledge learning curve and plan accordingly
- 🔄 Strategy pattern marked as "if time permits" rather than core feature

**What I Rejected:**
- ❌ Switching to tkinter—team has decided on PyQt6 for more professional appearance
- ❌ Removing BFS entirely—it's a core requirement worth 10% of grade
- ❌ Pre-designed mazes only—we'll implement random generation with BFS validation as specified

---

### Scope Considerations (3-Week Timeline)

**MVP Features (Must Complete):**
- 4x4 navigable maze with random generation
- BFS solvability validation
- 60 trivia questions stored in SQLite database
- Basic save/load functionality (position, score, maze seed)
- PyQt6 GUI with clean, professional design
- Question-answer-unlock door flow
- Movement validation (boundary checks, locked doors)
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
