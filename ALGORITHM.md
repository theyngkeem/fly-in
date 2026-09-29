# Fly-in: how the project works

Read this with the code open. The names in the project are sometimes spelled unusually (`schedular.py`, `schudle`, `stiemal_zaman`, `vsualization`), so this guide uses the names that actually exist. The current subject is version 2.0. The goal is to deliver every drone from the start zone to the end zone in as few turns as possible while respecting zone capacity, connection capacity, and movement costs.

## 1. Follow one run from start to finish

The entry point is `pedri.py`:

```text
map file
  -> MapParser.parse_map()          validate text, build raw dictionaries
  -> Graph(...)                     create Zone, Bridge, Drone objects and distances
  -> Scheduler(...)                 plan a timed path for every drone
  -> Simulator.goo_goo_dolls()      print the turn-by-turn movements
  -> Visualizer.goo_goo()           replay the same paths in Pygame
```

`pedri.py` checks that Pygame is installed, reads the map path from the command line, and catches errors around the run. The simulator prints first; the window opens afterward. The visualizer does not choose routes. It only reads the schedule that already exists.

The Python modules are grouped by responsibility:

| File | Main responsibility |
|---|---|
| `map_parsing.py` | Validate the input and store zone/connection definitions. |
| `elemnts/zone.py` | Represent zones, zone types, and bidirectional bridges. |
| `elemnts/drone.py` | Represent each drone and its state/path. |
| `elemnts/graph.py` | Build objects, adjacency lists, and the goal-distance heuristic. |
| `elemnts/schedular.py` | Plan paths and reserve zone/connection capacity. |
| `elemnts/simulator.py` | Turn paths into the required terminal output. |
| `vsualization/visualizer.py` | Draw and replay the graph in Pygame. |
| `pedri.py` | Connect all of the above. |

## 2. Rules and the meaning of a turn

A normal or priority zone costs one turn to enter. Entering a restricted zone costs two turns. A blocked zone cannot be entered. `max_drones` limits how many drones can occupy a normal zone at one time; its default is 1. The start and end zones have no effective occupancy limit. `max_link_capacity` limits departures across a connection in one turn; its default is 1. Connections are bidirectional, so both directions share the same capacity.

In a scheduled path, `(zone, 0)` means the drone is at that zone before the first printed turn. A move from `(A, 0)` to `(B, 1)` appears on output line 1. A restricted move from `(A, 0)` to `(B, 2)` prints `D<ID>-A-B` on line 1 and `D<ID>-B` on line 2. The drone cannot wait halfway through that move. A second drone may start crossing the same capacity-1 connection on line 2, when the first drone arrives and frees it. This same-turn reuse is required by the revised subject.

Moves are simultaneous. A drone leaving a zone frees its space for another drone arriving on that turn. The scheduler enforces this by checking destination occupancy at the **arrival** time and bridge capacity at the **departure** time. A path entry with the same zone at consecutive turns means the drone waited there.

## 3. Parsing a map: `MapParser`

`MapParser.parse_map()` reads the file with a context manager, so the file closes even if parsing fails. It tracks the physical line number for errors. Blank lines and comments beginning with `#` are ignored. The first non-comment declaration must be `nb_drones: <positive integer>`.

Each later line goes through `parse_line()`. It checks the prefix (`start_hub`, `end_hub`, `hub`, or `connection`) and dispatches to the relevant validation. For a zone, it requires a unique name with no dash, integer `x` and `y`, and at most one start and one end declaration. At the end it checks that both are present. For a connection, `parse_connection()` requires two **previously defined** zone names. It sorts the names to recognize `a-b` and `b-a` as duplicates.

`parse_opsett()` handles bracketed metadata such as `[zone=restricted color=red max_drones=2]`. Keys may appear in any order. It rejects unknown or repeated keys, invalid zone types, invalid/nonpositive numeric capacities, and empty values such as `color=`. On start and end hubs, `max_drones` is ignored even if its value is invalid, as the subject specifies. The parser stores dictionaries rather than `Zone` objects; `Graph` builds the objects in the next stage.

A disconnected graph is different from a malformed file. The parser can accept its syntax; the scheduler later detects that the start is unreachable and raises a clear error.

Questions to practise: Why must a connection refer to already defined zones? Why sort the connection names? What is the difference between `ParseError` and a scheduling failure?

## 4. Graph and model objects

