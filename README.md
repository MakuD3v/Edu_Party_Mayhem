# 🎓 EDU PARTY MAYHEM

**A Massive Multiplayer Online Learning Battle Royale**

Edu Party Mayhem is a real-time multiplayer educational game where players compete in various mini-games (Math, Coding, Typing) to qualify for the next round. It uses a Battle Royale format where players are eliminated each round until one winner remains.

---

## 🏗️ Project Structure

The project is divided into a Python **Backend** (FastAPI) and a standard HTML/JS **Frontend**.

```
EDU PARTY MAYHEM/
├── backend/
│   ├── app.py                 # Main FastAPI Entry Point
│   ├── config.py              # Configuration & Environment Variables
│   ├── database.py            # Async Database Engine (SQLAlchemy)
│   ├── models.py              # Database Models (User, Session)
│   ├── games/                 # Game Logic Modules (OOP Strategy Pattern)
│   │   ├── base_game.py       # Abstract Base Class for all games
│   │   ├── math_quiz.py
│   │   ├── speed_typing.py
│   │   └── ... 
│   ├── routes/
│   │   ├── auth_routes.py     # Login/Register API
│   │   ├── game_routes.py     # WebSocket Handling & Game Loop
│   │   └── session_routes.py  # Lobby Management
│   └── services/
│       ├── game_session_service.py  # Core Game Logic Orchestrator
│       └── lobby_service.py         # Lobby State Management
│
├── frontend/
│   ├── index.html            # Launcher / Main Menu
│   ├── lobby.html            # Lobby / Waiting Room
│   ├── game.html             # Main Game Interface
│   ├── js/
│   │   ├── game.js           # Client-side Game Logic
│   │   ├── socket.js         # WebSocket Wrapper Class
│   │   └── waiting_room.js   # Lobby Logic
│   └── css/
│       └── styles.css        # Global Styles
```

---

## 🧠 Backend Architecture

### 1. Game Session Orchestration (`game_session_service.py`)
This is the heart of the game. It controls the state of a live game session.
- **Class `GameSession`**: specific instance of a running game.
  - **Properties**: `current_round`, `active_players`, `eliminated_players`, `slots_available`.
  - **Methods**: `start_round()`, `complete_round()`, `calculate_results()`.
  - **Sync Logic**: Uses `players_ready_for_round` set to ensure all players are synchronized before starting.
  - **Timer Logic**: Runs a server-side async timer to enforce round limits (plus a small buffer for frontend animations).

### 2. Game Modes Strategy Pattern (`backend/games/`)
We use the **Strategy Pattern** to handle different mini-games easily.
- **`BaseGame` (Abstract Class)**: Defines the contract (`start`, `process_action`, `end`).
- **`MathQuiz`, `SpeedTyping`, etc.**: Concrete implementations. The `GameSession` selects one of these classes at random for each round and delegates the game-specific logic to it.

### 3. WebSocket Communication (`game_routes.py`)
Handles real-time bi-directional communication using FastAPI WebSockets.
- **ConnectionManager**: Handles broadcasting messages to specific session groups.
- **Events**:
  - `ROUND_START`: Triggers the round on frontend.
  - `GAME_ACTION`: Receives answers from players.
  - `ROUND_COMPLETE`: Players report their final score.
  - `ROUND_RESULT`: Backend informs player if they Qualified or were Eliminated.

---

## 🎨 Frontend Architecture

### 1. Game Flow Manager (`game.js`)
Uses a simplified **State Machine** pattern via the `GameFlow` class.
- **`startSequence(data)`**: Orchestrates the Intro -> Tutorial -> Countdown -> Game loop.
- **`showStage(name)`**: Handles DOM switching between stages (Intro, Game, Intermission).
- **`startGame(data)`**: Switches logic based on the `game_type` received (Strategy implementation on client).

### 2. WebSocket Wrapper (`socket.js`)
Encapsulates the raw `WebSocket` object into a robust `GameSocket` class.
- Handles automatic reconnection logic.
- Provides an event-based system (`on('event', callback)`).

---

## 🔄 The Game Loop

1. **Lobby**: Host clicks "Start Game".
2. **Game Start**: Backend creates a `GameSession` and broadcasts `GAME_START`.
3. **Redirect**: Clients move to `game.html`.
4. **Sync**: Clients connect via WS and send `PLAYER_READY_FOR_ROUND`.
5. **Round Start**: Once all players are ready, Backend broadcasts `ROUND_START`.
6. **Gameplay**: 
   - Backend requires a strict count of active players.
   - Frontend runs local timer.
   - Backend runs server timer (authoritative).
7. **Round End**:
   - Clients send `ROUND_COMPLETE` with scores.
   - Backend aggregates scores, ranks players, and cuts the bottom % (Elimination).
   - Backend sends `ROUND_RESULT`.
8. **Progression**:
   - If qualified -> Next Round.
   - If eliminated -> Return to Lobby.
   - If last player standing -> WINNER!

---

## 🛠️ Object-Oriented Patterns Used

- **Singleton Pattern**: used for `ConnectionManager` and Services (`game_session_service`) to ensure one global state manager.
- **Strategy Pattern**: used for Game Modes (`BaseGame` -> `MathGame`, `TypingGame`). This allows adding new games without changing the core loop.
- **Observer Pattern**: used in the WebSocket event system (listeners subscribe to message types).
