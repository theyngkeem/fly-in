# Drone Graph Visualization with Pygame (Step-by-Step)

This guide takes you from zero to a working turn-based visualization.

It is designed for your setup:
- You already have simulation logic (graph, A*, reservations, turn output).
- You want manual turn stepping first (SPACE = next turn).
- You want clear structure and minimal pygame code.

---

## Step 1) Create a minimal project structure

Start with this:

```text
project_root/
  main.py
  model.py
  data_adapter.py
  renderer.py
  input_controller.py
  assets/
    background.png      (optional)
    drone.png           (optional)
  gpygame.md
```

What each file does:
- `model.py`: dataclasses for zones, edges, drones, and simulation frame data.
- `data_adapter.py`: converts your simulation output into renderable turn states.
- `renderer.py`: all drawing logic (background, graph, zones, drones, HUD).
- `input_controller.py`: key handling (SPACE, optional BACKSPACE).
- `main.py`: game loop and turn progression.

Keep each file small and single-purpose.

---

## Step 2) Install and verify pygame

```bash
pip install pygame
```

Create this test in `main.py` first:

```python
import pygame

pygame.init()
screen = pygame.display.set_mode((1100, 700))
pygame.display.set_caption("Drone Graph Visualizer")
clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((20, 22, 28))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
```

If this window appears and closes correctly, continue.

---

## Step 3) Define render-friendly data models

In `model.py`:

```python
from dataclasses import dataclass

@dataclass
class Zone:
    name: str
    x: int
    y: int
    zone_type: str = "normal"         # normal, restricted, priority, ...
    color: str | tuple | None = None   # "red", "#ffcc00", (255,0,0), or None

@dataclass
class Edge:
    a: str   # zone name
    b: str   # zone name

@dataclass
class DronePath:
    drone_id: str
    # list of (zone_name, turn)
    scheduled: list[tuple[str, int]]
```

Why this matters:
- Keeps your renderer decoupled from simulation internals.
- Makes debugging easier because data is explicit.

---

## Step 4) Convert simulation output into turn states

You want an index like this:

```python
turn_index[turn][drone_id] = zone_name
```

In `data_adapter.py`:

```python
from model import DronePath


def build_turn_index(drone_paths: list[DronePath]) -> dict[int, dict[str, str]]:
    """
    Convert per-drone scheduled path into a per-turn lookup.
    Example output:
      {
        0: {"D1": "A", "D2": "B"},
        1: {"D1": "B", "D2": "B"},
      }
    """
    turn_index: dict[int, dict[str, str]] = {}

    for path in drone_paths:
        for zone_name, turn in path.scheduled:
            turn_index.setdefault(turn, {})
            turn_index[turn][path.drone_id] = zone_name

    return turn_index
```

If your simulator outputs move events instead of `(zone, turn)`, preprocess once into this same structure.

---

## Step 5) Add safe color parsing (invalid color fallback)

Constraint: invalid or missing zone color must use default.

In `renderer.py`:

```python
import pygame

DEFAULT_ZONE_COLOR = (120, 170, 220)


def safe_color(value, default=DEFAULT_ZONE_COLOR):
    if value is None:
        return default

    # Accept pygame color strings, e.g., "red", "#ffcc00"
    try:
        return pygame.Color(value)
    except Exception:
        pass

    # Accept RGB tuples
    if isinstance(value, tuple) and len(value) == 3:
        if all(isinstance(c, int) and 0 <= c <= 255 for c in value):
            return value

    return default
```

---

## Step 6) Build a Renderer class

In `renderer.py`:

```python
import math
import pygame
from model import Zone, Edge

DEFAULT_BG = (18, 21, 27)
DEFAULT_ZONE_COLOR = (120, 170, 220)


def safe_color(value, default=DEFAULT_ZONE_COLOR):
    if value is None:
        return default
    try:
        return pygame.Color(value)
    except Exception:
        pass
    if isinstance(value, tuple) and len(value) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in value):
        return value
    return default


class Renderer:
    def __init__(self, screen: pygame.Surface, zones: list[Zone], edges: list[Edge]):
        self.screen = screen
        self.zones = zones
        self.edges = edges
        self.zones_by_name = {z.name: z for z in zones}
        self.font = pygame.font.SysFont(None, 20)

        self.background = None  # optional image
        self.drone_image = None # optional image

    def load_assets(self, background_path: str | None = None, drone_path: str | None = None):
        if background_path:
            try:
                bg = pygame.image.load(background_path).convert()
                self.background = pygame.transform.scale(bg, self.screen.get_size())
            except Exception:
                self.background = None

        if drone_path:
            try:
                # Use convert_alpha for PNG with transparency
                self.drone_image = pygame.image.load(drone_path).convert_alpha()
                self.drone_image = pygame.transform.smoothscale(self.drone_image, (18, 18))
            except Exception:
                self.drone_image = None

    def draw(self, current_turn: int, max_turn: int, turn_state: dict[str, str]):
        self._draw_background()
        self._draw_connections()
        self._draw_zones()
        self._draw_drones(turn_state)
        self._draw_hud(current_turn, max_turn)

    def _draw_background(self):
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(DEFAULT_BG)

    def _draw_connections(self):
        for edge in self.edges:
            a = self.zones_by_name.get(edge.a)
            b = self.zones_by_name.get(edge.b)
            if not a or not b:
                continue
            pygame.draw.line(self.screen, (80, 90, 105), (a.x, a.y), (b.x, b.y), 2)

    def _draw_zones(self):
        for z in self.zones:
            fill = safe_color(z.color)
            border = (230, 230, 230)
            border_width = 2

            if z.zone_type == "restricted":
                border = (220, 70, 70)
                border_width = 3
            elif z.zone_type == "priority":
                border = (255, 215, 90)
                border_width = 3

            pygame.draw.circle(self.screen, fill, (z.x, z.y), 16)
            pygame.draw.circle(self.screen, border, (z.x, z.y), 16, border_width)

            label = self.font.render(z.name, True, (245, 245, 245))
            self.screen.blit(label, (z.x + 18, z.y - 10))

    def _draw_drones(self, turn_state: dict[str, str]):
        # Group drones by zone to handle overlap cleanly
        grouped: dict[str, list[str]] = {}
        for drone_id, zone_name in turn_state.items():
            grouped.setdefault(zone_name, []).append(drone_id)

        for zone_name, drone_ids in grouped.items():
            z = self.zones_by_name.get(zone_name)
            if not z:
                continue

            n = len(drone_ids)
            for i, drone_id in enumerate(drone_ids):
                if n == 1:
                    dx, dy = 0, 0
                else:
                    angle = (2 * math.pi * i) / n
                    spread = 11
                    dx = int(math.cos(angle) * spread)
                    dy = int(math.sin(angle) * spread)

                px, py = z.x + dx, z.y + dy

                if self.drone_image is not None:
                    rect = self.drone_image.get_rect(center=(px, py))
                    self.screen.blit(self.drone_image, rect)
                else:
                    pygame.draw.circle(self.screen, (80, 240, 170), (px, py), 7)

                txt = self.font.render(drone_id, True, (230, 255, 240))
                self.screen.blit(txt, (px + 9, py - 7))

    def _draw_hud(self, current_turn: int, max_turn: int):
        line = f"Turn: {current_turn}/{max_turn}   [SPACE: next] [BACKSPACE: prev] [ESC: quit]"
        hud = self.font.render(line, True, (245, 245, 245))
        self.screen.blit(hud, (12, 10))
```

---

## Step 7) Handle keyboard input for manual turns

In `input_controller.py`:

```python
import pygame


def handle_event(event, current_turn: int, max_turn: int):
    """
    Returns (running, current_turn).
    Manual stepping only: no auto animation.
    """
    running = True

    if event.type == pygame.QUIT:
        return False, current_turn

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return False, current_turn
        if event.key == pygame.K_SPACE:
            if current_turn < max_turn:
                current_turn += 1
        if event.key == pygame.K_BACKSPACE:
            if current_turn > 0:
                current_turn -= 1

    return running, current_turn
```

---

## Step 8) Integrate everything in main loop

Now wire your data + renderer + input in `main.py`:

