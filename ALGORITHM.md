# Fly-in — Algorithm Deep Dive

This document explains, in detail, every algorithmic piece of the Fly-in drone routing
simulator: what it does, why it was chosen, how it is implemented, and what its
complexity is. It is meant to be read alongside the source code (`elemnts/graph.py`,
`elemnts/schedular.py`, `elemnts/simulator.py`) and to be usable as reference material
during peer evaluation.

## 1. Problem Restated

We have a graph of zones connected by bridges. A fleet of `N` drones must travel from
a single `start` zone to a single `end` zone, in the minimum number of simulation
turns, while respecting:

- **Zone capacity**: at most `max_drones` drones in a zone at once (start/end are
  unlimited).
- **Connection capacity**: at most `max_link_capacity` drones crossing a bridge at
  once.
- **Zone movement cost**: `normal` and `priority` zones cost 1 turn to enter,
  `restricted` zones cost 2 turns (and cannot be "paused" mid-transit — the drone must
  land on arrival), `blocked` zones cannot be entered at all.

This is a **multi-agent pathfinding (MAPF) problem with time-extended capacity
constraints**. The general MAPF problem is NP-hard, so the project uses a practical,
well-known decoupled strategy: plan one agent at a time on a shared space-time graph,
using each agent's committed path to constrain the next.

## 2. Overall Pipeline

```
MapParser -> Graph -> Scheduler -> Simulator -> Visualizer
  (parse)   (model)   (plan)       (print)      (animate)
```

Each stage is a separate class with a single responsibility (`map_parsing.py`,
`elemnts/graph.py`, `elemnts/schedular.py`, `elemnts/simulator.py`,
`vsualization/visualizer.py`), which is what satisfies the "completely object-oriented"
constraint from the subject.

## 3. Graph Construction (`Graph.__init__`)

The parser hands the `Graph` class three things: a dict of raw zone definitions, a
list of raw connection definitions, and the drone count. `Graph` turns these into
typed objects:

- `creat_zone`: builds one `Zone` object per parsed zone, resolving optional metadata
  (`color`, `zone` type, `max_drones`) to their defaults, and recording references to
  the unique `start_hub` and `end_hub`.
- `creat_conn`: builds one `Bridge` object per connection, resolving
  `max_link_capacity` to its default of 1.
- `creat_map`: builds an adjacency dictionary `{zone_name: [Bridge, ...]}` so that
  `get_nighbor(zone)` can return, in O(degree), the list of `(neighbor_zone, bridge)`
  pairs reachable from a zone (skipping zones marked `blocked`, since `Zone.accecible`
  is `False` for that type).
- `creat_drone`: instantiates `N` `Drone` objects, all starting at `start_hub`, in
  `waiting` state.

**Why this matters:** by resolving all defaults and metadata once at construction
time, every later component (the heuristic, the scheduler, the visualizer) can work
with a simple, uniform `Zone`/`Bridge` interface and never has to re-parse strings or
re-check for `None` metadata.

## 4. The Heuristic: Reverse Dijkstra from the Goal (`Graph.djikstra`)

