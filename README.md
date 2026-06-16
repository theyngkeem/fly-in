*This project has been created as part of the 42 curriculum by yaarab.*

# Fly-in — Drone Routing Simulation

## Description

Fly-in is a drone routing simulation system built entirely in Python. The goal is to move a fleet of drones from a central start zone to a target end zone across a network of connected zones, in the **fewest possible simulation turns**.

The system parses a custom map format describing zone types, capacities, and connections, then applies a multi-agent pathfinding strategy (A\* per drone with space-time reservation) to schedule all drones simultaneously while respecting movement rules and capacity constraints.

**Key features:**
- Full custom map parser with strict validation and meaningful error messages
- Object-oriented architecture: `Zone`, `Bridge`, `Drone`, `Graph`, `Scheduler`, `Simulator`, `Visualizer`
- Dijkstra pre-computation from the end zone used as heuristic in A\*
- Space-time reservation table to prevent zone and connection conflicts across all drones
- Step-by-step terminal output following the required `D<ID>-<zone>` format
- Pygame-based graphical visualizer with smooth animation and keyboard controls

---

## Instructions

### Requirements

- Python 3.10 or later
- pip

### Installation

```bash
make install
```

This installs all dependencies listed in `requirements.txt` (`pygame`, `flake8`, `mypy`).

### Running

```bash
make run
# or directly:
python3 pedri.py "ur mapfile"
```

Replace the map file path with any file from the `maps/` directory, or use your own custom map.

### Debug mode

```bash
make debug
# opens pdb on the main script
```

### Linting

```bash
make lint
# runs flake8 and mypy with the required flags
```

### Cleaning

```bash
make clean
# removes __pycache__, .mypy_cache, and .pyc files
```

---

## Usage Examples

```bash
python3 pedri.py maps/easy/01_linear_path.txt
python3 pedri.py maps/medium/03_priority_puzzle.txt
python3 pedri.py maps/hard/03_ultimate_challenge.txt
```

**Terminal output example:**

```
D1-roof1 D2-corridorA
D1-roof2 D2-tunnelB
D1-goal D2-goal
wslat talabiya f 3
```

Each line represents one simulation turn. Drones that are not moving in a given turn are omitted. Drones traversing a restricted zone (2-turn cost) are shown mid-transit in the format `D<ID>-<from>-<to>` on the first turn and `D<ID>-<to>` on the second.

**Graphical visualizer controls (Pygame window opens after simulation):**

| Key | Action |
|-----|--------|
| `SPACE` | Advance one turn |
| `R` | Reset to turn 0 |
| `+` / `-` | Zoom in / out |
| Arrow keys | Pan the view |

---

## Map File Format

Maps use a plain-text format with the following syntax:

```
nb_drones: 5

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: obstacleX 5 5 [zone=blocked color=gray]

connection: hub-roof1
connection: corridorA-roof1 [max_link_capacity=2]
```

**Zone types and movement costs:**

| Type | Cost | Notes |
|------|------|-------|
| `normal` | 1 turn | Default |
| `priority` | 1 turn | Preferred by pathfinding |
| `restricted` | 2 turns | Drone occupies bridge during transit |
| `blocked` | — | Inaccessible |

Comments start with `#` and are ignored.

---

## Algorithm Choices and Implementation Strategy

### 1. Graph Construction

The graph is built from parsed map data as a set of `Zone` objects (nodes) and `Bridge` objects (edges). Adjacency is stored as a dictionary mapping each zone name to its list of connected bridges.

### 2. Dijkstra Pre-Computation (Heuristic)

Before scheduling any drone, Dijkstra's algorithm is run **backwards from the end zone** over the entire graph. This produces a distance map from every zone to the goal, which is used as the admissible heuristic `h(n)` in each drone's A\* search. Priority zones are given a cost of 0 (preferred), while normal and restricted zones cost 8000, making A\* strongly prefer priority paths.

**Complexity:** O((V + E) log V) once, amortized across all drones.