```python
import pygame
from model import Zone, Edge, DronePath
from data_adapter import build_turn_index
from renderer import Renderer
from input_controller import handle_event


def sample_data():
    zones = [
        Zone("A", 150, 120, "normal", "#4b91ff"),
        Zone("B", 380, 140, "priority", "#2ecc71"),
        Zone("C", 620, 260, "restricted", "not-a-color"),  # invalid -> fallback
        Zone("D", 300, 380, "normal", None),                 # missing -> fallback
        Zone("E", 760, 140, "normal", (220, 170, 60)),
    ]

    edges = [
        Edge("A", "B"),
        Edge("B", "C"),
        Edge("A", "D"),
        Edge("D", "C"),
        Edge("C", "E"),
    ]

    drone_paths = [
        DronePath("D1", [("A", 0), ("B", 1), ("C", 2), ("E", 3)]),
        DronePath("D2", [("A", 0), ("D", 1), ("C", 2), ("E", 3)]),
        DronePath("D3", [("B", 0), ("B", 1), ("C", 2), ("C", 3)]),
    ]

    return zones, edges, drone_paths


def main():
    pygame.init()
    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Drone Zone Simulation")
    clock = pygame.time.Clock()

    zones, edges, drone_paths = sample_data()
    turn_index = build_turn_index(drone_paths)

    max_turn = max(turn_index.keys()) if turn_index else 0
    current_turn = 0

    renderer = Renderer(screen, zones, edges)
    renderer.load_assets(
        background_path="assets/background.png",  # optional
        drone_path="assets/drone.png",            # optional
    )

    running = True
    while running:
        for event in pygame.event.get():
            running, current_turn = handle_event(event, current_turn, max_turn)
            if not running:
                break

        turn_state = turn_index.get(current_turn, {})
        renderer.draw(current_turn, max_turn, turn_state)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
```

At this point you have:
- Graph drawn from `(x, y)`
- Zone colors with invalid fallback
- Drones rendered per turn
- Overlap handling for multiple drones in same zone
- SPACE for manual next-turn stepping

---

## Step 9) Connect your real simulator output

Replace `sample_data()` with your real source.

Expected conversion target:

```python
zones: list[Zone]
edges: list[Edge]
drone_paths: list[DronePath]
```

If your simulator already has these concepts under different names, write a small adapter function.

Example adapter skeleton:

```python
def from_simulation(sim_graph, sim_schedule):
    zones = []
    edges = []
    drone_paths = []

    # 1) zones
    # for each sim zone -> Zone(name, x, y, type, color)

    # 2) edges
    # for each graph link -> Edge(a_name, b_name)

    # 3) scheduled drone path
    # for each drone -> DronePath(drone_id, [(zone_name, turn), ...])

    return zones, edges, drone_paths
```

---

## Step 10) Debugging checklist (practical)

Use this sequence when visuals are wrong:

1. Window black / empty
- Confirm render loop is running.
- Confirm `renderer.draw(...)` is called every frame.
- Confirm `pygame.display.flip()` is called.

2. Zones missing
- Print number of zones and first 3 values.
- Verify zone `(x, y)` is within window bounds.

3. Drones not moving by turn
- Print `current_turn` when pressing SPACE.
- Print `turn_index.get(current_turn)` each step.
- Check if turn keys exist in `turn_index`.

4. Crash on color
- Ensure every zone color goes through `safe_color(...)`.

5. Drones overlap badly
- Increase `spread` in renderer.
- Reduce drone radius or icon size.

6. Asset image not loading
- Temporarily print inside `load_assets` except blocks.
- Test with no image fallback (circles).

7. Edges not drawn
- Validate each `Edge(a, b)` zone name exists in `zones_by_name`.

---

## Optional Improvements After Base Works

### A) Smooth movement between turns

Keep manual SPACE, but animate from old turn to new turn for a short duration.

Core idea:
- On SPACE: set `from_turn = current_turn`, `to_turn = current_turn + 1`, start timer.
- While animating: interpolate each drone position from zone A to zone B.

Interpolation formula:

- `x = x0 + alpha * (x1 - x0)`
- `y = y0 + alpha * (y1 - y0)`
- where `alpha` goes from 0 to 1 over ~250 ms.

### B) Stronger visuals by zone type

- `restricted`: red border + small "X" overlay.
- `priority`: gold pulsing outer ring.
- `normal`: simple white border.

### C) HUD improvements

Show:
- current turn
- total drones
- delivered count (if available from simulation)
- controls legend

### D) Play/Pause mode

Add key `P`:
- `playing = not playing`
- if `playing`, auto increment turn every fixed interval (for example 400 ms).
- keep SPACE manual stepping always available.

---

## Final Build Order (recommended)

Follow this exact order to avoid getting stuck:

1. Minimal pygame loop (`main.py` only).
2. Add zone drawing from hardcoded data.
3. Add edge drawing.
4. Add one drone fixed at one zone.
5. Add `turn_index` and SPACE stepping.
6. Add overlap handling.
7. Add color fallback.
8. Connect your real simulator adapter.
9. Add optional assets (background/drone icon).
10. Add optional smoothing and play/pause.

If each step runs before the next, integration will be smooth and easy to debug.