`Graph.__init__()` turns the parser's dictionaries into objects. `creat_zone()` makes a `Zone` for each definition and remembers the start and end objects. `creat_conn()` makes `Bridge` objects. `creat_drone()` creates drones numbered from 1 to `nb_drones`. `creat_map()` builds an adjacency dictionary: zone name -> list of bridges touching it.

A `Zone` has coordinates, color, `zone_type`, capacity, and flags for start/end. `Zone.cost` is 2 only for restricted zones; it is 1 otherwise. `Zone.accecible` is false for blocked zones. `Bridge.next_zone(zone)` returns its other endpoint. `Bridge.dup_check()` returns its endpoint names in sorted order, which gives either travel direction the same reservation key.

`Graph.get_nighbor(zone)` looks at the adjacency list and returns `(neighbor, bridge)` pairs, excluding blocked destination zones. That makes one expansion proportional to the current zone's degree rather than scanning every connection. The start/end occupancy exception is implemented in `ReservationPath.can_enter()`, not by relying on the large placeholder capacity stored on those `Zone` objects.

The project's main objects each have a job; `pedri.py` is a small script that wires them together. No graph library is used: adjacency, Dijkstra, and A* are implemented in this repository.

## 5. The goal heuristic: reverse Dijkstra

`Graph.djikstra()` runs once before scheduling any drone. It starts at the end zone and works backward through the adjacency lists, storing a value in `Graph.best_op` for each reachable zone. A priority queue from Python's `heapq` selects the next cheapest entry. If a better value is found for a zone, it is pushed again; an old, more expensive queue entry is ignored when popped.

The important detail is the reverse relaxation in the actual code:

```python
if nighbor.zone_type == ZoneType.priority:
    ncost = cost
else:
    ncost = cost + zone.cost
```

Here `zone` is the current point of the **reverse** search, and `nighbor` is the candidate predecessor. In a forward move from `nighbor` to `zone`, the real cost is `zone.cost`. This calculation sometimes discounts that cost to zero when the predecessor is a priority zone. Therefore `best_op` is a **lower bound**, not the actual remaining travel time. Discounting can make priority routes more attractive in A*'s queue ordering, but priority zones still take one real turn to enter. Do not describe the heuristic as charging 8000, as a true shortest-path table, or as a guarantee that every drone will take a priority route.

If the start zone is missing from `best_op`, there is no usable path to the end. `Scheduler.__init__()` reports this instead of searching forever. The Dijkstra pass costs about `O((V + E) log V)` time and `O(V + E)` graph storage, where `V` is the number of zones and `E` is the number of connections.

Question to practise: Why is Dijkstra run once from the end rather than once for every drone? What happens if the heuristic underestimates travel time?

## 6. Planning drones one at a time

`Scheduler.schudle()` processes drones in ID order. For each drone, it calls `a_star()`, saves the resulting `path_schdl`, then calls `ReservationPath.use_path()` to commit its capacity usage. Later drones must plan around earlier drones. This is prioritized planning: it finds good schedules on the supplied maps but does **not** prove a globally minimum final turn count for every possible map.

### Initial start times

`calcul_flow()` estimates how many drones can leave the start in one turn:

```text
outflow = sum(min(connection capacity, neighbor zone capacity)
              for each usable neighbor of start)
```

It assigns that many drones the same initial search time, then assigns the next batch one turn later. This is an estimate, not a fixed departure order: A* may add waits at the start. If a search finds no path, `schudle()` retries with a later initial time, at most 10 times. If all attempts fail, it raises an error. Since earlier paths are never rearranged, this method can miss a schedule that a joint planner would find.

### Space-time A*

A search state is `(zone, turn)`, not just a zone. The same zone can be usable at one turn and full at another. A move to `next_zone` creates `(next_zone, turn + next_zone.cost)`; a wait creates `(zone, turn + 1)`. The search does not move into the start again. Entering a restricted zone jumps exactly two turns, so it cannot pause on the connection.

The queue orders states with `f = g + best_op[zone]`. `g` is elapsed turn cost since this drone's chosen start time. The search keeps `from_zone` to reconstruct the winning path, `g_arch` for the best score seen at each state, and `visited` for processed states. It discards stale queue entries whose score was later improved.

The current score is a pair `(elapsed_turns, start_waits)`. When two routes reach the same `(zone, turn)` at the same elapsed cost, the route with fewer waits at the start wins. `start_waits` increases only for a wait while `zone.is_srt` is true. This tie-break helped the supplied priority puzzle use both branches: the current schedule takes 6 turns instead of 7. It is a secondary preference, not a change to movement duration or the subject's priority-zone rule.

