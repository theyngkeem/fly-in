# 🚁 Fly-in — Continuation Guide
## From Current Code State to Working Algorithm

> Based on your actual code as of now.
> Every fix includes WHY before HOW.
> Build in the exact order listed.

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Fix 1 — zone.py](#2-fix-1--zonepy)
3. [Fix 2 — drone.py](#3-fix-2--dronepy)
4. [Fix 3 — graph.py — The Rebuild](#4-fix-3--graphpy--the-rebuild)
5. [Step 4 — Dijkstra on the Graph](#5-step-4--dijkstra-on-the-graph)
6. [Step 5 — ReservationTable class](#6-step-5--reservationtable-class)
7. [Step 6 — Scheduler and Space-Time A*](#7-step-6--scheduler-and-space-time-a)
8. [Step 7 — Simulator](#8-step-7--simulator)
9. [Step 8 — main.py](#9-step-8--mainpy)
10. [Final File Structure](#10-final-file-structure)

---

## 1. Current State Assessment

### What is done and correct

| File | Status | Notes |
|---|---|---|
| `map_parser.py` | ✅ Complete | One decision remaining (inline comments) |
| `zone.py` | 🟡 95% correct | Two small issues |
| `drone.py` | 🟡 90% correct | One naming issue, one logic concern |
| `graph.py` | 🔴 Broken | Critical bugs — cannot run at all |
| `scheduler.py` | ⬜ Not started | |
| `simulator.py` | ⬜ Not started | |

### What is blocking you right now

Your `graph.py` will crash immediately when constructed because:
- `self.zones` is a `list[Zone]` but then called as `self.zones("start_hub")` — a list is not callable
- `bfs()` is referenced but not defined anywhere

Fix the models first. Do not write a single line of algorithm until the graph constructs correctly.

---

## 2. Fix 1 — zone.py

### Issue 1 — Typo in `accessible`

**Why it matters:** `self.accecible` is a public attribute that the pathfinder will read to skip blocked zones. If you later write `zone.accessible` (correct spelling) in the algorithm, Python raises `AttributeError` silently replaced by a harder-to-find bug. Fix the typo now.

**Fix:**
```
self.accecible = ...   →   self.accessible = ...
```

### Issue 2 — `capacity` can be `None` with wrong default logic

**Why it matters:** Your parser stores `None` for `max_drones` when it is not specified in the metadata. Your Zone does `capacity if capacity else 1`. The problem: if someone passes `capacity=0`, this also defaults to 1 — but 0 should have been rejected by the parser (and it is). So this works for now, but it is fragile. A cleaner way:

**Fix:**
```python
self.capacity = capacity if capacity is not None else 1
```

The `is not None` check is explicit. It only triggers when the value is literally `None`, not when it is `0` or any other falsy value.

### Issue 3 — `zone_type` can be `None` when metadata has no `zone=` key

**Why it matters:** Your parser sets `zone` key to `None` when not specified. Then `Graph.creat_zone` calls `ZoneType(None)` — this raises `ValueError` because `None` is not a valid enum value.

**Fix in Zone.__init__:**
```python
self.zone_type = zone_type if zone_type is not None else ZoneType.normal
```

But this means Graph must handle the conversion BEFORE passing to Zone. See Graph fix below.

### Issue 4 — `is_srtend` parameter name is still a typo

**Why it matters:** You fixed the logic inside (is_srt / is_end) but the parameter name `is_srtend` is still confusing. The start/end zones also have unlimited capacity — you need to override the capacity default for them.

**Fix — full corrected Zone.__init__:**
```python
def __init__(self, name: str, color: Optional[str],
             zone_type: Optional[ZoneType], capacity: Optional[int],
             zone_line_type: str, x: int, y: int):
    self.name = name
    self.color = color if color is not None else "white"
    self.zone_type = zone_type if zone_type is not None else ZoneType.normal
    self.is_start = zone_line_type == "start_hub"
    self.is_end = zone_line_type == "end_hub"
    # Start and end zones have unlimited capacity — store as large int
    if self.is_start or self.is_end:
        self.capacity = 999999
    else:
        self.capacity = capacity if capacity is not None else 1
    self.cost = 2 if self.zone_type == ZoneType.restricted else 1
    self.accessible = self.zone_type != ZoneType.blocked
    self.x = x
    self.y = y
```

### Issue 5 — Bridge should be renamed to Connection

**Why it matters:** The subject uses the word "connection" everywhere. Your parser uses `first_zone` and `destination`. Your peer reviewer will read your code and compare it to the subject. Consistent naming reduces confusion and avoids peer review questions. Also, the subject specifically talks about `max_link_capacity` — naming the class `Connection` matches the spec.

**Fix:** In `zone.py`, rename the class:
```python
class Connection:  # was Bridge
    """connection between two zones — bidirectional edge in the graph"""
    def __init__(self, zone_a: Zone, zone_b: Zone, capacity: int = 1):
        self.zone_a = zone_a      # was first_zone
        self.zone_b = zone_b      # was second_zone
        self.capacity = capacity if capacity is not None else 1

    def other(self, zone: Zone) -> Zone:
        """given one endpoint, return the other"""
        return self.zone_b if zone.name == self.zone_a.name else self.zone_a

    def key(self) -> tuple[str, str]:
        """canonical key for deduplication — alphabetically sorted"""
        names = sorted([self.zone_a.name, self.zone_b.name])
        return (names[0], names[1])
```

The `other()` method is used by the pathfinder constantly — it answers "I am at zone A, what is the other side of this connection?". The `key()` method is used by the reservation table to identify the connection regardless of direction.

---

## 3. Fix 2 — drone.py

### Issue 1 — `drone_type` should be `state`

**Why it matters:** The attribute stores the drone's current state (waiting, moving, etc.). Calling it `drone_type` is misleading — "type" usually refers to a classification, not a mutable runtime state. The simulator will read and write this field constantly. `state` is clearer and matches the algo guide.

**Fix:**
```python
self.state = drone_state   # was self.drone_type
```

Update `is_delivered()` to match:
```python
def is_delivered(self) -> bool:
    return self.state == DroneState.delivered
```

### Issue 2 — `in_bridge` state should be `in_transit`

**Why it matters:** You renamed `Bridge` to `Connection`. The state name should match. Also `in_transit` is the term used in the subject and the algo guide — it describes a drone that is between zones (on its way to a restricted zone). Consistent terminology makes peer review easier.

**Fix:**
```python
class DroneState(Enum):
    waiting = "waiting"
    moving = "moving"
    delivered = "delivered"
    in_transit = "in_transit"    # was in_bridge
```

### Issue 3 — Drone should not store `path` as a parameter

**Why it matters:** In the current design, drones are created by the Graph, but paths are computed by the Scheduler (which runs after the Graph is built). If you pass path at construction, you are forced to either compute paths during Graph construction (wrong — mixes responsibilities) or pass empty paths and set them later anyway.

The cleaner design: Drone is constructed with no path. The Scheduler assigns `drone.path` after computing it.

**Fix:**
```python
def __init__(self, drone_id: int, current_zone: Zone):
    self.drone_id = drone_id
    self.state = DroneState.waiting
    self.current_zone = current_zone
    self.path: list[Zone] = []       # assigned by Scheduler later
    self.scheduled_path: list[tuple[Zone, int]] = []  # (zone, turn) pairs
    self.wait_count = 0              # was wait_c — renamed for clarity
    self.path_index = 0              # was path_id — renamed for clarity
```

### Issue 4 — `to_reach` field is unused and unclear

**Why it matters:** `to_reach` appears to track turns remaining for restricted zone transit, but it is never explained and never used in any method. Remove it now. When you build the simulator, you will handle restricted zone transit through the scheduled path, not through a counter.

**Fix:** Remove `self.to_reach = 0`.

---

## 4. Fix 3 — graph.py — The Rebuild

This section is the most important. Your current Graph has several crashes that prevent it from running at all. Rather than patching, rebuild it correctly from scratch. The explanation for each design decision is below.

### Why `self.zones` must be a `dict[str, Zone]` not a `list[Zone]`

You need to look up zones by name constantly:
- When building connections: `connection["first_zone"]` is a string name, you need the Zone object
- When running pathfinding: neighbors are identified by name from the adjacency list
- When the simulator checks where a drone is

With a list, lookup is O(n) — you scan the whole list every time. With a dict keyed by name, lookup is O(1). Every algorithm in this project needs fast zone lookup by name.

### Why `self.adjacency` must be `dict[str, list[Connection]]` not `dict[Zone, list[Connection]]`

Your current `creat_map` uses Zone objects as dict keys. This works in Python (objects are hashable by identity) but creates a subtle problem: you can only look up neighbors if you have the exact Zone object. If you have only a zone name (which happens constantly in pathfinding), you cannot look up neighbors without first finding the Zone object.

Using zone name strings as keys: `self.adjacency["roof1"]` → gives you all connections from roof1. Simple, fast, consistent.

### Why Graph should NOT call bfs() or any pathfinding in __init__

The Graph is a data structure. It stores zones, connections, and their relationships. Pathfinding is an algorithm that uses the data structure. Mixing them violates separation of concerns — if you want to change the pathfinding algorithm, you would need to modify the Graph class.

The correct design:
- Graph.__init__ builds the data structures
- Scheduler (separate class) runs the algorithm on the Graph

### Why `start_zone` and `end_zone` must be stored explicitly

The pathfinder needs to know where to start and where to aim. Searching through all zones every time to find the one with `is_start=True` is wasteful. Store them as direct references.

### The corrected Graph class — structure

```
Graph
├── zones_dict: dict[str, Zone]         ← all zones by name
├── connections: list[Connection]        ← all connections
├── adjacency: dict[str, list[Connection]]  ← neighbors per zone
├── start_zone: Zone                     ← direct reference
├── end_zone: Zone                       ← direct reference
└── drones: list[Drone]                  ← created without paths
```

### Fixing `creat_zone`

**Current problem:** Iterates `zones.values()` correctly now, but passes `zone["optional"]["zone"]` directly which is either a string or `None`. Zone expects a `ZoneType` enum.

**Why convert here and not in Zone:** The conversion from raw string to enum belongs at the boundary between raw data (parser output) and domain objects (Zone). The Graph is that boundary. Zone should receive a clean, typed value.

**Fix:**
```
raw_zone_type = zone.get("optional", {}).get("zone") or "normal"
zone_type = ZoneType(raw_zone_type)
```

**Current problem:** `zone["optional"]` crashes if the zone had no metadata (no `optional` key in the dict).

**Why this happens:** Your parser only adds `"optional"` to the dict if `len(words) > 4`. A bare `hub: A 0 0` line produces a dict with no `"optional"` key. Then `zone["optional"]["color"]` raises `KeyError`.

**Fix:** Use `.get()` with defaults:
```
optional = zone.get("optional") or {}
color = optional.get("color")
max_drones = optional.get("max_drones")
raw_zone_type = optional.get("zone")
```

### Fixing `creat_conn`

**Current problem:** `self.zones(bridge["first_zone"])` — you are calling `self.zones` as a function. `self.zones` is a list, not a function. A list is not callable. This raises `TypeError` immediately.

**Why the confusion:** You need to look up a Zone by name. With a list you cannot do that easily. With a dict you write `self.zones_dict["roof1"]`.

**Fix:** Change `self.zones` to `self.zones_dict` (a dict) and use dict lookup:
```
zone_a = self.zones_dict[bridge["first_zone"]]
zone_b = self.zones_dict[bridge["destination"]]
```

**Current problem:** `bridge["optional"]["max_link_capacity"]` — same issue as zones. Optional may not exist.

**Fix:**
```
optional = bridge.get("optional") or {}
capacity = optional.get("max_link_capacity") or 1
```

### Fixing `creat_drone`

**Current problem:** `self.zones("start_hub")` — same callable error as above.

**Fix:** Use `self.start_zone` (stored during `creat_zone`).

```
Drone(i, self.start_zone)
```

### The corrected Graph.__init__ order

Order matters because each step depends on the previous:

```
1. creat_zone(zones)      → builds zones_dict, finds start_zone and end_zone
2. creat_conn(connection) → builds connections (needs zones_dict for lookup)
3. creat_map()            → builds adjacency (needs connections)
4. creat_drone(nb_drone)  → builds drones (needs start_zone)
# NO pathfinding here — that belongs in Scheduler
```

### Corrected creat_map

**Why use zone name as key instead of Zone object:**
Explained above. Consistent with how everything else is keyed.

```
adjacency[zone.name] = []   for every zone
for each connection:
    adjacency[conn.zone_a.name].append(conn)
    adjacency[conn.zone_b.name].append(conn)
```

### Helper method — get_neighbors

The pathfinder will call this constantly. Build it now in Graph:

```
def get_neighbors(zone: Zone) -> list[tuple[Zone, Connection]]:
    """returns (neighbor_zone, connection) pairs for a zone.
    automatically skips blocked zones."""
    result = []
    for conn in self.adjacency.get(zone.name, []):
        neighbor = conn.other(zone)
        if neighbor.accessible:
            result.append((neighbor, conn))
    return result
```

**Why return both Zone and Connection:** The pathfinder needs the Zone to check its cost and the Connection to check its capacity. Returning both avoids a second lookup.

**Why skip blocked zones here:** Blocked zones are never valid path targets. By filtering them out in `get_neighbors`, every algorithm that uses this method automatically respects this rule without needing to check for it.

---

## 5. Step 4 — Dijkstra on the Graph

### Where this lives

Add `dijkstra_to_end()` as a method of `Graph`. It runs once before any drone scheduling.

### What it produces

A dictionary: `min_turns_to_end: dict[str, float]` — the minimum number of turns to reach end_zone from every zone, ignoring capacity and other drones.

**Why float and not int:** The priority zone trick (cost 0.9 instead of 1.0 to prefer priority zones) requires float. `float('inf')` is also cleaner as the initial "unreachable" value than using a large integer.

### How it works

Run Dijkstra **backwards from end_zone**. Since all connections are bidirectional, this is identical to running it forward from end — the distances are the same. Running it backwards means you get the distance from every zone to the goal in one pass.

```
1. Create priority queue with (0.0, end_zone.name)
2. Create costs dict: {end_zone.name: 0.0}, all others: inf
3. While queue not empty:
   a. Pop (cost, zone_name) with lowest cost
   b. If cost > costs[zone_name]: skip (stale entry)
   c. For each neighbor of zone_name:
      - if neighbor is blocked: skip
      - edge_cost = neighbor.cost (1 or 2, or 0.9 for priority)
      - new_cost = cost + edge_cost
      - if new_cost < costs[neighbor.name]:
          costs[neighbor.name] = new_cost
          push (new_cost, neighbor.name) to queue
4. Return costs dict
```

### The priority zone trick

Priority zones cost 1 turn in the simulation. But in Dijkstra, give them cost 0.9 so paths through priority zones rank slightly cheaper. This makes A* naturally prefer priority zones without changing actual simulation costs.

**Why 0.9 and not 0:** Zero cost would make priority zones effectively free and could produce incorrect path lengths. 0.9 is low enough to prefer them but high enough that the heuristic remains admissible (never overestimates real cost).

### Store the result

```python
self.heuristic: dict[str, float] = self.dijkstra_to_end()
```

Call this at the END of `__init__`, after building the graph structure.

---

## 6. Step 5 — ReservationTable class

### Where this lives

New file: `engine/reservation.py`

### Why a separate class

The reservation table is used by both the Scheduler (writes to it as drones are scheduled) and optionally the Simulator (reads from it to verify). Making it a class with clear methods prevents bugs from direct dict manipulation.

### What it stores

```
zone_res[zone_name][turn_number] = drone_count
link_res[connection_key][turn_number] = drone_count
```

Both use `defaultdict(lambda: defaultdict(int))` — so you never need to initialize keys. Any unseen `zone_res["A"][5]` automatically returns 0.

### Why two separate tables

Zone capacity and connection capacity are independent constraints. A drone must satisfy BOTH to make a move:
- Zone check: the destination zone is not over capacity at the arrival turn
- Link check: the connection is not over capacity at the traversal turn

### Methods to implement

**`can_enter(zone, turn) -> bool`**
```
if zone.is_start or zone.is_end: return True  (unlimited capacity)
return zone_res[zone.name][turn] < zone.capacity
```

**`reserve_zone(zone, turn) -> None`**
```
zone_res[zone.name][turn] += 1
```

**`can_use_link(conn, turn) -> bool`**
```
return link_res[conn.key()][turn] < conn.capacity
```

**`reserve_link(conn, turn) -> None`**
```
link_res[conn.key()][turn] += 1
```

**`commit_path(path_with_turns, drone_id) -> None`**

This is the key method. Takes the full scheduled path `list[tuple[Zone, int]]` and reserves every (zone, turn) pair and every (connection, turn) pair in it.

```
for each (zone, turn) in path_with_turns:
    reserve_zone(zone, turn)
for each consecutive pair ((zone_a, turn_a), (zone_b, turn_b)) in path_with_turns:
    find the connection between zone_a and zone_b
    reserve_link(connection, turn_a)  ← turn the drone crosses the link
```

### The path format

The scheduled path is a list of `(Zone, int)` tuples:
```
[(start_zone, 0), (zone_A, 1), (zone_B, 2), (end_zone, 3)]
```

Each tuple means "this drone is at this zone at this turn."

For restricted zones, the path includes an intermediate "in-transit" entry:
```
[(zone_A, 5), (restricted_zone_R, 7)]
```

Turn 6 is the in-transit turn — the drone is on the connection. The connection between A and R is reserved at turn 6. R is reserved at turn 7.

---

## 7. Step 6 — Scheduler and Space-Time A*

### Where this lives

New file: `engine/scheduler.py`

### The Scheduler class

```
Scheduler
├── graph: Graph
├── reservation: ReservationTable
└── schedule() -> list[Drone]    ← main entry point
```

`schedule()` runs Space-Time A* for each drone and returns the list of Drone objects with their `scheduled_path` filled in.

### Staggered start turns

Before running A* for any drone, compute when each drone should launch.

**Why stagger:** All 15 drones launching at turn 0 immediately congest the distribution gates (max 1 drone each). Drones 4-15 would just wait at start. Better to delay their launch so they enter a pipeline:

```
effective_outflow = sum of capacity of all zones directly connected to start
(for your map: 3 zones × capacity 1 = 3 drones per turn)

drone D (0-indexed) launches at turn: D // effective_outflow
```

Drone 0,1,2 → turn 0
Drone 3,4,5 → turn 1
Drone 6,7,8 → turn 2
etc.

### Space-Time A* — step by step

**State:** `(zone_name: str, turn: int)`

**Initial state for drone D:** `(start_zone.name, start_turn_D)`

**Priority queue entry:** `(f_score, g_score, zone_name, turn)`
- `g_score` = turns spent so far
- `f_score` = g_score + heuristic[zone_name]

**Visited set:** `set[tuple[str, int]]` — stores `(zone_name, turn)` pairs already expanded. Never expand the same (zone, turn) twice.

**came_from dict:** `dict[tuple[str, int], tuple[str, int]]` — maps each `(zone, turn)` to the `(zone, turn)` it came from. Used to reconstruct the path at the end.

**The expansion loop:**

```
while queue not empty:
    pop (f, g, zone_name, turn)
    
    if (zone_name, turn) in visited: continue
    visited.add((zone_name, turn))
    
    if zone_name == end_zone.name:
        reconstruct path from came_from
        return path
    
    zone = graph.zones_dict[zone_name]
    
    # Option 1: Move to a neighbor
    for (neighbor, conn) in graph.get_neighbors(zone):
        arrival_turn = turn + neighbor.cost
        
        if arrival_turn > MAX_TURNS: continue
        
        # For restricted zones: check link at 'turn' and zone at 'arrival_turn'
        # For normal zones: check link at 'turn' and zone at 'arrival_turn'
        if not reservation.can_use_link(conn, turn): continue
        if not reservation.can_enter(neighbor, arrival_turn): continue
        
        # Extra check for restricted: cannot bail out mid-transit
        # So only commit if we are SURE the zone will be free
        # (already checked above — arrival_turn check handles this)
        
        new_g = g + neighbor.cost
        new_f = new_g + graph.heuristic[neighbor.name]
        new_state = (neighbor.name, arrival_turn)
        
        if new_state not in visited:
            came_from[new_state] = (zone_name, turn)
            push (new_f, new_g, neighbor.name, arrival_turn) to queue
    
    # Option 2: Wait in place
    wait_turn = turn + 1
    if wait_turn <= MAX_TURNS:
        if reservation.can_enter(zone, wait_turn):
            new_g = g + 1
            new_f = new_g + graph.heuristic[zone_name]
            wait_state = (zone_name, wait_turn)
            if wait_state not in visited:
                came_from[wait_state] = (zone_name, turn)
                push (new_f, new_g, zone_name, wait_turn) to queue

return None  # no path found
```

### Path reconstruction

```
path = []
current = (end_zone.name, arrival_turn)
while current in came_from:
    zone = graph.zones_dict[current[0]]
    path.append((zone, current[1]))
    current = came_from[current]
path.append((start_zone, start_turn))
path.reverse()
return path
```

### Committing the path

After A* returns a path for drone D:
```
drone.scheduled_path = path
reservation.commit_path(path)
```

This fills the reservation table so drone D+1 sees the slots taken by drone D.

### Handling A* failure

If A* returns None (no path found within MAX_TURNS):
```
increase start_turn by 1 and retry (up to MAX_RETRIES = 10)
if still fails after MAX_RETRIES: raise ScheduleError with clear message
```

---

## 8. Step 7 — Simulator

### Where this lives

New file: `engine/simulator.py`

### What the simulator does

Executes the pre-planned schedule turn by turn. All decisions are already made. The simulator:
1. Reads `turn_events[turn]` (built from scheduled paths)
2. Executes moves
3. Produces output lines

### Building turn_events before simulation

After scheduling all drones, build an index:

```
turn_events: dict[int, list[tuple[Drone, Zone, Zone]]] = {}
# turn → list of (drone, from_zone, to_zone)

for drone in drones:
    for i in range(len(drone.scheduled_path) - 1):
        zone_from, turn = drone.scheduled_path[i]
        zone_to, turn_to = drone.scheduled_path[i + 1]
        if zone_from != zone_to:  # skip wait entries
            turn_events[turn].append((drone, zone_from, zone_to))
```

### The turn loop

```
turn = 0
while not all drones delivered:
    turn += 1
    output_tokens = []
    
    moves = turn_events.get(turn, [])
    
    for (drone, from_zone, to_zone) in moves:
        # determine output token
        if to_zone.zone_type == ZoneType.restricted:
            # this might be the in-transit turn or the arrival turn
            # check if this is turn 1 or turn 2 of the restricted move
            conn = find_connection(from_zone, to_zone)
            if is_transit_turn(drone, turn):
                token = f"D{drone.drone_id}-{conn_name}"
            else:
                token = f"D{drone.drone_id}-{to_zone.name}"
        else:
            token = f"D{drone.drone_id}-{to_zone.name}"
        
        drone.current_zone = to_zone
        if to_zone.is_end:
            drone.state = DroneState.delivered
        else:
            drone.state = DroneState.moving
        
        output_tokens.append((drone.drone_id, token))
    
    # sort by drone id for consistent output
    output_tokens.sort(key=lambda x: x[0])
    line = " ".join(t for _, t in output_tokens)
    print(line)

print(f"\nTotal turns: {turn}")
```

### Detecting in-transit vs arrival for restricted zones

A restricted zone move appears as two consecutive steps in the scheduled path:
```
(zone_A, turn_5) → (zone_R, turn_7)    ← gap of 2 turns means restricted
```

Turn 6 is the in-transit turn (drone on the connection). Turn 7 is the arrival turn.

In your `turn_events`, you have two events:
- At turn 5-6 crossing: drone goes "onto connection" → output: `D1-zoneA-zoneR` (connection name)
- At turn 6-7 crossing: drone arrives at R → output: `D1-zoneR`

Build the output by checking the turn gap between consecutive path entries. If gap == 2, the first event is in-transit.

---

## 9. Step 8 — main.py

### Responsibilities

```
1. Read command line argument (map file path)
2. Run MapParser.parse_map()
3. Build Graph(parser.zones, parser.connections, parser.nb_drones)
4. Run Scheduler(graph).schedule()
5. Run Simulator(graph).run()
6. Display visual (terminal + optional pygame)
```

### Error handling

```python
try:
    parser = MapParser(sys.argv[1])
    parser.parse_map()
except FileNotFoundError:
    print(f"Error: file '{sys.argv[1]}' not found", file=sys.stderr)
    sys.exit(1)
except ParseError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
```

---

## 10. Final File Structure

```
fly-in/
├── main.py
├── Makefile
├── README.md
├── .gitignore
├── requirements.txt
│
├── models/
│   ├── __init__.py
│   ├── zone.py          ← Zone, ZoneType, Connection (was Bridge)
│   ├── drone.py         ← Drone, DroneState
│   └── graph.py         ← Graph (data structure + Dijkstra heuristic)
│
├── engine/
│   ├── __init__.py
│   ├── reservation.py   ← ReservationTable
│   ├── scheduler.py     ← Scheduler, Space-Time A*
│   └── simulator.py     ← Simulator, output formatting
│
├── visual/
│   ├── __init__.py
│   ├── terminal.py      ← ANSI colored output
│   └── gui.py           ← pygame display
│
├── parser/
│   ├── __init__.py
│   └── map_parser.py    ← MapParser (complete)
│
└── maps/
    ├── easy_linear.txt
    └── hard_ultimate.txt
```

---

## Build Order — What to Do Right Now

```
TODAY:
[1] Fix zone.py         → rename accessible, fix capacity/None, rename Bridge→Connection, add other() and key()
[2] Fix drone.py        → rename state, fix DroneState, remove path from init, remove to_reach
[3] Rebuild graph.py    → zones_dict, adjacency, start_zone, end_zone, get_neighbors, no bfs call
[4] Test graph builds   → create a small map dict manually and confirm Graph constructs without crash

THIS WEEK:
[5] dijkstra_to_end()   → add to Graph, test heuristic values make sense
[6] ReservationTable    → new file, test all 4 methods manually
[7] Space-Time A*       → single drone first, empty reservation table, verify matches Dijkstra
[8] Full scheduler      → all drones, staggered starts, test on easy maps
[9] Simulator           → execute schedule, verify output format
[10] Visual output      → terminal colors first, pygame after simulator confirmed correct
```

---

*Every step in this guide can be tested in isolation before moving to the next.
If step N crashes, do not proceed to step N+1.
The most common mistake is adding complexity before verifying the foundation.*
