# 🧠 Fly-in — Algorithm Guide
## Space-Time A* for Multi-Drone Routing

> This guide picks up after `models/graph.py` is built.
> It covers everything inside `engine/scheduler.py` and `engine/simulator.py`.
> No code — only concepts, logic, and build order.

---

## Table of Contents

1. [Where You Are and Where You're Going](#1-where-you-are-and-where-youre-going)
2. [The Core Idea — Why Space-Time](#2-the-core-idea--why-space-time)
3. [Part A — The Reservation Table](#3-part-a--the-reservation-table)
4. [Part B — Single-Drone Pathfinding (Dijkstra recap)](#4-part-b--single-drone-pathfinding-dijkstra-recap)
5. [Part C — Space-Time A*](#5-part-c--space-time-a)
6. [Part D — The Heuristic](#6-part-d--the-heuristic)
7. [Part E — Restricted Zone Handling](#7-part-e--restricted-zone-handling)
8. [Part F — Connection Capacity](#8-part-f--connection-capacity)
9. [Part G — Scheduling All Drones](#9-part-g--scheduling-all-drones)
10. [Part H — Deadlock Detection and Recovery](#10-part-h--deadlock-detection-and-recovery)
11. [Part I — The Simulator](#11-part-i--the-simulator)
12. [Part J — Output Formatting](#12-part-j--output-formatting)
13. [Build Order for the Algorithm](#13-build-order-for-the-algorithm)
14. [How All Parts Connect](#14-how-all-parts-connect)
15. [Performance Analysis](#15-performance-analysis)

---

## 1. Where You Are and Where You're Going

### What you already have after the graph

At this point your program can:
- Parse a map file into `Zone` and `Connection` objects
- Store them in a `Graph` with an adjacency list
- Query neighbors of any zone
- Know which zones are blocked, restricted, priority

### What is still missing

Your program cannot yet:
- Find a path from start to end
- Route multiple drones without conflicts
- Schedule who moves when
- Output the turn-by-turn simulation

### The two classes you will build

```
engine/scheduler.py   → decides paths and timing for all drones
engine/simulator.py   → executes those decisions turn by turn and produces output
```

The scheduler is the brain. The simulator is the executor.

---

## 2. The Core Idea — Why Space-Time

### The single-drone problem vs the multi-drone problem

For one drone, finding the shortest path is a classic graph problem. Dijkstra or A* solves it perfectly.

For N drones, the challenge is completely different. Each drone's movement affects what the others can do. A zone that is free for drone 1 may be occupied when drone 2 arrives. Two drones heading toward the same zone on the same turn create a conflict.

### Why a normal graph is not enough

A normal graph only tells you about **space** — what zones exist and how they connect. It has no concept of time. Two drones cannot be in the same zone on the same turn, but a normal graph has no way to represent "drone 1 is here at turn 3, so drone 2 cannot be here at turn 3."

### The space-time graph

The solution is to add time as a second dimension. Instead of searching through **zones**, you search through **(zone, turn)** pairs.

A normal graph node is a zone:
```
zone_A
```

A space-time node is a zone at a specific turn:
```
(zone_A, turn_3)
```

Two drones can both visit zone_A without conflict as long as they do so at different turns:
```
Drone 1: (zone_A, turn_2) → no conflict
Drone 2: (zone_A, turn_5) → no conflict
```

This single insight transforms the multi-drone problem back into a single-drone pathfinding problem. Each drone searches through (zone, turn) space, avoiding slots already reserved by previous drones.

---

## 3. Part A — The Reservation Table

### What it is

The reservation table is the central data structure of the whole algorithm. It tracks how many drones are committed to be in each zone at each turn in the future.

### Structure

Think of it as a two-key dictionary:
```
reservation[zone_name][turn_number] = count_of_drones_committed_here
```

### How it starts

At the beginning, before any drone is scheduled, the table is completely empty. Every zone has zero drones committed at every turn.

### How it fills up

Every time you find a path for a drone and commit it, you update the reservation table for every step of that path:

```
Drone 1 path: start → A → B → goal
Turn 0: drone is at start  → reservation["start"][0] += 1
Turn 1: drone is at A      → reservation["A"][1] += 1
Turn 2: drone is at B      → reservation["B"][2] += 1
Turn 3: drone is at goal   → reservation["goal"][3] += 1
```

### How it prevents conflicts

Before scheduling drone 2 to arrive at zone A on turn 1, you check:
```
reservation["A"][1] + 1 <= A.max_drones ?
```

If yes — space available, the move is valid.
If no — zone is full at that turn, the drone must wait or take another route.

### Two separate reservation tables

You need one reservation table for **zones** and a separate one for **connections**:

```
zone_reservation[zone_name][turn] = drone_count
link_reservation[connection_key][turn] = drone_count
```

The connection table enforces `max_link_capacity` — how many drones can traverse the same edge on the same turn.

### The connection key

Since connections are bidirectional and you need a consistent key, use the canonical key from your `Connection` class — the alphabetically sorted tuple of zone names. Both directions of the same edge share one reservation counter.

### When drones leave the table

Once a drone reaches the end zone, it is delivered. You do not need to track it after that. For simplicity, you can keep its reservations in the table forever — they will not cause problems since the end zone has unlimited capacity.

### Start zone special case

All 15 drones begin at the start zone at turn 0. So `zone_reservation["start"][0] = 15` immediately. This is valid because the start zone has unlimited capacity. Do not apply capacity checks to the start zone.

---

## 4. Part B — Single-Drone Pathfinding (Dijkstra recap)

### Why you still need Dijkstra

Before building Space-Time A*, you should first have a working Dijkstra that ignores other drones. This serves two purposes:

1. It tells you if a path from start to end exists at all (if Dijkstra finds nothing, no drone can ever reach the goal)
2. It gives you the **heuristic** values used inside A* (the minimum possible turns from any zone to the end)

### How Dijkstra works on your graph

Dijkstra explores zones in order of cumulative cost, always expanding the cheapest known option first.

The cost of entering a zone is defined by its type:
```
normal    → 1 turn
priority  → 1 turn (but preferred, use 0.9 in Dijkstra to break ties)
restricted → 2 turns
blocked   → infinite (skip entirely, never add to queue)
```

### The priority queue

Dijkstra uses a priority queue — a data structure that always gives you the element with the smallest cost. Python's `heapq` module provides this. Each entry in the queue is `(cumulative_cost, zone_name)`.

### What Dijkstra produces

After running Dijkstra from end_hub backwards (or from start forward), you get:

```
min_cost_to_end[zone_name] = minimum turns from this zone to goal
```

Run it **backwards from the end** (treating all edges as reversible) once before scheduling any drone. Cache this result. It becomes your heuristic.

This is worth doing because:
- It runs once, O(V log V)
- It gives perfect lower-bound estimates for A*
- A* with a perfect heuristic is dramatically faster than A* with no heuristic

---

## 5. Part C — Space-Time A*

### What A* is

A* is Dijkstra with a heuristic. Instead of sorting the queue only by cost-so-far, it sorts by:

```
priority = cost_so_far + heuristic_estimate_to_goal
```

The heuristic is an estimate of how many more turns it will take to reach the end. If the estimate is accurate, A* expands nodes in a much smarter order than Dijkstra and finds the answer faster.

### The space-time node

Each node in your A* search is a `(zone, turn)` pair. When you pop a node from the priority queue, you know both where the drone is and what turn it is.

### The starting node

For drone D that starts at turn T_start:
```
initial node: (start_zone, T_start)
initial cost: 0
```

The starting turn T_start depends on when you decide to launch this drone. For the first drone, T_start = 0. For staggered starts (explained later), T_start may be 1 or 2.

### Transitions from a node

From node `(zone_Z, turn_T)`, there are two possible transitions:

**Move to a neighbor N:**
```
new_node = (N, T + N.move_cost())
new_cost = current_cost + N.move_cost()
```

But this transition is only valid if:
```
zone_reservation[N][T + N.move_cost()] + 1 <= N.max_drones
AND
link_reservation[conn_key][T] + 1 <= conn.max_link_capacity
AND
N is not blocked
```

**Wait in place:**
```
new_node = (zone_Z, T + 1)
new_cost = current_cost + 1
```

But this is only valid if:
```
zone_reservation[zone_Z][T + 1] + 1 <= zone_Z.max_drones
```

(Start and end zones skip the capacity check — they have unlimited capacity.)

### The goal condition

The search ends when you pop a node where `zone == end_hub`. The turn at which this happens is the arrival turn for this drone.

### Preventing revisiting

In a normal graph, you never want to visit the same zone twice (cycles waste turns). In space-time, the concept is different — you never want to visit the same `(zone, turn)` pair twice. Keep a `visited` set of `(zone_name, turn)` tuples. If you pop a node that is already in visited, skip it.

### The path reconstruction

As in Dijkstra, keep a `came_from` dictionary:
```
came_from[(zone_name, turn)] = (previous_zone_name, previous_turn)
```

When you reach the end, trace back through `came_from` to reconstruct the full path as a sequence of `(zone, turn)` pairs.

### The maximum turn limit

Space-time graphs can grow very large if drones wait a long time. Set a hard limit:
```
if turn > MAX_TURN_SEARCH:
    do not expand this node
```

A reasonable limit is 3× the number of zones × number of drones. If no path is found within this limit, something is fundamentally wrong (deadlock in scheduling, disconnected graph, etc.).

---

## 6. Part D — The Heuristic

### What a heuristic is

The heuristic is a function `h(zone)` that estimates how many more turns it will take to reach the end from `zone`. It must never overestimate (this property is called admissibility). If it overestimates, A* may miss the optimal path.

### Why the heuristic matters

Without a heuristic (h=0), A* degenerates to Dijkstra — correct but slower. With a good heuristic, A* focuses its search toward the goal and finds the answer faster, which matters when scheduling 15 drones.

### Computing the heuristic

Run Dijkstra **backwards from end_hub** once, before any drone scheduling:

1. Start Dijkstra at end_hub with cost 0
2. Traverse all edges in reverse (since edges are bidirectional, this is the same graph)
3. Record the shortest path cost from end_hub to every zone

The result: `min_turns_to_end[zone_name]` = minimum turns from that zone to the goal, ignoring other drones and ignoring capacity constraints.

This is admissible because real paths can only cost the same or more (due to other drones blocking and forcing waits).

### Using the heuristic in A*

When you push a node `(zone, turn)` onto the priority queue, its priority is:
```
priority = turns_spent_so_far + min_turns_to_end[zone.name]
```

This makes A* always try the node that looks most promising (low total estimated cost) first.

### Special case: restricted zones in the heuristic

When running Dijkstra backwards to compute the heuristic, use the actual move costs (restricted = 2). This gives more accurate estimates and better A* performance.

---

## 7. Part E — Restricted Zone Handling

### The problem

Restricted zones cost 2 turns to enter. This means:

- Turn T: drone commits to moving toward restricted zone R. The drone leaves its current zone and is "on the connection." It is no longer at its origin but has not yet arrived at R.
- Turn T+1: drone MUST arrive at R. It cannot wait on the connection. It cannot back out.

This creates a strict constraint: before committing at turn T, you must guarantee R has space at turn T+1.

### How to handle this in Space-Time A*

When the A* search considers moving from zone Z to restricted zone R at turn T:

**Check 1:** Is there space on the connection at turn T?
```
link_reservation[conn_key][T] + 1 <= conn.max_link_capacity
```

**Check 2:** Will R have space at turn T+1?
```
zone_reservation[R][T+1] + 1 <= R.max_drones
```

**Both must be true.** If either fails, this transition is skipped entirely. The drone does not attempt a partial commitment — it either commits fully or waits at Z.

### The in-transit state

In the space-time model, you represent the in-transit state as a special node:
```
(connection_A_R, turn_T)
```

This means the drone is on the connection from A to R during turn T. The next node must be:
```
(zone_R, turn_T+1)
```

There is no option to stay at the connection node — it must always transition to the arrival node. This is enforced by the structure of your A* search.

### Reservations during transit

When a drone is committed in transit:
- The connection `A-R` is reserved at turn T → increment `link_reservation`
- Zone R is reserved at turn T+1 → increment `zone_reservation`
- Zone A's occupancy decreases after turn T (the drone has left)

### The 2-turn cost in practice

In your space-time path, a restricted zone entry looks like this:
```
(A, T) → (connection_A_R, T) → (R, T+1) → (next_zone, T+2)
```

Graphically, the drone spends turn T in transit and arrives at turn T+1. The cost from A to having left R is 2 turns total.

---

## 8. Part F — Connection Capacity

### What max_link_capacity means

A connection with `max_link_capacity=2` means at most 2 drones can traverse it simultaneously. This applies to both directions combined — it is the total traffic on that edge in one turn.

### How to enforce it in space-time

Before committing a drone to traverse connection C at turn T:
```
link_reservation[C.key()][T] + 1 <= C.max_link_capacity
```

If this check fails, the drone must wait or take a different route.

### Bidirectional traffic conflict

Two drones crossing in opposite directions on the same edge at the same turn:
```
Drone 1: A → B at turn T
Drone 2: B → A at turn T
```

Both use connection A-B at turn T. If `max_link_capacity=1`, only one can go. The one that is scheduled second will be forced to wait.

In your reservation table, both directions use the same key `(min_name, max_name)` and share the same counter. This naturally prevents over-capacity bidirectional traffic.

---

## 9. Part G — Scheduling All Drones

### The cooperative scheduling approach

You schedule drones one at a time, in order. Each drone uses the reservation table as it exists after all previous drones have been committed. This means each drone automatically avoids conflicts with all previously scheduled drones.

The quality of this approach depends on the order in which drones are scheduled.

### Scheduling order

The simplest approach: schedule drone 1, then drone 2, then drone 3, up to N. Each finds the optimal path given the reservations already in place.

A better approach: prioritize drones that have harder paths (longer minimum distances) by scheduling them first. They get first choice of the uncongested graph.

For this project, sequential scheduling in order 1..N is sufficient to hit the performance benchmarks.

### Staggered starts

A key optimization: do not send all 15 drones at turn 0. Instead, calculate the optimal start turn for each drone based on the distribution gate capacity.

Looking at your map: 3 distribution gates, each with `max_drones=1`. This means at most 3 drones can leave the start zone per turn. Drone 4 must wait until turn 1, drone 7 until turn 2, etc.

More precisely:
```
effective_throughput = sum of max_drones of all zones adjacent to start
```

For your map: `1 + 1 + 1 = 3`. So the stagger interval is:
```
drone_D_start_turn = floor((D-1) / effective_throughput)
```

Drone 1, 2, 3 → start turn 0
Drone 4, 5, 6 → start turn 1
Drone 7, 8, 9 → start turn 2
...

When running Space-Time A* for drone D, use `start_turn` as the initial turn instead of 0. The search will naturally find the correct arrival time.

### What the scheduler produces

After scheduling all N drones, you have for each drone:
```
drone.scheduled_path = list of (zone, turn) pairs from start to goal
```

This is the complete schedule: where each drone is at every turn from launch to delivery.

### Building the turn map for the simulator

After scheduling, build a turn-indexed data structure for the simulator:

```
turn_events[turn_number] = list of (drone_id, from_zone, to_zone) movements
```

The simulator iterates through turns and executes the pre-planned movements. It does not make decisions — all decisions were made by the scheduler.

---

## 10. Part H — Deadlock Detection and Recovery

### When deadlocks happen in the scheduler

Space-Time A* with a reservation table is largely deadlock-free because each drone searches for a valid path before committing. However, deadlocks can still happen in edge cases:

**Circular waiting:** Drone 1's optimal path requires a zone that drone 2 is occupying. Drone 2's optimal path requires a zone that drone 1 is occupying. Both paths are planned without knowledge of each other if you are not careful about the commit order.

This does NOT happen in the cooperative scheduling approach because you commit drones one at a time. Drone 2 sees drone 1's reservations and routes around them.

**Unreachable goal:** If the reservation table is so full that no valid space-time path exists for a drone within the max turn limit. This can happen if:
- Capacity constraints are so tight that the drone must wait indefinitely
- The graph has a chokepoint with too little capacity for all drones

### How to detect

If Space-Time A* returns no path for a drone (exhausted all nodes within max turn limit), that is a scheduling failure. It needs recovery.

### Recovery strategies

**Strategy 1 — Increase start turn:**
If drone D fails to find a path starting at turn T, try again starting at turn T+1, T+2, etc. This gives the graph time to clear up before the drone launches.

**Strategy 2 — Reschedule earlier drones:**
Remove the last few committed drones from the reservation table, then reschedule them in a different order. This is expensive but sometimes necessary.

**Strategy 3 — Path diversity:**
Before scheduling, find the top-K paths using Dijkstra (without time). Assign different drones to different base paths, then use Space-Time A* to fine-tune timing within each path group.

For this project, Strategy 1 alone handles almost all cases. Strategy 2 is only needed for the Challenger bonus map.

### Deadlock in the simulator (different issue)

If the simulator executes turns and finds that a drone cannot move for more than N consecutive turns, that means the scheduler made an error. The simulator should log a warning and stop rather than loop forever. This should not happen if the scheduler is correct.

---

## 11. Part I — The Simulator

### The simulator's role

By the time the simulator runs, all decisions have already been made by the scheduler. The simulator's job is to:

1. Execute the pre-planned schedule turn by turn
2. Verify that all capacity constraints are respected
3. Produce the output lines in the required format
4. Optionally display the visual representation

### Why verify if the scheduler already planned everything?

The scheduler works with reservation tables which are a simplified model. The simulator enforces the actual rules. Running both gives you a second layer of safety — if the scheduler made any mistake (off-by-one in turn counting, wrong capacity check), the simulator catches it.

### The turn loop

The simulator runs from turn 1 until all drones are delivered. At each turn:

**Step 1 — Collect all moves for this turn:**
Look up `turn_events[current_turn]` from the pre-built schedule. This gives you all `(drone, from, to)` movements planned for this turn.

**Step 2 — Verify moves:**
For each move, check that the actual current zone occupancy allows it. This is the verification step — it should always pass if the scheduler was correct.

**Step 3 — Apply moves simultaneously:**
Update all drone positions at once. The key rule: drones moving out of a zone free up space on the SAME turn. Process all departures before processing all arrivals.

**Step 4 — Handle in-transit drones:**
Drones committed to a restricted zone must arrive this turn. Flag them and force their arrival regardless of waiting logic.

**Step 5 — Mark delivered drones:**
Any drone that arrives at end_hub this turn is delivered and removed from active tracking.

**Step 6 — Build the output line:**
For all drones that moved, build the token string. Format each token as `D<id>-<zone_name>` or `D<id>-<connection_name>` for in-transit moves.

**Step 7 — Advance turn counter.**

### Zone occupancy during a turn

The tricky part is computing what is "occupied" during a turn. Use this model:

```
occupied_after_turn = 
    current_occupants
    - drones_leaving_this_turn
    + drones_arriving_this_turn
```

This must be <= `zone.max_drones` for every non-start, non-end zone.

### Handling the in-transit output format

When a drone is in transit toward a restricted zone (turn 1 of a 2-turn move), the output token is the connection name, not the destination zone:

```
D3-dist_gate1-maze_loop1   ← drone 3 is on the connection toward maze_loop1
```

On the next turn, when it arrives:
```
D3-maze_loop1              ← drone 3 has arrived
```

Store the connection name in your drone's in-transit state so the simulator can look it up when generating output.

---

## 12. Part J — Output Formatting

### The required format

Each line of output represents one simulation turn. It contains all drone movements for that turn, space-separated:
```
D1-zoneA D2-zoneB D3-connectionName
```

Rules:
- Drones that do not move are omitted from the line
- Drones that are delivered (at end_hub) are never mentioned again
- The line can be empty if no drone moves that turn (output an empty line or skip it — decide consistently)
- Drones in the output are sorted by drone ID for readability

### Tracking what to output

As the simulator executes each turn, build a list of movement tokens:

For a normal move to zone Z: `f"D{drone.id}-{Z.name}"`
For an in-transit move toward restricted zone R via connection C: `f"D{drone.id}-{C.name}"`
For a drone waiting: nothing (omit)

### The summary at the end

After all drones are delivered, print:
```
Total turns: N
Drones delivered: D
Average turns per drone: X.X
```

These secondary metrics are not required for grading but expected by the subject for peer evaluation.

---

## 13. Build Order for the Algorithm

Build in this exact order. Each step can be tested before moving to the next.

### Phase 1 — Pathfinding foundation
```
[1] Dijkstra on the graph (single drone, no time)
    → test: find shortest path on easy maps
    → verify: restricted zones cost 2 turns
    → verify: blocked zones are never included

[2] Backwards Dijkstra from end_hub
    → builds min_turns_to_end for all zones
    → test: distances look reasonable on your visual map
```

### Phase 2 — Reservation table
```
[3] Build ReservationTable class
    → zone_reservation[zone][turn] = count
    → link_reservation[conn_key][turn] = count
    → methods: can_enter(zone, turn), reserve(zone, turn), can_use_link(key, turn), reserve_link(key, turn)
    → test: manually reserve slots, verify checks work
```

### Phase 3 — Space-Time A*
```
[4] Space-Time A* for single drone
    → state: (zone_name, turn)
    → transitions: move (check zone + link reservation), wait (check zone reservation)
    → heuristic: min_turns_to_end[zone_name]
    → goal: reached end_hub at any turn
    → test: single drone, empty reservation table → should match Dijkstra result

[5] Add restricted zone handling
    → detect when neighbor is restricted
    → check reservation for arrival turn (T+1)
    → use in-transit node in path representation
    → test: path through restricted zone costs 2 turns

[6] Add connection capacity handling
    → check link_reservation before any move
    → test: two drones on same connection simultaneously respects max_link_capacity
```

### Phase 4 — Scheduler
```
[7] Schedule first drone
    → run Space-Time A* for drone 1 at start_turn=0
    → fill reservation table with its path
    → test: path is valid, reservations are correct

[8] Schedule all N drones sequentially
    → compute staggered start turns
    → run Space-Time A* for each drone
    → commit each path to the reservation table before scheduling the next
    → test: all drones get paths, no conflicts in reservations

[9] Build turn_events map from all scheduled paths
    → turn_events[T] = list of (drone_id, zone, move_type) for that turn
```

### Phase 5 — Simulator
```
[10] Basic simulator loop
    → iterate turns from 1 to max
    → execute pre-planned moves from turn_events
    → print output line each turn
    → test: output format is correct on easy maps

[11] Add in-transit handling
    → detect restricted zone moves
    → output connection name on turn 1, zone name on turn 2
    → test: restricted zone paths produce correct 2-line output

[12] Add delivered tracking
    → mark drones at end_hub as delivered
    → stop tracking them in output
    → end simulation when all delivered

[13] Add verification layer
    → check actual occupancy at each turn matches reservations
    → log warnings if mismatches found
```

### Phase 6 — Optimization
```
[14] Test against performance benchmarks
    → easy maps: should pass immediately
    → medium maps: likely pass with basic scheduling
    → hard maps: may need stagger tuning or path diversity

[15] Add deadlock recovery
    → if Space-Time A* fails for a drone, increase its start_turn
    → retry up to max_retries times
    → log if still fails
```

---

## 14. How All Parts Connect

```
                    ┌─────────────────────────────────┐
                    │          Graph (built)           │
                    │  zones, connections, adjacency   │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │     Backwards Dijkstra          │
                    │  min_turns_to_end[zone] = cost  │
                    └──────────────┬──────────────────┘
                                   │ heuristic values
                    ┌──────────────▼──────────────────┐
                    │       Reservation Table          │
                    │  zone_res[zone][turn] = count    │
                    │  link_res[conn][turn] = count    │
                    └──────────────┬──────────────────┘
                                   │ checked and updated
                                   │ for each drone
                    ┌──────────────▼──────────────────┐
                    │        Space-Time A*             │
                    │  state: (zone, turn)             │
                    │  transitions: move / wait        │
                    │  heuristic: min_turns_to_end     │
                    └──────────────┬──────────────────┘
                                   │ one path per drone
                    ┌──────────────▼──────────────────┐
                    │          Scheduler               │
                    │  runs A* for each drone          │
                    │  staggered start turns           │
                    │  builds turn_events map          │
                    └──────────────┬──────────────────┘
                                   │ turn_events[T]
                    ┌──────────────▼──────────────────┐
                    │          Simulator               │
                    │  executes turn by turn           │
                    │  verifies capacity rules         │
                    │  produces output lines           │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │      Visual + Output             │
                    │  terminal ANSI lines             │
                    │  pygame animation                │
                    └─────────────────────────────────┘
```

---

## 15. Performance Analysis

### Time complexity

**Backwards Dijkstra:** O(V log V) where V = number of zones. Runs once.

**Space-Time A* per drone:** O(V × T × log(V × T)) where T = max turns searched. In practice T is bounded by your max_turn_limit. With a good heuristic, only a fraction of nodes are ever expanded.

**Scheduling N drones:** O(N × V × T × log(V × T)). For 15 drones on a map with ~30 zones and T ≤ 100, this is fast enough to run instantly.

**Simulator:** O(T × N) — linear in turns and drones.

### Memory complexity

**Reservation table:** O(V × T × N) in the worst case. In practice much smaller because most zones are empty most of the time. Use a defaultdict with default 0 rather than pre-allocating the full table.

**Space-time A* search nodes:** O(V × T) per drone search. The visited set and came_from dict grow to at most this size.

### Why this beats naive approaches

**Naive sequential (all drones same path, wait in line):**
For 15 drones, 1 drone arrives per turn at the end → minimum 15 turns just for final delivery. Plus path length. Total could be 30+ turns.

**Space-Time A* with staggered starts:**
Multiple paths used simultaneously. Drones flow in a pipeline. The constraint is the bottleneck throughput, not sequential queuing.

**For your specific map:**
- 3 paths through layer 5 (restricted, normal, priority)
- `final_gate3` has max_drones=1, so minimum 15 turns for all deliveries
- With 3 distribution gates: 5 turns to launch all 15 drones
- Total theoretical minimum: approximately 20-25 turns

Space-Time A* will get close to this theoretical minimum automatically.

### Caching note

Once the backwards Dijkstra heuristic is computed, cache it. Do not recompute it for each drone. It never changes — it is based on the static graph, not the reservation table.

---

*Build Phase 1 and 2 first, test them, then move to Phase 3.
Do not move to the simulator until Space-Time A* produces correct single-drone paths.
The whole algorithm is only as good as the reservation table being correctly maintained.*