Before allowing a move, A* checks three things: arrival is within the search horizon, the destination has room at arrival, and the bridge has capacity at departure. Waiting checks occupancy of the current zone on the next turn. The horizon is `max(start_turn, last_delivery) + 2 * V`; it grows with earlier scheduled deliveries and the graph size, rather than being a fixed 100-turn limit.

### Reservation tables

`ReservationPath` has two counting tables:

```text
zone_reservation[zone_name][turn]       -> number of planned occupants
bridge_reservation[sorted_names][turn]  -> number of planned crossings
```

`can_enter()` compares the first count with `zone.capacity`, except that start and end always pass. `can_use_bridge()` compares the second count with `bridge.cp`. `use_path()` reserves each `(zone, turn)` entry and one bridge slot for each actual move; waits do not use a bridge. For a restricted move, the slot is keyed by its departure turn. Under the revised subject, that connection is free again on the following turn when the drone arrives. The destination zone is reserved at that arrival turn. Both travel directions count against the same bridge key.

The reservation table lets later drones use a zone on the same turn an earlier drone leaves it: the earlier path reserves its old zone at its old time and its next zone at arrival, not its old zone at arrival. Check this with a single-file chain of drones during evaluation.

## 7. A worked two-drone example

Take a capacity-1 connection `start-slow`, where `slow` is restricted, followed by `slow-end`. One valid schedule is:

```text
D1: start@0 -> slow@2 -> end@3
D2: start@1 -> slow@3 -> end@4
```

The terminal output is:

```text
D1-start-slow
D1-slow D2-start-slow
D2-slow D1-end
D2-end
```

On line 2, D1 arrives at `slow` and D2 begins crossing `start-slow`. That is legal because D1 releases the connection on its arrival turn. On line 3, D1 leaves `slow` while D2 arrives there; the vacated zone is available in the same turn. This example demonstrates both the connection and zone reuse rules.

## 8. Turning the schedule into terminal output

`Simulator.turn_event()` scans every drone's `path_schdl`. For each pair of different zones, it records `(drone, from_zone, to_zone, duration)` under the **departure** turn. Waits are omitted.

`goo_goo_dolls()` advances its turn counter, prints any restricted-zone arrivals that were pending from the previous turn, and then prints new departures. A one-turn move prints `D<ID>-<destination>`. A two-turn move prints `D<ID>-<from>-<to>` first and queues `D<ID>-<to>` for the next line. In this map syntax, `<from>-<to>` identifies the connection because zone names cannot contain dashes. Drones that wait do not get a movement token. End arrivals set `DroneState.delivered`, and the loop ends when all drones are delivered.

The simulator uses `DroneState` for its stopping condition, while the scheduler's timed paths are the source of movement events. This distinction matters when explaining why the replay can restart even after the terminal simulation has marked every drone delivered.

## 9. Visual replay

`Visualizer` opens after terminal output finishes. `cal_offset()` computes a scale and screen offsets from the zone coordinates so the graph fits the window. `draw_connections()`, `draw_zones()`, and `draw_drones()` draw the map and scheduled drone positions. Map color values go through Pygame's color parser; unknown names fall back to gray. The top text shows the turn and delivered count. The bottom text shows controls.

`build_events()` splits each scheduled move into one animation segment per turn. For a two-turn restricted move, the first press of Space animates from origin to halfway along the edge, and the second press animates from halfway to destination. `position_at()` finds where a drone should be when no animation is active. Delivered drones are omitted. If several drones share a screen position, `draw_drones()` shows a count instead of overlapping all their labels. `R` resets the replay and refits the map; Space advances one turn; arrows pan; `+`/`-` zoom; Escape closes the window.

The display is for understanding and replay. It does not validate the schedule or change it. You can explain it as a way to see bottlenecks, waits, and restricted crossings after the terminal output.

## 10. Complexity and limits to explain honestly

Let `T` be the maximum turn explored for one drone. There are at most about `V * T` space-time states; each expansion examines the current zone's neighbors and uses a heap. A useful upper bound for one search is `O(T * (V + E) * log(T * V))` time and `O(T * V)` search memory, plus the reservation tables. Planning all `N` drones multiplies the search work by `N`; retries can multiply it further. These are bounds for this implementation, not a promise of constant performance on arbitrary huge maps.