Before any drone is scheduled, the `Graph` runs **one** Dijkstra pass, seeded at the
`end_hub` with cost 0, and relaxes outward over the *undirected* adjacency (since
bridges are bidirectional, "distance from X to goal" equals "distance from goal to
X").

```python
def djikstra(self) -> dict[Zone | None, float]:
    tobo: list = []
    heapq.heappush(tobo, (0.0, "", self.end_hub))
    costs = {self.end_hub: 0.0}
    while tobo:
        cost, _, zone = heapq.heappop(tobo)
        if cost > costs[zone]:
            continue
        for nighbor, _ in self.get_nighbor(zone):
            if not nighbor.accecible:
                continue
            if nighbor.zone_type == ZoneType.priority:
                ncost = cost + 0
            else:
                ncost = cost + 8000
            if nighbor not in costs or ncost < costs[nighbor]:
                costs[nighbor] = ncost
                heapq.heappush(tobo, (ncost, nighbor.name, nighbor))
    return costs
```

**What the edge weights actually encode.** This is not a shortest-*distance* Dijkstra
in the usual sense — it is a **shortest-priority-detour** Dijkstra. Moving into a
`priority` zone costs `0`, moving into anything else costs `8000`. Because Dijkstra
always expands the lowest-cost frontier first, this means: among all zones reachable
from the goal, the ones reachable through the most `priority` zones (and the fewest
"non-priority hops") get the lowest score. The resulting `costs` dictionary is used
purely as a **heuristic bias**, not as a true distance metric — its job is to make the
A* search in step 5 *prefer* routes through `priority` zones whenever a free choice
exists, exactly as the subject requires ("should be prioritized in pathfinding"),
without forcing every drone down the same single route (which a literal
shortest-path-only heuristic would do, causing artificial bottlenecks).

**Complexity:** O((V + E) log V), since it's a single classic Dijkstra over the
zone graph (V zones, E bridges). It runs exactly once, regardless of how many drones
there are.

**Why not BFS or plain unweighted Dijkstra here?** A plain hop-count distance would
treat every non-priority path as equally good, giving the per-drone A* no signal to
break ties toward zones the subject says should be preferred. Encoding the preference
directly in the heuristic graph means the preference is respected automatically by
A*'s usual `f = g + h` ordering, with zero extra logic in the per-drone search.

## 5. Per-Drone Scheduling: Space-Time A* (`Scheduler.a_star`)

This is the core of the project. Each drone is scheduled **one at a time**, in drone-ID
order, using A* search over a **space-time graph** instead of the plain zone graph.

### 5.1 What a "state" is

A node in this search is not just a `Zone` — it's a pair `(zone, turn)`. Two drones can
both eventually be at zone `roof1`, just not at the same turn (unless capacity allows
it). Searching over `(zone, turn)` pairs is what lets the algorithm reason about
*when* a zone is free, not just *whether* it's reachable.

### 5.2 The search loop

```python
def a_star(self, drone: Drone, start_turn: int) -> list | None:
    tobo: list = []
    start = (self.graph.start_hub, start_turn)
    g = 0
    f = g + self.graph.best_op[self.graph.start_hub]
    heapq.heappush(tobo, (f, g, "", start[0], start[1]))
    visited = set()
    from_zone: dict = {}
    g_arch = {start: 0}
    while tobo:
        f, g, _, zone, turn = heapq.heappop(tobo)
        if (zone, turn) in visited:
            continue
        visited.add((zone, turn))
        if zone.is_end:
            return self.get_path(from_zone, (zone, turn), start_turn)
        for nighbor, bridge in self.graph.get_nighbor(zone):
            to_move = turn + nighbor.cost
            if to_move > self.max_wait:
                continue
            if not self.reservation.can_enter(nighbor, to_move):
                continue
            if not self.reservation.can_use_bridge(bridge, turn):
                continue
            new_g = g + nighbor.cost
            new_zone = (nighbor, to_move)
            if new_zone in g_arch and new_g > g_arch[new_zone]:
                continue
            g_arch[new_zone] = new_g
            from_zone[new_zone] = (zone, turn)
            new_f = new_g + self.graph.best_op[nighbor]
            heapq.heappush(tobo, (new_f, new_g, nighbor.name, nighbor, to_move))

        wait_c = turn + 1
        if wait_c <= self.max_wait:
            if self.reservation.can_enter(zone, wait_c):
                new_g = g + 1
                wait_zone = (zone, wait_c)
                if wait_zone not in g_arch or new_g < g_arch[wait_zone]:
                    g_arch[wait_zone] = new_g
                    from_zone[wait_zone] = (zone, turn)
                    new_f = new_g + self.graph.best_op[zone]
                    heapq.heappush(tobo, (new_f, new_g, zone.name, zone, wait_c))
    return None
```

Two kinds of transitions are expanded from each state `(zone, turn)`:

1. **Move to a neighbor.** `to_move = turn + nighbor.cost` (1 turn for normal/priority,
   2 turns for restricted). Before this edge is allowed:
   - `to_move` must not exceed `max_wait` (a safety bound against runaway search,
     currently 100 turns) — this also implicitly enforces the "restricted zone must be
     reached exactly 2 turns later, no idling on the connection" rule, since the
     transition jumps straight from `turn` to `turn + 2` with no intermediate state.
   - `reservation.can_enter(nighbor, to_move)` must hold: the destination zone must
     have free capacity at the arrival turn.
   - `reservation.can_use_bridge(bridge, turn)` must hold: the bridge must have free
     capacity at the turn the drone starts crossing it.
2. **Wait in place.** The drone can stay at `zone` for one more turn, costing `g + 1`,
   as long as the zone has capacity at `turn + 1`. This is what lets drones absorb
   congestion instead of failing outright when their first-choice path is briefly
   full.

Both transitions get the cost-so-far (`g`) combined with the Dijkstra heuristic for
the *target* zone (`new_f = new_g + self.graph.best_op[nighbor]`), giving the standard
A* priority `f = g + h`. Because `best_op` was computed once for the whole graph, this
lookup is O(1) per expansion.

**Termination:** the moment a popped state's zone `is_end`, the search stops and
reconstructs the path — exactly as in textbook A*, the first time the goal is popped
from the priority queue, it is guaranteed optimal under an admissible/consistent
ordering of the open list.

**Complexity per drone:** each distinct `(zone, turn)` pair is visited at most once
(`visited` set), and turn is bounded by `max_wait`, so in the worst case the search
explores O(V × max_wait) states, each with O(degree) neighbor expansions, giving
O(V × max_wait × E) in the absolute worst case — in practice far smaller, since most
states are never reached before the goal is found.

### 5.3 Reservation Table (`ReservationPath`)

```python
class ReservationPath:
    def __init__(self) -> None:
        self.zone_reservation: dict = defaultdict(lambda: defaultdict(int))
        self.bridge_reservation: dict = defaultdict(lambda: defaultdict(int))

    def can_enter(self, zone: Zone, turn: int) -> Any:
        if zone.is_srt or zone.is_end:
            return True
        return self.zone_reservation[zone.name][turn] < zone.capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        self.zone_reservation[zone.name][turn] += 1

    def reserve_bridge(self, bridge: Bridge, turn: int) -> None:
        self.bridge_reservation[bridge.dup_check()][turn] += 1

    def can_use_bridge(self, bridge: Bridge, turn: int) -> Any:
        return self.bridge_reservation[bridge.dup_check()][turn] < bridge.cp
```

This is a **nested counting table**: `zone_reservation[zone_name][turn]` is simply
"how many drones have already committed to being in this zone at this turn." Checking
capacity is O(1); reserving is O(1). `bridge.dup_check()` returns a sorted
`(name1, name2)` tuple so that the bridge `a-b` and a hypothetical lookup from either
direction always map to the same dictionary key, regardless of which zone the drone
is travelling *from*.

Once a drone's full path is found, `use_path` commits every `(zone, turn)` visit and
every bridge crossing into this table **before the next drone is searched**:

```python
def use_path(self, path: list[Tuple[Zone, int]], graph: Graph) -> None:
    for zone, turn in path:
        self.reserve_zone(zone, turn)
    for i in range(len(path) - 1):
        zone1, turn = path[i]
        zone2, _ = path[i + 1]
        if zone1 == zone2:
            continue
        for neighbor, bridge in graph.get_nighbor(zone1):
            if neighbor.name == zone2.name:
                self.reserve_bridge(bridge, turn)
                break
```

This is what gives the whole multi-drone schedule its conflict-free guarantee: drone
`k+1`'s A* search physically cannot route through a `(zone, turn)` or `(bridge, turn)`
slot that drone `k` already occupies, because `can_enter`/`can_use_bridge` will return
`False` for it. There is no separate "conflict detection and replanning" phase needed
— conflicts are made *unreachable* by construction, which is simpler and faster than
detect-and-repair approaches (like Conflict-Based Search) at the cost of not
guaranteeing a globally optimal makespan (decoupled planning is a well-known tradeoff
in MAPF literature — see Resources).

## 6. Staggering Drones at the Start: Flow Calculation (`Scheduler.calcul_flow`)

If all `N` drones simply started their A* search at `turn = 0`, the first drone to be
scheduled would greedily claim every outgoing slot from `start_hub`, and the *order*
in which drones are scheduled would arbitrarily determine who gets a fast path and who
gets stuck waiting. `calcul_flow` avoids this by **pre-computing how many drones can
realistically leave the start zone per turn**, based on the combined capacity of all
bridges directly out of `start_hub`:

```python
def calcul_flow(self) -> list:
    outflow = 0
    for nighbor, bridge in self.graph.get_nighbor(self.graph.start_hub):
        outflow += min(bridge.cp, nighbor.capacity)
    if outflow == 0:
        raise ValueError("no valid exit from start zone")
    start_flow = []
    curr_turn = 0
    c = 0
    for i in range(len(self.graph.drones)):
        start_flow.append(curr_turn)
        c += 1
        if c == outflow:
            c = 0
            curr_turn += 1
    return start_flow
```

For each neighbor of `start_hub`, the usable outflow through that exit is
`min(bridge_capacity, neighbor_zone_capacity)` — you cannot send more drones through a
bridge than either the bridge or the destination zone can absorb. Summed across all
exits, this gives a total per-turn outflow number. Drones are then assigned start
turns in batches of that size: the first `outflow` drones get `start_turn = 0`, the
next `outflow` get `start_turn = 1`, and so on.

**Why this helps:** it gives every drone a *reasonable* starting point for its
individual A* search, so the search rarely needs to "discover" through trial and
error that turn 0 is oversubscribed — it starts already spaced out, and A*'s own
wait-in-place transitions handle any remaining fine-grained congestion.

## 7. Retry Logic (`Scheduler.schudle`)

```python
def schudle(self) -> list[Drone]:
    start_flow = self.calcul_flow()
    for i, drone in enumerate(self.graph.drones):
        path = self.a_star(drone, start_flow[i])
        retry = 0
        start_turn = start_flow[i]
        while path is None and retry < self.maz_retry:
            start_turn += 1
            path = self.a_star(drone, start_turn)
            retry += 1
        if path is None:
            raise Exception(f"Drone {drone.drone_id} could not find path")
        drone.path_schdl = path
        self.reservation.use_path(path, self.graph)
    return self.graph.drones
```

`calcul_flow` is a heuristic, not a guarantee — on more constrained maps (capacity
bottlenecks deep in the graph, not just at the exit), a drone's A* search can still
legitimately fail to find a path from its assigned start turn (every reachable
`(zone, turn)` state is already reserved). When that happens, the scheduler simply
retries with `start_turn + 1`, up to 10 times, before giving up and raising an
exception. This is a pragmatic fallback: rather than implementing full backtracking
across already-scheduled drones (which would be significantly more complex), the
algorithm trusts that nudging the start turn forward by a turn or two is enough to find
a free slot, which holds true in practice across all provided test maps (see
benchmarks in the README).

## 8. From Schedule to Output (`Simulator`)

Once every drone has a committed `path_schdl` (a list of `(Zone, turn)` waypoints), the
`Simulator` converts this into the turn-by-turn textual format the subject requires.

It builds two turn-indexed maps in one pass over every drone's path:

- `start_events[turn]`: every move that *begins* on that turn — `(drone, from_zone,
  to_zone, duration)`.
- `arrival_events[turn]`: every mandatory restricted-zone arrival that must be printed
  on that exact turn (duration-2 moves only).

Then it iterates `turn = 1 .. max_turn` in order, emitting one line per turn that
contains, in order: any arrivals due this turn (`D<id>-<zone>`), followed by any new
moves starting this turn — printed either as `D<id>-<zone>` (1-turn move, drone
arrives immediately) or `D<id>-<connection>` (2-turn move into a restricted zone,
where `<connection>` is `<from_zone>-<to_zone>`, unambiguous since zone names cannot
contain dashes). Turns with no events at all are skipped, exactly as the subject's own
example output does. Once a drone's destination `is_end`, its state flips to
`delivered` and it stops being tracked.

This turn-indexed approach (rather than driving the loop off "does anything happen
next" as an earlier version of this code did) guarantees that a 2-turn restricted-zone
arrival is printed on the *exact* turn it occurs, even if no other drone has any
event on the turn in between.

## 9. Why This Design Satisfies the Subject's Requirements

- **No graph libraries used** — `Graph`, `Zone`, `Bridge` are all hand-rolled, and
  Dijkstra/A* are implemented from scratch with `heapq`.
- **Fully typesafe** — every public method has type hints; the project passes mypy
  with `--disallow-untyped-defs --check-untyped-defs`.
- **Fully object-oriented** — each pipeline stage is its own class with a single
  responsibility; there are no free-floating procedural scripts beyond the thin
  `pedri.py` entry point that wires the classes together.
- **Handles distribution across multiple paths** — the flow-aware start-turn staggering
  combined with per-drone independent A* naturally spreads drones across all
  available disjoint or overlapping routes, since the reservation table makes
  congested routes progressively less attractive (their early time-slots fill up) as
  more drones are scheduled.
- **Handles strategic waiting** — the explicit "wait in place" transition in the A*
  loop.
- **Avoids conflicts and deadlocks** — by construction, via the reservation table; no
  two drones can ever be assigned the same `(zone, turn)` beyond capacity, or the same
  `(bridge, turn)` beyond its `max_link_capacity`.
- **Accounts for zone-type movement costs** — `Zone.cost` (1 or 2) directly drives the
  A* edge weights and the multi-turn restricted-zone handling.

## 10. Complexity Summary

| Stage | Complexity | Runs |
|---|---|---|
| Graph construction | O(V + E) | once |
| Dijkstra heuristic | O((V + E) log V) | once |
| Flow calculation | O(degree(start)) | once |
| A* per drone | O(V × max_wait × E) worst case | once per drone |
| Reservation check/commit | O(1) per state | per A* expansion |
| Output formatting | O(total path length across all drones) | once |

Overall: **O((V + E) log V + N × V × max_wait × E)** where `N` is the number of
drones. In practice, the A* search terminates far earlier than its worst-case bound
because the heuristic and the staggered start turns keep the search focused, which is
reflected in the turn counts achieved on the benchmark maps (see the project README).

## Resources Used for This Approach

- Hart, Nilsson, Raphael (1968), *A Formal Basis for the Heuristic Determination of
  Minimum Cost Paths* — the original A* paper.
- Silver, D. (2005), *Cooperative Pathfinding* — introduces space-time A* with
  reservation tables for multi-agent pathfinding, which is the direct basis for
  `Scheduler.a_star` and `ReservationPath`.
- Stern et al. (2019), *Multi-Agent Pathfinding: Definitions, Variants, and
  Benchmarks* — survey covering the decoupled-vs-coupled MAPF tradeoff referenced in
  section 5.3.
- Python `heapq` documentation — used for both Dijkstra's and A*'s priority que
