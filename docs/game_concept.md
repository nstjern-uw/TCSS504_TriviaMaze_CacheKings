# Nick's Trivia Maze Concept

* Model: GameModel, Player, Level, Maze, Clog, Question, QuestionBank
* View: PyQt6
* Controller: main.py

## Section A: The Theme (The Hook)

You play a plumber with all the traits and mannersims of an 80s action hero -- confident, masculine, and ready to get to work. They are the best at clearing clogs in the city of Nuovo Fresco -- a grimy neon metropolis that was designed with the best intentions, but that's turned out to represent some of the worst. Cleaning the pipes is a dirty job, but someone's got to keep one less piece of sewage off the street. It's up to you to navigate the maze of pipes, clear the correct blockages, and keep the city flowing. 

Questions could stem from any topic. I know there are sites that allow you to connect to question bank API's across a wide range of topics. I was envisioning this as the main question engine to break through a clog. An additional nice to have could be a storyline that relates to how clearing the clogs impacts our hero as they progress through the levels. 

## Section B: The Test Strategy (QA & Algorithms)

We practice Test Driven Development (TDD). Describe specifically how we will verify the system works next week.

note: Energy is only used for the phase beam. It does not impact your ability to move or otherwise perform within the game. 

1. We will test that the user can select their character
2. We will test that the level map can be generated
3. We will test that blockages or "clogs" can be generated in the level map
4. We will test that the character can move throughout the level
5. We test that the character can approach a clog, interact with it
6. We will test that the character can receive a question, and respond to it after choosing to interact.
7. We will test that upon a correct response, the clog dissapears, +10 energy points, and the player can proceed. 
8. We will test that upon an incorrect response, the clog persists -5 energy points, and a new question is generated. 
9. We will test that the phase beam (see happy path for description) instantly removes blockage and 50 energy points are removed. 
10. We will test whether or not the player has >= to 50 energy points when they try and activate the phase beam. 
11. We will test that the user wins when all clogs are cleared that are blocking the level. +25 energy points for perfect level, +15 otherwise. 
12. We will test that a victory condition is triggered when the character navigates all levels. 


## The Happy Path: (Describe a standard successful interaction. e.g., "Player answers correctly -> Door unlocks -> Score +10").

1. The player approaches a blockage, receives a question, answers correctly, Energy +10
2. The player can activate their phase beam at a cost of 50 energy points to instantly clear a blockage


## The Edge Case: (Describe a boundary condition. e.g., "Player attempts to move North into a solid wall -> System catches invalid move -> Player stays at x,y").

1. Player attempts to move through walls of pipes, receives prompt of "ouch my head", and stays at x,y
2. Player attempts to step through a blockage without interacting, receives a prompt of "At least half my face is clean" or "Now I need a shower." 
    

## The Failure State: (Describe error handling. e.g., "Save file is corrupted -> Game catches exception -> Loads default new game").

1. If save file is corrupted, game catches exception, and loads new game. 

## The Solvability Check (Algorithm Selection):

Problem: How do we ensure the randomly generated maze is solvable and the exit is reachable?

Solution: We will use DFS to traverse the graph. I believe we should use DFS because we are only interested in whether or not the maze is solvable. 

Logic: Briefly explain why this algorithm fits (e.g., "We will start at (0,0) and flag all reachable rooms..."). Note: Do not write the code yet, just the logic.

Start at the entrance cell of the maze.
Mark the current cell as visited so you don’t loop back to it later.
Check if it is the exit.
If yes → the maze is solvable.
Look at neighboring cells (up, down, left, right, etc.).
For each neighbor that is:
Inside the maze bounds,
Not a wall,
Not already visited,
→ move to that cell and repeat the process.
If you hit a dead end (no valid unvisited neighbors):
Backtrack to the previous cell and try a different direction.
Continue exploring paths deeply until:
You reach the exit → solvable, or
All possible paths are exhausted → not solvable.
    
## Section C: The Architecture Map (Patterns)

