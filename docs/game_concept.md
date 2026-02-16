# Liam's Trivia Maze Concept — Tower of Trials

## Section A: The Theme (The Hook)

### Setting
The player enters the **Tower of Trials**, a mysterious vertical gauntlet where each “floor” is a self-contained maze made of sealed rooms. Every floor has its own biome and vibe, like the tower is pulling from different worlds.

Planned floors/biomes:
- **Jungle Floor** — overgrown ruins, vines, wildlife sounds
- **City Floor** — neon streets, subways, rooftops
- **Desert Floor** — dunes, ancient tomb corridors, heat haze
- **Underwater Floor** — submerged halls, coral growth, pressure locks

### Why is the player here?
The tower is a legendary proving ground. The player climbs to reach the top floor and escape, but the tower only opens doors for those who can solve its challenges.

### Core hook
Each room is a **challenge room**. To progress, the player must answer trivia correctly. Each floor ends with a **boss encounter** at the stairs door. Beat the boss to unlock the stairs and advance to the next biome/floor.

---

## Section B: The Test Strategy (QA & Algorithms)

We will practice TDD by writing tests for the logic layer first (Model + Controller-facing logic), before building the GUI.

### Test 1 — Happy Path (Standard successful run)
**Scenario:**  
Player starts on the Jungle floor at the spawn cell. The player moves through valid rooms, enters an uncleared challenge room, answers correctly, the room becomes cleared, score increases, and the player continues until reaching the **Boss Door / Stairs Up** cell. The boss encounter triggers. The player answers correctly through boss phases and wins, unlocking stairs and advancing to the next floor (City).

**Expected Result:**  
- Valid movement updates player position (x,y).  
- Entering an uncleared challenge room triggers a trivia question.  
- Correct answer marks the room cleared and awards points.  
- Boss Door remains locked until boss encounter is defeated.  
- Boss victory unlocks stairs, increments floor number, and loads the next biome’s layout.

---

### Test 2 — Edge Case (Boundary condition)
**Scenario:**  
Player attempts to move:
1) Off the grid (out of bounds), or  
2) Into a wall/blocked cell.

**Expected Result:**  
- The move is rejected safely.  
- Player position does not change.  
- No score change and no crash.  
- Controller returns a clear “invalid move” result that the View can display.

---

### Test 3 — Failure State (Error handling)
**Scenario:**  
Load is attempted but:
- The save file is corrupted (invalid JSON), OR
- The save references an invalid state (e.g., floor index doesn’t exist, position out of bounds).

**Expected Result:**  
- Game catches parsing/validation errors (no crash).  
- Game falls back to a safe default new-game state (Floor 1, spawn position, score reset).  
- Controller returns a user-friendly message for the GUI (“Save invalid. Starting new game.”).

---

### Test 4 — Algorithm Test (Solvability Check + Boss Graph Validity)

#### Solvability Check (Maze Reachability)
**Chosen Algorithm:** BFS (Breadth-First Search)

**Logic (no code):**  
- Represent each floor as a graph: each walkable cell is a node; edges connect adjacent walkable cells (N/E/S/W).  
- Run BFS from the spawn cell and mark all reachable cells.  
- Verify that the **Boss Door / Stairs Up** cell is reachable.  
- If it is not reachable, reject/regenerate the floor layout until solvable.  
- Repeat this validation for each floor (each biome floor must be playable).

**Why BFS fits:**  
BFS explores every cell reachable from the start. If the stairs cell is visited during traversal, a valid path exists; if not, the floor is unsolvable.

#### Boss Phase Graph Validity (Branching encounter rules)
**Logic (no code):**  
- Each boss encounter is defined as a small directed graph of phases (a state machine).  
- Validate:
  - A start phase exists  
  - Every transition points to a valid phase (no missing nodes)  
  - At least one path reaches WIN and at least one path reaches LOSE  
This ensures the boss encounter cannot soft-lock the player.

---

## Section B.5 — Boss Design (Branching Structure + Themed Questions)

### Biome-driven themed content (Option A flavor)
Each floor has a **BiomeProfile** that defines the theme and what question topics appear on that floor.

Example topic tracks for bosses:
- **Jungle Boss:** animals → plants → survival
- **City Boss:** landmarks → transit → pop culture
- **Desert Boss:** geography → weather → history
- **Underwater Boss:** ocean life → science → myths/shipwrecks

Normal rooms also pull questions filtered by the biome, so the entire floor feels consistent.

### Boss encounter structure (Option B structure)
Every boss uses the same branching **phase graph**, but with biome-specific question pools.

**Example phase graph (shared structure across biomes):**
- P0 (Intro, easy themed question)
  - correct → P1
  - wrong → R1
- P1 (Mid, medium themed question)
  - correct → P2
  - wrong → R1
- P2 (Final, hard themed question)
  - correct → WIN
  - wrong → R2
- R1 (Recovery, easy/medium)
  - correct → P1
  - wrong → LOSE
- R2 (Last chance, medium)
  - correct → P2
  - wrong → LOSE

**Key idea:**  
The *branching path* provides a consistent “boss fight” feeling, while the *biome filters + topic track* make each boss unique.

---

## Section C: The Architecture Map (Patterns)

### MVC Mapping (mandatory)

#### Model (Data + Game Logic)
Planned modules/classes (subject to refinement):
- **BiomeProfile**
  - biome name (Jungle/City/Desert/Underwater)
  - visual tile set id (for View)
  - allowed question topic tags
  - difficulty scaling rules
- **FloorMaze**
  - grid layout (walkable cells, walls)
  - spawn cell, boss/stairs cell
  - cleared room tracking for this floor
- **Tower**
  - ordered list of floors/biomes
  - current floor index
  - loads/creates the current floor maze
- **PlayerState**
  - position (x,y), current floor, score
  - cleared rooms / progress flags
- **QuestionService (backed by SQLite)**
  - fetch questions filtered by biome_tag, topic_tag, and difficulty
  - supports normal-room and boss-phase queries
- **BossRuleset**
  - boss phase graph definition (states + transitions)
  - mapping from biome → topic track for phases
- **SaveLoadService**
  - save state to JSON
  - load + validate state safely
- **DatabaseManager**
  - manages SQLite connection and query helpers

#### View (GUI)
**GUI library:** PyQt6 (planned)

The View will:
- Render the current floor grid using a biome-specific tile style (colors/icons)
- Show player position, walls, boss door/stairs, and cleared vs uncleared rooms
- Display trivia prompts (question text + answer options)
- Show status (biome, floor number, score, messages)

#### Controller (Game Flow / Glue)
Planned controller module/class: **GameController** (or similar)
- Handles UI events (movement, answer selection, save/load)
- Calls Model logic (attempt_move, generate_question, submit_answer, boss_phase_transition)
- Returns clean results/events for the View to render (no direct printing)

---

## AI Review Summary

**What I asked AI to review:**
- Whether the tower concept still satisfies the requirement of a navigable 2D grid
- Whether the rubric requirements are all explicitly present (4 tests, MVC mapping, BFS/DFS solvability)
- Whether the boss “unique question path” concept can be described in a clear, testable way without writing code

**Changes I accepted:**
- Clarified that each tower floor is its own 2D grid maze to meet the 2D navigation requirement
- Chose BFS for reachability validation and described a regeneration rule for unsolvable floors
- Defined boss encounters as a small phase graph (state machine) and added a validity test for it
- Added biome/topic tagging so boss fights and normal rooms both feel biome-themed

**Changes I rejected (and why):**
- Skipping per-floor solvability checks and validating only the final exit (rejected because each floor must be independently playable and not soft-lock progression)