### 3. Flow-Aware Drone Scheduling

Before running A\*, the scheduler calculates the maximum outflow from the start zone (limited by adjacent bridge and zone capacities). Drones are assigned staggered start turns based on this outflow capacity, so they naturally spread out and avoid immediate bottlenecks at the exit.

### 4. A\* with Space-Time Reservation

Each drone is scheduled sequentially using A\* on a **space-time graph**: states are `(zone, turn)` pairs, and edges represent either moving to a neighbor or waiting in place. The heuristic is the Dijkstra distance computed in step 2.

A `ReservationPath` table tracks, per turn, how many drones have reserved each zone and each bridge. Before expanding a neighbor, the A\* checks that:
- The zone has available capacity at the target turn (`can_enter`)
- The bridge has available capacity at the current turn (`can_use_bridge`)

Once a path is found for a drone, it is committed to the reservation table (`use_path`), and subsequent drones plan around it.

**Key properties:**
- Conflict-free by construction — no two drones can collide if the reservation table is respected
- Start and end zones have infinite capacity (no reservation needed)
- Restricted zones cost 2 turns; the drone occupies the connection during transit and must complete the move on the next turn

**Complexity per drone:** O((T × V + E) log(T × V)) where T is the max turn horizon.

### 5. Retry Logic

If A\* fails to find a path (e.g., all paths are blocked due to reservations), the scheduler bumps the drone's start turn by 1 and retries up to 10 times. This handles cases where a drone simply needs to wait a bit before a path opens.

### 6. Simulation Output

The `Simulator` reads the scheduled paths and converts them into a turn-indexed event dictionary. It then iterates turn by turn, printing all drone movements per turn in the required `D<ID>-<zone>` format. Restricted zone transits produce a two-turn entry (mid-bridge notation on turn 1, destination on turn 2).

---

## Visual Representation

After the terminal simulation completes, a Pygame window opens showing the full zone graph.

- **Zones** are drawn as colored circles using the colors specified in the map metadata (any valid pygame color name is accepted).
- **Connections** are drawn as lines between zones.
- **Drones** are shown as cyan dots that smoothly animate between zones when `SPACE` is pressed.
- **Turn counter** is displayed in the top-left corner.

The visualizer uses the same scheduled path data as the simulator — no re-computation is needed. The auto-scaling offset algorithm ensures the graph fits the window regardless of coordinate ranges.

The graphical interface provides a clear way to follow the simulation step by step, verify movements, and understand how drones distribute across multiple paths.

---

## Performance Benchmarks

| Map | Drones | Target | Notes |
|-----|--------|--------|-------|
| Easy: linear path | 2 | ≤ 6 turns | |
| Easy: simple fork | 4 | ≤ 8 turns | |
| Easy: basic capacity | 4 | ≤ 6 turns | |
| Medium: dead end trap | 5 | ≤ 12 turns | |
| Medium: circular loop | 6 | ≤ 15 turns | |
| Medium: priority puzzle | 5 | ≤ 12 turns | |
| Hard: maze nightmare | 8 | ≤ 30 turns | |
| Hard: capacity hell | 12 | ≤ 35 turns | |
| Hard: ultimate challenge | 15 | ≤ 45 turns | |
| Challenger: impossible dream | 25 | Beat 45 turns | Optional |

---

## Resources

### Pathfinding and Graph Algorithms

- Hart, P.E., Nilsson, N.J., Raphael, B. (1968). *A Formal Basis for the Heuristic Determination of Minimum Cost Paths* — original A\* paper
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html) — used for priority queues in A\* and Dijkstra
- [Pygame documentation](https://www.pygame.org/docs/) — used for the graphical visualizer

### AI Usage

AI (Claude) was used in the following parts of this project:
- Generating the initial structure and skeleton of the `Scheduler` class and `ReservationPath` logic
- Helping debug edge cases in the restricted zone (2-turn movement) handling
- Drafting sections of this README
- Multi-Agent Path Finding With Heterogeneous Geometric