The reservations need space proportional to committed zone visits and bridge uses across all drone paths. The parser and graph take roughly `O(V + E)` space. Output formatting is proportional to the scheduled movement events and turns printed.

Know these limitations before evaluation:

- Paths are committed in drone order. The planner does not backtrack over earlier drones, so global optimality is not guaranteed.
- The start-flow estimate and 10 retries are heuristics. A different valid map can expose a case they do not solve well.
- The priority discount changes search order; it does not make priority movement free.
- Pygame is required by `pedri.py` before the terminal run begins. Install dependencies before demonstrating the program.
- `ALGORITHM.md` explains the implementation; `README.md` is the required public project overview. Keep both consistent if code changes.

On the supplied version-2 maps, the current implementation reaches the listed optima: easy maps 4/4/4 turns, medium maps 8/10/6, hard maps 13/16/26, and the optional challenger 43. These are results on those specific maps, not a proof about unseen evaluation maps.

## 11. Questions to practise before the evaluation

Try answering these aloud without reading this guide:

1. Walk from one input line through `MapParser`, `Graph`, `Scheduler`, and `Simulator`. Which class owns each piece of data?
2. Show exactly why `a-b` and `b-a` refer to the same capacity-limited connection.
3. Explain the difference between a zone reservation at arrival and a bridge reservation at departure.
4. Draw a two-turn restricted move and show when the next drone may enter its connection.
5. Why does A* need `(zone, turn)` states? What does a wait edge represent?
6. What does `best_op` estimate? Why does a priority-zone discount not shorten an actual move?
7. Why can two drones arrive at the end together while a normal zone might reject the second one?
8. Explain the priority-puzzle tie-break and why it can help throughput without guaranteeing global optimality.
9. What happens for invalid metadata, a duplicate connection, or a disconnected graph?
10. Where would you change the behavior if the evaluator asked for a new zone type, a different display color, or a different turn-output token?

## 12. Before committing and pushing

This is a preparation checklist, not something to run blindly as one script. Run commands from the repository root. Do not delete the source packages to satisfy the subject's phrase about placing files at the repository root: the existing `elemnts/` and `vsualization/` directories are Python packages that the program imports.

1. **Check what is actually in your repository.** Run `git status --short` and `git ls-files`. Review each staged or unstaged change with `git diff` and `git diff --cached`. Keep `README.md`, `ALGORITHM.md`, `Makefile`, `requirements.txt`, `mapfile.txt`, `pedri.py`, `map_parsing.py`, `.gitignore`, and both source package directories. Remove only files you know are generated or unrelated to the submission.
2. **Clean generated Python files.** `make clean` removes `__pycache__/`, `.mypy_cache/`, and `.pyc` files. `.gitignore` also ignores these, `.venv/`, and `*.egg-info/`. A virtual environment and downloaded `maps.tar.gz` do not need to be committed. If a generated file was previously tracked, inspect it with `git ls-files` and remove it from the Git index with `git rm --cached <path>`; do not remove source files by guesswork. Do not run `git reset` or a broad delete command just to make `git status` look clean.
3. **Install and test in the environment you will demonstrate.** Use `python3 -m venv .venv`, `source .venv/bin/activate`, and `make install` if dependencies are not installed. Run `make lint`, then `make run` to check terminal output and the Pygame window. Close the window with Escape. Test the supplied maps and at least one invalid map, one disconnected map, and one two-turn restricted crossing. The subject can use unseen maps.
4. **Confirm the documentation matches the final code.** Check that `README.md` has the required first line, installation/run instructions, an input/output example, algorithm and visualization descriptions, resources, and your accurate AI-use section. Review the complexity and limitation statements in this file. Do not claim an optimum on a map you have not tested.
5. **Stage the intended files and inspect the result.** For example: `git add .gitignore Makefile README.md ALGORITHM.md requirements.txt mapfile.txt pedri.py map_parsing.py elemnts vsualization`. Then run `git diff --cached --stat` and `git diff --cached --check`. If an unrelated file appears, unstage that file with `git restore --staged <path>` and inspect it; keep your source files.
6. **Commit and push to the correct repository.** Check `git remote -v` and `git branch --show-current`. Commit with `git commit -m "Explain and finish Fly-in project"`. If this branch already tracks a remote branch, use `git push`; otherwise use `git push -u origin <branch-name>` with the branch name you just checked. Finally run `git status --short` and check the remote repository to confirm the commit and required files are present.