I asked AI to help me with this and here is what is gave me. Some of the things might be a bit too much for this project (things like effects and audio might get pushed out), but it's helping me better understand how the individual components that I've outlined above will fit into the MVC architecture (so I've left them in the list). This is also interesting because it further elaborated on how MVC impacts things like the happy path and edge cases outlined above. I'm curious to see / understand how the code ends up looking once we prompt it to be developed. 

Great concept — it’s very compatible with MVC because you already have **clear separation between game logic, presentation, and interaction rules**. Think of MVC here as:

* **Model = Game World & Rules**
* **View = What the Player Sees/Hears**
* **Controller = What the Player Does**

Below is a clean mapping of your Trivia Maze into MVC plus a few optional supporting patterns.

---

# MVC Mapping for Nick’s Trivia Maze

## 1. Model (The Brain / State / Rules)

The **Model** contains *all game data and logic* but **no rendering and no direct input handling**. If you deleted all graphics, the model should still run the game in pure text.

### Model Responsibilities

**Core Game State**

* Player stats
* Energy
* Position (x, y)
* Selected character
* Current level
* Cleared clogs count
* Win / loss conditions

**Maze & World Data**

* Maze grid structure
* Wall positions
* Clog locations
* Exit position
* Solvability flag

**Question System**

* Question pool
* Current question
* Correct/incorrect logic
* Regeneration rules

**Game Rules**

* +10 energy on correct answer
* –5 energy on wrong answer
* –50 energy for phase beam
* Perfect level bonus rules
* Movement validity
* Interaction rules

**Algorithms**

* DFS solvability check
* Random maze generation
* Random clog placement

**Persistence**

* Save/load logic
* Corruption detection
* Default fallback

### Model Unit Tests (Your Section B fits here perfectly)

Almost every one of your QA steps is a **Model test**, which is ideal:

* Character selection
* Map generation
* Clog generation
* Movement logic
* Interaction logic
* Energy updates
* Victory conditions
* Save corruption handling

---

## 2. View (The Face / Presentation Layer)

The **View** is responsible only for *display*. It **never changes game rules directly**.

### View Responsibilities

**Visuals**

* Maze rendering
* Pipe/wall tiles
* Character sprite
* Clog graphics
* Exit tile
* Neon city theme UI

**UI Elements**

* Energy bar
* Question dialog box
* Score
* Level indicator
* Prompts (“Ouch my head”)

**Feedback & Effects**

* Clog disappearing animation
* Phase beam animation
* Correct/incorrect flash
* Victory screen
* Failure screen

**Audio**

* Sewer ambience
* Action hero voice lines
* Correct/incorrect sounds

### Important Rule

The View **asks** the Model for data:

* “What is the player’s energy?”
* “Is this clog cleared?”
* “What text should I show?”

But it **never decides outcomes**.

---

## 3. Controller (The Translator / Input Logic)

The **Controller** takes player input and translates it into Model actions.

### Controller Responsibilities

**Input Handling**

* Keyboard / controller movement
* Interaction button
* Phase beam activation
* Answer selection
* Menu navigation

**Validation Before Model Calls**

* “Is this move allowed?”
* “Is the player near a clog?”
* “Does the player have ≥ 50 energy?”

**Flow Control**

* Triggering question prompts
* Starting levels
* Handling save/load
* Restarting after failure

### Example Flow (Happy Path)

1. Player presses **Interact**
2. Controller checks adjacency to clog
3. Controller asks Model for a question
4. View displays the question
5. Player selects an answer
6. Controller sends answer to Model
7. Model updates energy & clog state
8. View animates results

---

# Where Your Design Elements Fit

## Happy Path

* **Controller:** detects interaction input
* **Model:** evaluates answer, updates energy/clog
* **View:** shows animations and score change

## Edge Cases

* **Controller:** catches invalid move attempts
* **Model:** confirms collision logic
* **View:** displays “ouch my head” text

## Failure State

* **Model:** throws load exception
* **Controller:** switches to new game
* **View:** shows “New Game Loaded” message

## DFS Solvability

Pure **Model responsibility**.
Controller just calls: `model.generateLevel()`.

---

# Optional Supporting Design Patterns

MVC is the foundation, but a few patterns fit naturally:

## 1. Observer Pattern

**Use for UI updates.**

* Model changes energy → View auto-updates bar
* Model clears clog → View removes sprite

Prevents tight coupling between Model and View.

---

## 2. State Pattern

Useful for **Game Phases**:

* Main Menu
* Playing
* Question Mode
* Victory
* Game Over
* Paused

Controller switches states instead of giant if-else chains.

---

## 3. Factory Pattern

For creating:

* Mazes
* Questions
* Clogs
* Characters

Makes random generation cleaner and testable.

---

## 4. Command Pattern (Optional but Nice)

Encapsulate actions like:

* Move
* Interact
* Phase Beam

Helps with undo, replay, or input rebinding later.

---

# Simple Mental Diagram

```
Player Input
     ↓
 Controller
     ↓
   Model  ← DFS, Energy, Rules, Save/Load
     ↓
    View  ← Graphics, UI, Sounds
```

--- 

# Why MVC Works Well for This Game

* **TDD Friendly:** You can fully test the Model without graphics.
* **Theme Flexibility:** Swap neon sewer theme for space pipes without touching logic.
* **Scalability:** New question types or abilities don’t break rendering.
* **Team Friendly:** Artists work in View, programmers in Model, gameplay devs in Controller.


## AI Insights:

Apart from the insight on MVC mentioned above, the AI was a bit confused on how the energy economy worked in the game. I'd only introduced it as a way to gain an ability to destroy a clog without having to answer a question. However, the AI was asking what would happen if the player had 0 energy. It was under the impression that the game might end, but this is not how I intended it to function. 
