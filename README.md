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
python3 -m venv .venv
source .venv/bin/activate
make install
```

This installs all dependencies listed in `requirements.txt` (`pygame`, `flake8`, `mypy`).

### Running

```bash
make run
# or directly:
python3 pedri.py mapfile.txt
```

The repository includes `mapfile.txt`. You can also pass your own map, or a map extracted from the subject's separate `maps.tar.gz` archive.

### Debug mode

```bash
make debug
# opens pdb with mapfile.txt; enter c to continue
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

Save the small map in **Map File Format** below as `example.txt`, then run:

```bash
python3 pedri.py example.txt
```

**Expected terminal output for that map:**

```text
D1-corridorA
D1-goal D2-corridorA
D2-goal
```

Each line represents one simulation turn. Drones that are not moving in a given turn are omitted. Drones traversing a restricted zone (2-turn cost) are shown mid-transit in the format `D<ID>-<from>-<to>` on the first turn and `D<ID>-<to>` on the second.

**Graphical visualizer controls (Pygame window opens after simulation):**

| Key | Action |
|-----|--------|
| `SPACE` | Advance one turn |
| `R` | Reset to turn 0 and fit the graph |
| `+` / `-` | Zoom in / out |
| Arrow keys | Pan the view |
| `ESC` | Close the window |

---

## Map File Format

Maps use a plain-text format with the following syntax:

```
nb_drones: 2

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: obstacleX 5 5 [zone=blocked color=gray]

connection: hub-roof1
connection: hub-corridorA
connection: corridorA-roof1 [max_link_capacity=2]
connection: corridorA-goal
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

Before scheduling any drone, Dijkstra's algorithm is run **backwards from the end zone**. For a backward step from `zone` to `neighbor`, the cost is zero if `neighbor` is a priority zone; otherwise it is `zone.cost`, the cost of the corresponding forward move. These discounted distances form an admissible lower bound `h(n)` for A\*. Actual moves still cost 1 or 2 turns; priority influences search order without making travel instantaneous.

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
- Start and end zones bypass occupancy checks; connection capacities still apply
- Restricted zones cost 2 turns; the drone occupies the connection during transit and must complete the move on the next turn

**Search complexity per drone:** O(T × (V + E) log(T × V)), where T is the number of turns searched. The schedule-dependent horizon is finite: `max(start_turn, last_delivery) + 2 × V`. After previous drones finish, this leaves enough time to traverse a simple path. This is a search bound, not a delay imposed on departures.

Each drone is planned around earlier reservations. This approach meets the supplied benchmarks but does not guarantee the globally fewest turns for every map.

### 5. Retry Logic

A fallback still retries A\* up to 10 times with a later start turn if no path is found. Normal congestion is handled by waiting inside the search; the calculated horizon replaces the old fixed 100-turn cutoff.

### 6. Simulation Output

The `Simulator` reads the scheduled paths and converts them into a turn-indexed event dictionary. It then iterates turn by turn, printing all drone movements per turn in the required `D<ID>-<zone>` format. Restricted zone transits produce a two-turn entry (mid-bridge notation on turn 1, destination on turn 2).

---

## Visual Representation

After the terminal simulation completes, a Pygame window opens showing the full zone graph.

- **Zones** use the map's colors, with labels for start, end, and special zone types. Unknown color names use gray.
- **Connections** are drawn as lines between zones.
- **Drones** appear as cyan dots with an ID, or a count when several share a position. Press `SPACE` to advance one turn.
- **Restricted moves** stop halfway along the connection on the first turn and arrive on the next. Waiting drones stay visible; delivered drones disappear at their scheduled arrival.
- **Status and controls** show the current turn, delivered count, and keyboard shortcuts. `R` restarts the replay and restores the view.

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

AI was used in the following parts of this project:
- Helping debug edge cases in the restricted zone (2-turn movement) handling
- review the project against the subject
- test edge cases
- update this README.