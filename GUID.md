# 🚁 Fly-in — Complete Project Guide

> Python drone routing simulator — solo dev guide

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Setup & File Structure](#2-setup--file-structure)
3. [Build Order — What to Code First](#3-build-order--what-to-code-first)
4. [Step 1 — Data Models](#4-step-1--data-models)
5. [Step 2 — The Parser](#5-step-2--the-parser)
6. [Step 3 — The Graph](#6-step-3--the-graph)
7. [Step 4 — Pathfinding Algorithm](#7-step-4--pathfinding-algorithm)
8. [Step 5 — The Scheduler](#8-step-5--the-scheduler)
9. [Step 6 — The Simulator](#9-step-6--the-simulator)
10. [Step 7 — Visual Output](#10-step-7--visual-output)
11. [Step 8 — Main Entry Point & Makefile](#11-step-8--main-entry-point--makefile)
12. [Step 9 — Test Maps](#12-step-9--test-maps)
13. [Step 10 — Code Quality (flake8 + mypy)](#13-step-10--code-quality-flake8--mypy)
14. [Step 11 — README](#14-step-11--readme)
15. [Common Pitfalls](#15-common-pitfalls)
16. [Algorithm Deep Dive](#16-algorithm-deep-dive)
17. [Performance Targets Checklist](#17-performance-targets-checklist)

---

## 1. Project Overview

### What you are building

A Python program that:
- Reads a **map file** describing a network of zones and connections
- Routes a **fleet of drones** from a start zone to an end zone
- Respects **strict movement rules** (zone capacities, connection limits, zone types)
- Outputs each simulation turn **line by line** in a specific format
- Displays the simulation **visually** (terminal colors + optional pygame GUI)
- Does all of this in the **fewest possible turns**

### Key constraints to never forget

- No graph libraries (`networkx`, `graphlib`, etc.) — forbidden
- Must be fully **object-oriented**
- Must be fully **type-safe** (mypy + flake8 pass with zero errors)
- `restricted` zones cost **2 turns** to enter and a drone **cannot wait mid-connection**
- `blocked` zones can **never** be entered
- Zone capacity and connection capacity are **separate** constraints
- Start and end zones have **unlimited** capacity

---

## 2. Setup & File Structure

### Recommended file structure

```
fly-in/
│
├── main.py
├── Makefile
├── README.md
├── .gitignore
├── requirements.txt
│
├── parser/
│   └── map_parser.py
│
├── models/
│   ├── zone.py
│   ├── connection.py
│   ├── drone.py
│   └── graph.py
│
├── engine/
│   ├── scheduler.py
│   └── simulator.py
│
├── visual/
│   ├── terminal.py
│   └── gui.py
│
└── maps/
    ├── easy_linear.txt
    ├── easy_fork.txt
    ├── medium_loop.txt
    └── hard_maze.txt
```

### Makefile rules required

```makefile
install:   # pip install -r requirements.txt
run:       # python main.py <map_file>
debug:     # python -m pdb main.py <map_file>
clean:     # remove __pycache__, .mypy_cache
lint:      # flake8 . && mypy . --warn-return-any --warn-unused-ignores
           #   --ignore-missing-imports --disallow-untyped-defs
           #   --check-untyped-defs
```

### .gitignore minimum

```
__pycache__/
*.pyc
.mypy_cache/
*.egg-info/
.venv/
```

### requirements.txt

```
pygame       # for GUI visualization
```
> Nothing else is needed. Do NOT add networkx or any graph library.

---

## 3. Build Order — What to Code First

This is the order that makes sense. Each step depends on the previous one.

```
[1] models/zone.py          ← no dependencies
[2] models/connection.py    ← depends on zone
[3] models/drone.py         ← depends on zone
[4] models/graph.py         ← depends on zone + connection
[5] parser/map_parser.py    ← depends on all models
[6] engine/scheduler.py     ← depends on graph + drone
[7] engine/simulator.py     ← depends on all of the above
[8] visual/terminal.py      ← depends on simulator output
[9] visual/gui.py           ← depends on graph + simulator
[10] main.py                ← ties everything together
```

**Do not** jump to the simulator before the parser works.
**Do not** jump to the GUI before the terminal output is correct.
Test each layer before moving to the next.

---

## 4. Step 1 — Data Models

These are your core data structures. Think of them as the vocabulary of your program.

### `models/zone.py`

**What it represents:** A single node in the graph (a location a drone can be in).

**Fields to include:**
- `name: str` — unique identifier, no dashes, no spaces
- `x: int`, `y: int` — coordinates (used for display only, not pathfinding)
- `zone_type: ZoneType` — an Enum with values: `normal`, `blocked`, `restricted`, `priority`
- `color: Optional[str]` — for visual display
- `max_drones: int` — default 1, can be overridden in metadata
- `is_start: bool`, `is_end: bool` — flags for the special zones

**Methods to include:**
- `move_cost() -> int` — returns 2 if restricted, 1 otherwise
- `is_accessible() -> bool` — returns False if blocked

**Important design decision:** Use a `ZoneType` Enum rather than raw strings. This makes type checking reliable and prevents typo bugs.

---

### `models/connection.py`

**What it represents:** A bidirectional edge between two zones.

**Fields to include:**
- `zone_a: Zone`, `zone_b: Zone` — the two endpoints
- `max_link_capacity: int` — default 1

**Methods to include:**
- `other(zone: Zone) -> Zone` — given one endpoint, returns the other
- `key() -> tuple[str, str]` — returns a canonical (alphabetically sorted) tuple of names, used to detect duplicate connections during parsing

---

### `models/drone.py`

**What it represents:** A single drone with its current state and planned path.

**Fields to include:**
- `drone_id: int` — used to build the label `D1`, `D2`, etc.
- `current_zone: Zone` — where the drone physically is right now
- `path: list[Zone]` — the full planned route from start to end
- `path_index: int` — which step of the path it is currently on
- `state: DroneState` — an Enum: `WAITING`, `MOVING`, `IN_TRANSIT`, `DELIVERED`
- `transit_turns_left: int` — countdown for restricted zone 2-turn movement
- `wait_count: int` — how many consecutive turns the drone has waited (deadlock detection)

**Methods to include:**
- `next_zone() -> Optional[Zone]` — returns `path[path_index + 1]` or None
- `label: str` — property returning `f"D{self.drone_id}"`
- `is_delivered() -> bool`

**State machine overview:**
```
WAITING ──move possible──► MOVING ──reach end──► DELIVERED
MOVING ──blocked──► WAITING
MOVING ──toward restricted──► IN_TRANSIT
IN_TRANSIT ──next turn──► MOVING or DELIVERED
```

---

## 5. Step 2 — The Parser

**What it does:** Reads the map file line by line, validates everything strictly, and builds a `Graph` object.

**Class:** `MapParser` in `parser/map_parser.py`

**Create a custom exception:** `ParseError(Exception)` — raised with the line number and reason on any bad input.

### Parsing logic — line by line

For each non-empty, non-comment line:

| Line starts with | Action |
|---|---|
| `nb_drones:` | Parse positive integer |
| `start_hub:` | Parse zone, mark `is_start=True`, add to graph |
| `end_hub:` | Parse zone, mark `is_end=True`, add to graph |
| `hub:` | Parse zone, add to graph |
| `connection:` | Parse connection between two already-defined zones |
| `#` | Skip (comment) |
| anything else | Raise `ParseError` |

### Zone line format

```
<prefix>: <name> <x> <y> [optional metadata]
```

Metadata is everything inside `[...]`. Each token inside is `key=value`. Order of tokens is **not fixed** — parse them as a set.

Valid metadata keys for zones: `zone`, `color`, `max_drones`

### Connection line format

```
connection: <zone1>-<zone2> [optional metadata]
```

Split on `-` to get the two zone names. This is why zone names cannot contain dashes.
Validate that both zones were previously defined.
Check for duplicates using the canonical `key()` method on the connection.

Valid metadata keys for connections: `max_link_capacity`

### Validation rules to enforce

- First non-comment line must be `nb_drones`
- Exactly one `start_hub` and one `end_hub`
- All zone names must be unique
- Zone names cannot contain dashes or spaces
- Zone type must be one of the four valid values — anything else is a `ParseError`
- `max_drones` and `max_link_capacity` must be positive integers
- Connection must reference previously defined zones only
- No duplicate connections (`a-b` and `b-a` are the same)

### Testing your parser

Write small test maps that intentionally break each rule and confirm your parser catches them with a clear error message showing the line number.

---

## 6. Step 3 — The Graph

**What it does:** Stores all zones and connections, provides adjacency queries.

**Class:** `Graph` in `models/graph.py`

**Fields:**
- `zones: dict[str, Zone]` — keyed by name
- `connections: list[Connection]`
- `adjacency: dict[str, list[Connection]]` — for fast neighbor lookup
- `start: Optional[Zone]`
- `end: Optional[Zone]`

**Methods:**
- `add_zone(zone: Zone) -> None`
- `add_connection(conn: Connection) -> None` — adds to both endpoints in adjacency
- `get_neighbors(zone: Zone) -> list[tuple[Zone, Connection]]` — returns all accessible neighbors (skip blocked zones) as (zone, connection) pairs
- `dijkstra(start: Zone, end: Zone) -> Optional[list[Zone]]` — see next step
- `find_k_shortest_paths(start, end, k) -> list[list[Zone]]` — see next step

---

## 7. Step 4 — Pathfinding Algorithm

This is where you implement Dijkstra's algorithm from scratch. No heapq import is needed — you can use Python's built-in `heapq` module since it is a standard library data structure, not a graph library.

### Why Dijkstra and not BFS

Plain BFS treats all edges as cost 1. Here, entering a `restricted` zone costs 2 turns. Dijkstra handles weighted edges correctly by always expanding the cheapest known path first.

### How Dijkstra works here

- The **cost** of a path is the sum of `move_cost()` of each destination zone along the route
- Use a **min-heap** (priority queue) sorted by cumulative cost
- Keep a `costs` dict tracking the best known cost to reach each zone
- Keep a `previous` dict to reconstruct the path at the end
- Skip `blocked` zones entirely — never add them to the queue

### Finding multiple paths

For multi-drone routing you need to know all viable paths, not just the shortest one. A simple approach:

1. Find the shortest path with Dijkstra
2. For each intermediate zone on that path (not start/end), temporarily mark it as blocked and re-run Dijkstra
3. Collect any valid alternative paths found
4. Return up to `k` unique paths sorted by cost

This is not perfectly optimal (Yen's K-shortest algorithm is the theoretically correct version) but it is simple, explainable, and works well enough for this project's map sizes.

### What to return

Each path is a `list[Zone]` from start to end inclusive. The path `[start, A, B, end]` means the drone visits start → A → B → end.

---

## 8. Step 5 — The Scheduler

**What it does:** Takes the list of paths and assigns each drone to one of them, before the simulation starts.

**Class:** `Scheduler` in `engine/scheduler.py`

### Assignment strategy

The simplest strategy that works well:

- Find all available paths (up to k=5)
- Assign drones in round-robin: drone 1 → path 0, drone 2 → path 1, ..., drone k+1 → path 0 again

A better strategy (if you want better performance):

- Calculate the **bottleneck capacity** of each path (the minimum `max_drones` or `max_link_capacity` along the path)
- Assign more drones to paths with higher bottleneck capacity
- Example: path A has bottleneck 1, path B has bottleneck 2 → assign 1 drone to A, 2 drones to B per cycle

### What the scheduler produces

A `list[Drone]`, each with:
- `drone_id` assigned (1-based)
- `current_zone` set to the start zone
- `path` set to the chosen path
- `path_index` set to 0
- `state` set to `WAITING`

---

## 9. Step 6 — The Simulator

This is the most complex part of the project. Read this section carefully.

### Overview

The simulator runs a loop. Each iteration is one turn. A turn:
1. Collects what every active drone wants to do
2. Validates each proposed move against all constraints
3. Applies all valid moves simultaneously
4. Outputs the turn's log line
5. Repeats until all drones are delivered

### Key data structures per turn

You need to track, **within each turn**, the following:

```
zone_occupancy: dict[str, int]
    Current number of drones in each zone at the START of the turn.
    Used to check if a drone can enter a zone.

zone_incoming: dict[str, int]
    How many drones are committed to entering each zone this turn.
    Used to prevent exceeding max_drones.

zone_outgoing: dict[str, int]
    How many drones are committed to leaving each zone this turn.
    A drone moving out frees up space for a drone moving in (same turn).

link_usage: dict[tuple[str,str], int]
    How many drones are using each connection this turn.
    Used to enforce max_link_capacity.
```

### Turn execution logic (pseudo-code)

```
function execute_turn():
    
    moves = {}   # drone_id -> output token
    
    build zone_occupancy from current drone positions
    initialize zone_incoming, zone_outgoing, link_usage to empty
    
    sort active drones by priority
        (closer to end = higher priority, fewer conflicts)
    
    for each active drone (in priority order):
    
        if drone is IN_TRANSIT:
            handle_restricted_arrival(drone)
            continue
    
        next_zone = drone.next_zone()
        if next_zone is None:
            continue   # drone has no more steps (shouldn't happen)
    
        conn = find_connection(drone.current_zone, next_zone)
        
        # Check 1: link capacity
        if link_usage[conn.key()] >= conn.max_link_capacity:
            drone waits
            continue
        
        # Check 2: zone capacity
        # available = max_drones - current_occupants - incoming + outgoing
        available_space = next_zone.max_drones
                          - zone_occupancy[next_zone]
                          - zone_incoming[next_zone]
        if next_zone is start or end:
            available_space = infinity
        if available_space <= 0:
            drone waits
            continue
        
        # Check 3: restricted zone special case
        if next_zone is restricted:
            commit drone to IN_TRANSIT
            reserve link
            free current zone in occupancy tracking
            record output token as "D<id>-<connection_name>"
            continue
        
        # Normal move: apply it
        update zone_incoming, zone_outgoing, link_usage
        move drone to next_zone
        advance path_index
        if next_zone is end: mark DELIVERED
        record output token as "D<id>-<zone_name>"
    
    return space-separated output tokens
```

### The restricted zone rule (most important edge case)

When a drone commits to entering a `restricted` zone:
- Turn N: drone is "on the connection" — it has left its current zone but has NOT arrived yet. Output: `D1-connName`
- Turn N+1: drone **must** arrive at the restricted zone — it **cannot** wait. Output: `D1-restrictedZoneName`

This means before committing at turn N, you must verify the restricted zone will have space at turn N+1. The safe approach: only commit if the restricted zone currently has space AND no other drone is already committed to arrive there next turn.

### Deadlock detection

If a drone's `wait_count` exceeds a threshold (e.g., 10 turns), it means it is stuck. Options:
- Recalculate its path using Dijkstra with current zone capacities as constraints
- Force it to take an alternate path from `find_k_shortest_paths`
- Log a warning but continue (for now)

### Occupancy rule clarification

The subject states: "Drones moving out of a zone free up capacity for that same turn."

This means if drone A leaves zone X and drone B wants to enter zone X on the same turn, that is **valid** — even if zone X had max_drones=1. Your tracking must account for this.

```
effective_occupancy(zone) = current_occupants - outgoing + incoming
this must be <= max_drones
```

---

## 10. Step 7 — Visual Output

### Terminal output (mandatory)

Use ANSI escape codes for colored output. You must map zone colors from the map file to terminal colors.

```
Format per turn:  T<n>: D1-zoneName D2-zoneName ...
```

Color each drone label differently. Color zone names using the color metadata from the map file.

ANSI color codes reference:
```
\033[91m  red
\033[92m  green
\033[93m  yellow
\033[94m  blue
\033[90m  gray
\033[96m  cyan
\033[0m   reset
```

Print a summary at the end showing total turns, average turns per drone, and total path cost.

### Pygame GUI (recommended, not forbidden)

Build this after the core logic is verified. Suggested layout:

- Draw zones as **circles** at their `(x, y)` coordinates scaled to fit the window
- Color each circle using the zone's color metadata
- Draw connections as **lines** between zone centers
- Draw drones as **smaller colored dots** on top of their current zone
- Each frame of the pygame loop = one simulation turn (with a small delay so it is watchable)
- Show turn number and drone status in a panel

The coordinates in the map file are abstract integers. Scale them to fit your window:
```
screen_x = (zone.x / max_x) * (WIDTH - PADDING) + PADDING/2
screen_y = (zone.y / max_y) * (HEIGHT - PADDING) + PADDING/2
```

---

## 11. Step 8 — Main Entry Point & Makefile

### `main.py` responsibilities

- Accept the map file path as a command-line argument (`sys.argv[1]`)
- Print usage and exit cleanly if no argument given
- Call `MapParser.parse()` — catch `ParseError` and print the message then exit with code 1
- Call `Scheduler.assign()` to get drones with paths
- Call `Simulator.run()` to get the simulation result
- Print each turn line to stdout (the required format)
- Display terminal visualization
- Optionally launch pygame GUI

### Error handling

- All parsing errors: print to `stderr`, exit code 1
- No valid path found: print clear message to `stderr`, exit code 1
- Max turns exceeded without delivering all drones: print warning

---

## 12. Step 9 — Test Maps

Write your own test maps. This is **critical** — the evaluation maps will be different from the ones in the subject.

### Easy map to start with

```
nb_drones: 2
start_hub: start 0 0 [color=green]
end_hub: goal 4 0 [color=yellow]
hub: A 1 0 [zone=normal]
hub: B 2 0 [zone=normal]
hub: C 3 0 [zone=normal]
connection: start-A
connection: A-B
connection: B-C
connection: C-goal
```
Expected: D1 goes first, D2 follows one turn behind. Should finish in ~6 turns.

### Capacity test

```
nb_drones: 4
start_hub: start 0 0 [color=green]
end_hub: goal 3 0 [color=yellow]
hub: bottle 1 0 [zone=normal max_drones=2]
hub: wide 2 0 [zone=normal max_drones=4]
connection: start-bottle [max_link_capacity=2]
connection: bottle-wide
connection: wide-goal [max_link_capacity=2]
```

### Restricted zone test

```
nb_drones: 2
start_hub: start 0 0
end_hub: goal 3 0
hub: danger 1 0 [zone=restricted color=red]
hub: safe 2 0 [zone=normal]
connection: start-danger
connection: danger-safe
connection: safe-goal
```
Drone 1 starts moving toward `danger` on turn 1 (on the connection), arrives turn 2, then moves normally.

### Blocked zone test (parser should reject paths through it)

```
nb_drones: 1
start_hub: start 0 0
end_hub: goal 2 0
hub: wall 1 0 [zone=blocked]
connection: start-wall
connection: wall-goal
```
Expected: no valid path exists — your program should handle this gracefully.

### Two-path fork test

```
nb_drones: 3
start_hub: start 0 0
end_hub: goal 4 0
hub: A 1 1
hub: B 2 1
hub: C 1 -1
hub: D 2 -1
connection: start-A
connection: A-B
connection: B-goal
connection: start-C
connection: C-D
connection: D-goal
```
Expected: drones split across both paths.

---

## 13. Step 10 — Code Quality (flake8 + mypy)

Run these constantly while coding, not only at the end.

### flake8 rules to watch

- Max line length: 79 characters (PEP8 default). Use `\` for line continuation or restructure
- Two blank lines between top-level definitions
- One blank line between methods inside a class
- No unused imports
- No bare `except:` clauses

### mypy rules that will catch you

- Every function parameter needs a type annotation
- Every function needs a return type annotation (including `-> None`)
- Every class field initialized in `__init__` should have an annotation
- Use `Optional[X]` (or `X | None` in Python 3.10+) when something can be None
- Use `list[X]`, `dict[K, V]`, `tuple[A, B]` — not the old `List`, `Dict` from `typing`
- Use `TYPE_CHECKING` guard for circular import type hints

### Common mypy errors and fixes

| Error | Fix |
|---|---|
| `Missing return statement` | Add a `return` or change return type to `Optional` |
| `Incompatible types in assignment` | Check that None is handled before use |
| `Argument 1 has incompatible type` | Make sure the types actually match |
| `Cannot access member X for type None` | Add a None check before accessing |
| `Missing type parameters for generic type` | Use `list[str]` not just `list` |

### Docstrings (PEP 257)

Every class and every public method needs a docstring. Use Google style:

```python
def find_path(self, start: Zone, end: Zone) -> Optional[list[Zone]]:
    """Finds the shortest weighted path between two zones.

    Args:
        start: The starting zone.
        end: The destination zone.

    Returns:
        A list of zones from start to end, or None if unreachable.
    """
```

---

## 14. Step 11 — README

The README must be in English and must contain:

### Required sections

**First line (italicized):**
```
*This project has been created as part of the 42 curriculum by <your_login>.*
```

**Description:** What the project is, what problem it solves, brief overview.

**Instructions:** How to install, how to run. Example:
```
make install
make run maps/easy_linear.txt
```

**Algorithm:** Describe your choices:
- What pathfinding algorithm you used (Dijkstra) and why
- How you handle multiple drones (scheduler + round-robin or capacity-based)
- How you handle the restricted zone 2-turn rule
- How you detect and resolve deadlocks
- What your turn-by-turn simulation engine does

**Visual Representation:** Describe your terminal output and pygame GUI. Show screenshots if possible.

**Resources:**
- Link to Dijkstra's algorithm explanation
- Link to Multi-Agent Pathfinding (MAPF) concept
- Note on how AI was used (which parts, which tasks)

---

## 15. Common Pitfalls

### Parser pitfalls

- Forgetting that `b-a` is a duplicate of `a-b` — use canonical key comparison
- Not validating that connections reference previously defined zones (not just any name)
- Allowing `nb_drones` to appear anywhere instead of enforcing it as the first meaningful line
- Not stripping whitespace from parsed values before converting types

### Simulator pitfalls

- Forgetting that drones leaving a zone free up space **on the same turn** — your occupancy check must account for outgoing drones
- Processing drones sequentially instead of resolving all moves simultaneously — this causes some drones to see stale state
- Not handling the case where a drone `IN_TRANSIT` toward a restricted zone finds no space on arrival — you must prevent this commitment from happening in the first place
- Assuming the simulation will always end — add a max_turns safety limit

### Algorithm pitfalls

- Using BFS (unweighted) instead of Dijkstra — will give wrong turn counts for maps with restricted zones
- Finding only one path — multi-drone scenarios need multiple paths to be efficient
- Not checking if a path to the end exists at all — always handle the "no path" case

### Typing pitfalls

- Using `Zone` in type hints inside `zone.py` itself before the class is defined — use string literals `"Zone"` or `from __future__ import annotations`
- Circular imports between `drone.py` and `zone.py` — use `TYPE_CHECKING` guard
- Forgetting `-> None` on `__init__` and other void methods

---

## 16. Algorithm Deep Dive

### Why Dijkstra fits this project

| Feature | BFS | Dijkstra |
|---|---|---|
| Edge weights (zone costs) | ✗ ignores them | ✓ handles correctly |
| Priority zones | ✗ treats same as normal | ✓ can be weighted lower |
| Implementation complexity | low | medium |
| Library needed | no | no (just heapq) |

### The reservation table concept (for advanced scheduling)

Instead of only checking capacity at runtime, you can maintain a structure:
```
reservation[zone_name][turn_number] = count_of_drones_arriving
```

Before scheduling a drone to arrive at zone X on turn T, check that:
```
current_occupants_staying + reservation[X][T] < X.max_drones
```

This allows you to plan ahead, which is especially important for restricted zones where you need to guarantee space 2 turns in advance.

### Staggered starts

A simple but effective optimization: instead of sending all drones at turn 1, delay the start of drones sharing the same path:

- Drone 1 on path A starts at turn 1
- Drone 2 on path A starts at turn 2 (or when drone 1 has moved far enough)
- Drone 3 on path A starts at turn 3

This naturally avoids zone conflicts on paths with low capacity. The delay equals the minimum spacing needed based on the path's bottleneck capacity.

### Priority zone handling

The subject says `priority` zones cost 1 turn (same as normal) but should be **preferred** in pathfinding. The clean way to implement this: give priority zones a cost of 0.9 in Dijkstra instead of 1. This makes paths through priority zones rank higher while keeping the turn cost functionally correct (round to 1 for simulation purposes).

---

## 17. Performance Targets Checklist

Use this during testing to track your progress:

| Map | Target | Your Result | Status |
|---|---|---|---|
| Linear path, 2 drones | ≤ 6 turns | — | ⬜ |
| Simple fork, 3 drones | ≤ 6 turns | — | ⬜ |
| Basic capacity, 4 drones | ≤ 8 turns | — | ⬜ |
| Dead end trap, 5 drones | ≤ 15 turns | — | ⬜ |
| Circular loop, 6 drones | ≤ 20 turns | — | ⬜ |
| Priority puzzle, 4 drones | ≤ 12 turns | — | ⬜ |
| Maze nightmare, 8 drones | ≤ 45 turns | — | ⬜ |
| Capacity hell, 12 drones | ≤ 60 turns | — | ⬜ |
| Ultimate challenge, 15 drones | ≤ 35 turns | — | ⬜ |
| The Impossible Dream, 25 drones | < 45 turns | — | ⬜ (bonus) |

---

*Good luck. Build in order, test every layer, and never skip the type checking.*
