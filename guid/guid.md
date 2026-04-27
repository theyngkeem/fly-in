# 🎮 Fly-in — Pygame Visualization Guide
## Complete Guide to Visualizing Drone Routing with Pygame

> From zero pygame knowledge to full animated simulation.
> Every concept explained before showing how to use it.

---

## Table of Contents

1. [What is Pygame and Why Use It](#1-what-is-pygame-and-why-use-it)
2. [Core Pygame Concepts](#2-core-pygame-concepts)
3. [The Coordinate System](#3-the-coordinate-system)
4. [Setting Up the Window](#4-setting-up-the-window)
5. [The Game Loop](#5-the-game-loop)
6. [Drawing Basics](#6-drawing-basics)
7. [Mapping Your Zones to Screen Coordinates](#7-mapping-your-zones-to-screen-coordinates)
8. [Drawing the Map](#8-drawing-the-map)
9. [Animating Drone Movement](#9-animating-drone-movement)
10. [Adding Text and Info Display](#10-adding-text-and-info-display)
11. [Handling User Input](#11-handling-user-input)
12. [Full Implementation Structure](#12-full-implementation-structure)
13. [Color Scheme](#13-color-scheme)
14. [Performance Tips](#14-performance-tips)

---

## 1. What is Pygame and Why Use It

### What is Pygame?

Pygame is a Python library that wraps SDL (Simple DirectMedia Layer), a low-level graphics library. It gives you:
- A window to draw in
- Functions to draw shapes (circles, rectangles, lines)
- Event handling (keyboard, mouse, window close)
- Frame timing (control animation speed)

### Why Use It for This Project?

**Debugging:** Watch drones move in real-time. Spot routing bugs immediately (drones colliding, wrong zones, stuck drones).

**Presentation:** Show your peer evaluators a visual simulation instead of text output. Much more impressive.

**Understanding:** See bottlenecks visually. Watch how drones queue at gates, take different paths, etc.

### Installation

```bash
pip install pygame
```

That's it. No other dependencies.

---

## 2. Core Pygame Concepts

### Surface

A **surface** is a 2D image in memory. Think of it as a canvas you can draw on.

**The main surface** is your window — created with `pygame.display.set_mode()`.

Every frame, you:
1. Clear the surface (fill with background color)
2. Draw everything on it
3. Flip to show it on screen

### Pixel Coordinates

Everything in pygame is positioned by pixel coordinates `(x, y)`.

`(0, 0)` is the **top-left corner** of the window.
`x` increases to the right.
`y` increases **downward** (opposite of math class).

```
(0,0) ────────────► x
  │
  │
  │
  ▼
  y

(800, 600) is bottom-right of an 800×600 window
```

### The Clock

`pygame.time.Clock()` controls frame rate. Call `clock.tick(60)` at the end of each frame to:
- Limit to 60 frames per second
- Return milliseconds since last frame (for smooth animation)

### Events

Events are things that happen: key press, mouse click, window close, etc.

`pygame.event.get()` returns a list of events that occurred since last frame. You loop through them and respond.

```python
for event in pygame.event.get():
    if event.type == pygame.QUIT:  # User clicked X button
        running = False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            paused = not paused
```

---

## 3. The Coordinate System

### Your Map Coordinates vs Screen Coordinates

Your map file has zones at coordinates like:
```
start: (0, 0)
gate1: (1, 0)
gate2: (1, 1)
roof: (2, 1)
```

These are **logical coordinates** in your simulation space.

Pygame needs **pixel coordinates** on screen:
```
(100, 300)  ← pixels from top-left
```

### The Transformation

You need to convert from `(map_x, map_y)` to `(screen_x, screen_y)`.

**Key decisions:**
1. **Scale:** How many pixels per map unit?
2. **Offset:** Where is `(0, 0)` on screen?
3. **Y-flip:** Your map might use math coordinates (Y up), but pygame uses Y down

**Example transformation:**

```
SCALE = 80  # Each map unit = 80 pixels
OFFSET_X = 100  # Leave margin on left
OFFSET_Y = 500  # Start near bottom

screen_x = map_x * SCALE + OFFSET_X
screen_y = OFFSET_Y - (map_y * SCALE)  # Note the minus — flips Y
```

Why flip Y? If your map has positive Y going up (math style), but pygame has Y going down, you need to invert it.

### Example

Map coordinate `(2, 3)`:
```
screen_x = 2 * 80 + 100 = 260
screen_y = 500 - (3 * 80) = 260
```

So zone at `(2, 3)` draws at pixel `(260, 260)`.

---

## 4. Setting Up the Window

### Basic Setup

```python
import pygame
import sys

# Initialize pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
BACKGROUND_COLOR = (20, 20, 30)  # Dark blue-gray

# Create window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Fly-in Drone Simulator")

# Clock for frame rate
clock = pygame.time.Clock()
```

### What Each Line Does

**`pygame.init()`** — Initializes all pygame modules. Required before anything else.

**`set_mode((width, height))`** — Creates window and returns the surface to draw on.

**`set_caption(text)`** — Sets window title (appears in title bar).

**`clock = pygame.time.Clock()`** — Creates timing object for frame control.

---

## 5. The Game Loop

Every graphical program has a **main loop** that runs until the program quits.

### The Pattern

```python
running = True
while running:
    # 1. Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # 2. Update state
    # (move drones, advance turn, etc.)
    
    # 3. Draw everything
    screen.fill(BACKGROUND_COLOR)  # Clear screen
    # draw_map()
    # draw_drones()
    # draw_info()
    
    # 4. Display and wait
    pygame.display.flip()  # Show what we drew
    clock.tick(60)  # Wait to maintain 60 FPS

pygame.quit()
sys.exit()
```

### Why This Order?

**Events first:** If user clicks close, you want to catch it immediately.

**Update next:** Calculate new positions based on time elapsed.

**Draw last:** Once everything is updated, render the new frame.

**Flip at end:** The `flip()` call swaps the back buffer (what you drew) with the front buffer (what's shown). This prevents flickering.

---

## 6. Drawing Basics

Pygame has simple drawing functions in `pygame.draw`.

### Drawing a Circle

```python
pygame.draw.circle(surface, color, center, radius)
```

**surface:** Where to draw (usually `screen`)
**color:** RGB tuple like `(255, 0, 0)` for red
**center:** `(x, y)` tuple in pixel coordinates
**radius:** Integer pixel radius

**Example:**
```python
# Draw red circle at (400, 300) with radius 20
pygame.draw.circle(screen, (255, 0, 0), (400, 300), 20)
```

### Drawing a Rectangle

```python
pygame.draw.rect(surface, color, rect_object)
```

**rect_object:** `pygame.Rect(x, y, width, height)` where `(x, y)` is top-left corner

**Example:**
```python
# Draw blue 50×50 rectangle at (100, 100)
rect = pygame.Rect(100, 100, 50, 50)
pygame.draw.rect(screen, (0, 0, 255), rect)
```

### Drawing a Line

```python
pygame.draw.line(surface, color, start_pos, end_pos, width)
```

**Example:**
```python
# Draw white line from (100, 100) to (200, 200), 2 pixels thick
pygame.draw.line(screen, (255, 255, 255), (100, 100), (200, 200), 2)
```

### Drawing Text

Text is more complex because you need a font object first.

```python
# Create font
font = pygame.font.SysFont('Arial', 24)

# Render text to a surface
text_surface = font.render("Hello World", True, (255, 255, 255))

# Blit (copy) text surface to screen at position
screen.blit(text_surface, (100, 50))
```

**Why three steps?**
1. Font defines the typeface and size
2. Render creates an image of the text (expensive operation)
3. Blit draws that image onto screen (fast)

**Optimization tip:** Render text once and reuse if it doesn't change.

---

## 7. Mapping Your Zones to Screen Coordinates

### Find the Map Bounds

Before drawing, scan all zones to find min/max coordinates:

```python
def get_map_bounds(zones: dict[str, Zone]) -> tuple:
    """Returns (min_x, max_x, min_y, max_y)"""
    if not zones:
        return (0, 10, 0, 10)
    
    min_x = min(z.x for z in zones.values())
    max_x = max(z.x for z in zones.values())
    min_y = min(z.y for z in zones.values())
    max_y = max(z.y for z in zones.values())
    
    return (min_x, max_x, min_y, max_y)
```

### Calculate Scale and Offset

```python
def calculate_transform(zones: dict[str, Zone], 
                       window_width: int, 
                       window_height: int):
    """Calculate scale and offset to fit map in window"""
    min_x, max_x, min_y, max_y = get_map_bounds(zones)
    
    # Add margins
    MARGIN = 100  # pixels from edge
    
    # Available space
    available_width = window_width - 2 * MARGIN
    available_height = window_height - 2 * MARGIN
    
    # Map dimensions
    map_width = max_x - min_x
    map_height = max_y - min_y
    
    # Avoid division by zero
    if map_width == 0:
        map_width = 1
    if map_height == 0:
        map_height = 1
    
    # Scale to fit
    scale_x = available_width / map_width
    scale_y = available_height / map_height
    scale = min(scale_x, scale_y)  # Use smaller to fit both dimensions
    
    # Center the map
    offset_x = MARGIN + (available_width - map_width * scale) / 2
    offset_y = MARGIN + (available_height - map_height * scale) / 2
    
    return scale, offset_x, offset_y, min_x, min_y
```

### The Transform Function

```python
def map_to_screen(zone: Zone, scale, offset_x, offset_y, min_x, min_y) -> tuple:
    """Convert zone coordinates to screen pixels"""
    # Normalize to 0-based
    rel_x = zone.x - min_x
    rel_y = zone.y - min_y
    
    # Scale and offset
    screen_x = int(rel_x * scale + offset_x)
    screen_y = int(rel_y * scale + offset_y)
    
    # Note: We're NOT flipping Y here because we'll draw from top to bottom
    # If your map uses Y-up coordinates, add: screen_y = window_height - screen_y
    
    return (screen_x, screen_y)
```

---

## 8. Drawing the Map

### Drawing Order Matters

Draw in layers, back to front:
1. Connections (lines) — background
2. Zones (circles) — middle
3. Drones (moving circles) — foreground
4. Text (labels, info) — top

### Drawing Connections

```python
def draw_connections(screen, graph, transform_params):
    """Draw all connections as lines"""
    scale, offset_x, offset_y, min_x, min_y = transform_params
    
    for bridge in graph.connections:
        # Get screen positions of both zones
        pos1 = map_to_screen(bridge.first_zone, scale, offset_x, offset_y, min_x, min_y)
        pos2 = map_to_screen(bridge.second_zone, scale, offset_x, offset_y, min_x, min_y)
        
        # Choose color based on capacity
        if bridge.capacity == 1:
            color = (80, 80, 80)  # Gray for single capacity
        else:
            color = (100, 150, 100)  # Green-ish for higher capacity
        
        # Draw line
        pygame.draw.line(screen, color, pos1, pos2, 2)
```

### Drawing Zones

```python
def draw_zones(screen, zones, transform_params):
    """Draw all zones as circles"""
    scale, offset_x, offset_y, min_x, min_y = transform_params
    
    for zone in zones.values():
        pos = map_to_screen(zone, scale, offset_x, offset_y, min_x, min_y)
        
        # Choose color based on zone type
        color = get_zone_color(zone)
        
        # Zone radius proportional to capacity
        radius = 15 + zone.capacity * 2
        if zone.is_srt or zone.is_end:
            radius = 30  # Bigger for start/end
        
        # Draw zone
        pygame.draw.circle(screen, color, pos, radius)
        
        # Draw border
        border_color = (255, 255, 255) if zone.is_srt or zone.is_end else (200, 200, 200)
        pygame.draw.circle(screen, border_color, pos, radius, 2)  # 2px border
        
        # Draw zone name
        font = pygame.font.SysFont('Arial', 12)
        text = font.render(zone.name, True, (255, 255, 255))
        text_rect = text.get_rect(center=(pos[0], pos[1] - radius - 10))
        screen.blit(text, text_rect)
```

### Color Mapping Function

```python
def get_zone_color(zone):
    """Return RGB color for zone based on type"""
    if zone.is_srt:
        return (50, 200, 50)  # Green for start
    if zone.is_end:
        return (255, 215, 0)  # Gold for end
    
    # Type-based colors
    if zone.zone_type == ZoneType.blocked:
        return (50, 50, 50)  # Dark gray
    elif zone.zone_type == ZoneType.restricted:
        return (150, 50, 150)  # Purple
    elif zone.zone_type == ZoneType.priority:
        return (50, 150, 200)  # Cyan
    else:
        return (100, 100, 150)  # Blue-gray for normal
```

---

## 9. Animating Drone Movement

### The Challenge

Your scheduled path is:
```python
drone.path_schdl = [
    (zone_A, 0),
    (zone_B, 1),
    (zone_C, 3)  # Note: turn 2 was skipped (drone waited at B)
]
```

But you want smooth animation — the drone should appear to **move gradually** from A to B, not teleport.

### Solution: Interpolation

**Interpolation** means calculating positions between two points over time.

If drone is at position A `(x1, y1)` and moving to position B `(x2, y2)`, and it's 40% of the way there:

```python
current_x = x1 + (x2 - x1) * 0.4
current_y = y1 + (y2 - y1) * 0.4
```

### Frame-Based Animation

Track where each drone is in its journey:

```python
class DroneAnimationState:
    def __init__(self, drone):
        self.drone = drone
        self.path_index = 0  # Which segment of path we're on
        self.progress = 0.0  # 0.0 to 1.0 through current segment
        self.current_pos = None  # (x, y) screen position
```

### Update Animation Each Frame

```python
def update_drone_animation(drone_state, elapsed_ms, transform_params):
    """Move drone along its path"""
    path = drone_state.drone.path_schdl
    
    if drone_state.path_index >= len(path) - 1:
        return  # Drone reached end
    
    # Get current and next zone
    current_zone, current_turn = path[drone_state.path_index]
    next_zone, next_turn = path[drone_state.path_index + 1]
    
    # If same zone (waiting), don't animate
    if current_zone == next_zone:
        drone_state.path_index += 1
        return
    
    # Calculate positions
    pos1 = map_to_screen(current_zone, *transform_params)
    pos2 = map_to_screen(next_zone, *transform_params)
    
    # Animation speed
    TURNS_PER_SECOND = 1.0  # One turn = 1 second
    turn_duration_ms = 1000 / TURNS_PER_SECOND
    
    # Update progress
    drone_state.progress += elapsed_ms / turn_duration_ms
    
    if drone_state.progress >= 1.0:
        # Reached next zone
        drone_state.path_index += 1
        drone_state.progress = 0.0
        drone_state.current_pos = pos2
    else:
        # Interpolate position
        t = drone_state.progress
        x = pos1[0] + (pos2[0] - pos1[0]) * t
        y = pos1[1] + (pos2[1] - pos1[1]) * t
        drone_state.current_pos = (int(x), int(y))
```

### Drawing Animated Drones

```python
def draw_drones(screen, drone_states):
    """Draw all drones at their current positions"""
    for state in drone_states:
        if state.current_pos is None:
            continue
        
        # Draw drone as small circle
        color = (255, 50, 50)  # Red
        pygame.draw.circle(screen, color, state.current_pos, 8)
        
        # Draw drone ID
        font = pygame.font.SysFont('Arial', 10)
        text = font.render(str(state.drone.drone_id), True, (255, 255, 255))
        text_rect = text.get_rect(center=(state.current_pos[0], state.current_pos[1] - 15))
        screen.blit(text, text_rect)
```

---

## 10. Adding Text and Info Display

### HUD (Heads-Up Display)

Show current turn, delivered drones, etc. at top of screen.

```python
def draw_hud(screen, current_turn, total_drones, delivered_count):
    """Draw info overlay"""
    font = pygame.font.SysFont('Arial', 20)
    
    # Turn counter
    turn_text = font.render(f"Turn: {current_turn}", True, (255, 255, 255))
    screen.blit(turn_text, (10, 10))
    
    # Delivery counter
    delivery_text = font.render(
        f"Delivered: {delivered_count}/{total_drones}", 
        True, (255, 255, 255)
    )
    screen.blit(delivery_text, (10, 40))
    
    # Instructions
    font_small = pygame.font.SysFont('Arial', 14)
    instructions = font_small.render(
        "SPACE: Pause | Q: Quit | UP/DOWN: Speed", 
        True, (200, 200, 200)
    )
    screen.blit(instructions, (10, 70))
```

### Zone Info on Hover

When mouse hovers over a zone, show tooltip:

```python
def get_zone_at_position(zones, pos, transform_params, max_distance=30):
    """Find zone near mouse position"""
    for zone in zones.values():
        zone_pos = map_to_screen(zone, *transform_params)
        dx = pos[0] - zone_pos[0]
        dy = pos[1] - zone_pos[1]
        distance = (dx*dx + dy*dy) ** 0.5
        
        if distance < max_distance:
            return zone
    return None

def draw_tooltip(screen, zone, mouse_pos):
    """Draw info box for zone"""
    font = pygame.font.SysFont('Arial', 14)
    
    lines = [
        f"Zone: {zone.name}",
        f"Type: {zone.zone_type.value}",
        f"Capacity: {zone.capacity}",
        f"Cost: {zone.cost} turns"
    ]
    
    # Calculate box size
    line_height = 20
    box_width = 150
    box_height = len(lines) * line_height + 10
    
    # Draw background box
    box_rect = pygame.Rect(mouse_pos[0] + 10, mouse_pos[1], box_width, box_height)
    pygame.draw.rect(screen, (40, 40, 40), box_rect)
    pygame.draw.rect(screen, (200, 200, 200), box_rect, 1)
    
    # Draw text lines
    y = mouse_pos[1] + 5
    for line in lines:
        text = font.render(line, True, (255, 255, 255))
        screen.blit(text, (mouse_pos[0] + 15, y))
        y += line_height
```

---

## 11. Handling User Input

### Keyboard Controls

```python
# In main loop
for event in pygame.event.get():
    if event.type == pygame.QUIT:
        running = False
    
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            paused = not paused
        
        elif event.key == pygame.K_q:
            running = False
        
        elif event.key == pygame.K_UP:
            animation_speed = min(animation_speed * 1.5, 10.0)
        
        elif event.key == pygame.K_DOWN:
            animation_speed = max(animation_speed / 1.5, 0.1)
```

### Mouse Hover

```python
# In main loop, after drawing everything
mouse_pos = pygame.mouse.get_pos()
hovered_zone = get_zone_at_position(zones, mouse_pos, transform_params)

if hovered_zone:
    draw_tooltip(screen, hovered_zone, mouse_pos)
```

---

## 12. Full Implementation Structure

### File: `visual/gui.py`

```python
import pygame
import sys
from models.graph import Graph
from models.zone import ZoneType
from engine.scheduler import Scheduler


class DroneAnimationState:
    """Tracks animation state for one drone"""
    def __init__(self, drone, transform_params):
        self.drone = drone
        self.path_index = 0
        self.progress = 0.0
        self.current_pos = self.get_initial_position(transform_params)
    
    def get_initial_position(self, transform_params):
        """Get starting screen position"""
        if self.drone.path_schdl:
            zone, _ = self.drone.path_schdl[0]
            return map_to_screen(zone, *transform_params)
        return (0, 0)


class PyGameVisualizer:
    """Main visualizer class"""
    
    def __init__(self, scheduler: Scheduler):
        pygame.init()
        
        self.scheduler = scheduler
        self.graph = scheduler.graph
        
        # Window setup
        self.WINDOW_WIDTH = 1400
        self.WINDOW_HEIGHT = 800
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("Fly-in Drone Routing Simulator")
        
        # Colors
        self.BG_COLOR = (20, 20, 30)
        
        # Transform parameters
        self.transform_params = self.calculate_transform()
        
        # Animation state
        self.drone_states = [
            DroneAnimationState(drone, self.transform_params) 
            for drone in self.graph.drones
        ]
        
        # Timing
        self.clock = pygame.time.Clock()
        self.animation_speed = 1.0
        self.paused = False
        
        # State
        self.current_turn = 0
        self.delivered_count = 0
    
    def calculate_transform(self):
        """Calculate scale and offset to fit map"""
        zones = self.graph.zones
        
        # Find bounds
        min_x = min(z.x for z in zones.values())
        max_x = max(z.x for z in zones.values())
        min_y = min(z.y for z in zones.values())
        max_y = max(z.y for z in zones.values())
        
        MARGIN = 100
        available_w = self.WINDOW_WIDTH - 2 * MARGIN
        available_h = self.WINDOW_HEIGHT - 2 * MARGIN - 100  # Extra for HUD
        
        map_w = max_x - min_x if max_x != min_x else 1
        map_h = max_y - min_y if max_y != min_y else 1
        
        scale = min(available_w / map_w, available_h / map_h)
        
        offset_x = MARGIN + (available_w - map_w * scale) / 2
        offset_y = MARGIN + 100 + (available_h - map_h * scale) / 2
        
        return (scale, offset_x, offset_y, min_x, min_y)
    
    def map_to_screen(self, zone):
        """Convert zone to screen coordinates"""
        scale, offset_x, offset_y, min_x, min_y = self.transform_params
        
        rel_x = zone.x - min_x
        rel_y = zone.y - min_y
        
        screen_x = int(rel_x * scale + offset_x)
        screen_y = int(rel_y * scale + offset_y)
        
        return (screen_x, screen_y)
    
    def get_zone_color(self, zone):
        """Return color for zone"""
        if zone.is_srt:
            return (50, 200, 50)
        if zone.is_end:
            return (255, 215, 0)
        
        if zone.zone_type == ZoneType.blocked:
            return (50, 50, 50)
        elif zone.zone_type == ZoneType.restricted:
            return (150, 50, 150)
        elif zone.zone_type == ZoneType.priority:
            return (50, 150, 200)
        else:
            return (100, 100, 150)
    
    def draw_connections(self):
        """Draw all connections"""
        for bridge in self.graph.connections:
            pos1 = self.map_to_screen(bridge.first_zone)
            pos2 = self.map_to_screen(bridge.second_zone)
            
            color = (80, 80, 80) if bridge.capacity == 1 else (100, 150, 100)
            pygame.draw.line(self.screen, color, pos1, pos2, 2)
    
    def draw_zones(self):
        """Draw all zones"""
        for zone in self.graph.zones.values():
            pos = self.map_to_screen(zone)
            color = self.get_zone_color(zone)
            
            radius = 15 + zone.capacity * 2
            if zone.is_srt or zone.is_end:
                radius = 30
            
            pygame.draw.circle(self.screen, color, pos, radius)
            
            border_color = (255, 255, 255) if (zone.is_srt or zone.is_end) else (200, 200, 200)
            pygame.draw.circle(self.screen, border_color, pos, radius, 2)
            
            # Label
            font = pygame.font.SysFont('Arial', 11)
            text = font.render(zone.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(pos[0], pos[1] - radius - 12))
            self.screen.blit(text, text_rect)
    
    def update_animations(self, elapsed_ms):
        """Update all drone positions"""
        for state in self.drone_states:
            path = state.drone.path_schdl
            
            if state.path_index >= len(path) - 1:
                continue
            
            current_zone, _ = path[state.path_index]
            next_zone, _ = path[state.path_index + 1]
            
            if current_zone == next_zone:
                state.path_index += 1
                continue
            
            pos1 = self.map_to_screen(current_zone)
            pos2 = self.map_to_screen(next_zone)
            
            turn_duration_ms = 1000 / self.animation_speed
            state.progress += elapsed_ms / turn_duration_ms
            
            if state.progress >= 1.0:
                state.path_index += 1
                state.progress = 0.0
                state.current_pos = pos2
                
                # Check if delivered
                if next_zone.is_end:
                    self.delivered_count += 1
            else:
                t = state.progress
                x = pos1[0] + (pos2[0] - pos1[0]) * t
                y = pos1[1] + (pos2[1] - pos1[1]) * t
                state.current_pos = (int(x), int(y))
    
    def draw_drones(self):
        """Draw all drones"""
        for state in self.drone_states:
            if state.current_pos:
                pygame.draw.circle(self.screen, (255, 50, 50), state.current_pos, 8)
                
                font = pygame.font.SysFont('Arial', 10)
                text = font.render(str(state.drone.drone_id), True, (255, 255, 255))
                text_rect = text.get_rect(center=(state.current_pos[0], state.current_pos[1] - 15))
                self.screen.blit(text, text_rect)
    
    def draw_hud(self):
        """Draw info overlay"""
        font = pygame.font.SysFont('Arial', 20)
        
        turn_text = font.render(f"Turn: {self.current_turn}", True, (255, 255, 255))
        self.screen.blit(turn_text, (10, 10))
        
        delivery_text = font.render(
            f"Delivered: {self.delivered_count}/{len(self.graph.drones)}", 
            True, (255, 255, 255)
        )
        self.screen.blit(delivery_text, (10, 40))
        
        speed_text = font.render(f"Speed: {self.animation_speed:.1f}x", True, (255, 255, 255))
        self.screen.blit(speed_text, (10, 70))
        
        if self.paused:
            pause_text = font.render("PAUSED", True, (255, 255, 0))
            pause_rect = pause_text.get_rect(center=(self.WINDOW_WIDTH // 2, 30))
            self.screen.blit(pause_text, pause_rect)
        
        # Instructions
        font_small = pygame.font.SysFont('Arial', 14)
        instructions = font_small.render(
            "SPACE: Pause | Q: Quit | UP/DOWN: Speed", 
            True, (200, 200, 200)
        )
        self.screen.blit(instructions, (self.WINDOW_WIDTH - 300, 10))
    
    def run(self):
        """Main loop"""
        running = True
        
        while running:
            elapsed_ms = self.clock.tick(60)
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_UP:
                        self.animation_speed = min(self.animation_speed * 1.5, 10.0)
                    elif event.key == pygame.K_DOWN:
                        self.animation_speed = max(self.animation_speed / 1.5, 0.1)
            
            # Update
            if not self.paused:
                self.update_animations(elapsed_ms)
            
            # Draw
            self.screen.fill(self.BG_COLOR)
            self.draw_connections()
            self.draw_zones()
            self.draw_drones()
            self.draw_hud()
            
            pygame.display.flip()
            
            # Check if done
            if self.delivered_count == len(self.graph.drones):
                print(f"\nAll drones delivered in {self.current_turn} turns!")
                pygame.time.wait(2000)
                running = False
        
        pygame.quit()
```

### Usage in main.py

```python
from visual.gui import PyGameVisualizer

# After scheduling
visualizer = PyGameVisualizer(scheduler)
visualizer.run()
```

---

## 13. Color Scheme

### Recommended Colors (RGB)

```python
COLORS = {
    'background': (20, 20, 30),      # Dark blue-gray
    'start_zone': (50, 200, 50),     # Bright green
    'end_zone': (255, 215, 0),       # Gold
    'normal_zone': (100, 100, 150),  # Blue-gray
    'restricted': (150, 50, 150),    # Purple
    'priority': (50, 150, 200),      # Cyan
    'blocked': (50, 50, 50),         # Dark gray
    'connection': (80, 80, 80),      # Gray
    'drone': (255, 50, 50),          # Red
    'text': (255, 255, 255),         # White
    'text_dim': (200, 200, 200),     # Light gray
}
```

---

## 14. Performance Tips

### Pre-render Static Elements

Map doesn't change — draw it once to a surface, then blit:

```python
# In __init__
self.map_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
self.map_surface.fill(BG_COLOR)
self.draw_connections()  # Draw to map_surface
self.draw_zones()        # Draw to map_surface

# In main loop
screen.blit(self.map_surface, (0, 0))  # Fast blit
draw_drones()  # Only redraw drones
```

### Limit Font Renders

Create font objects once, not every frame:

```python
# In __init__
self.font_large = pygame.font.SysFont('Arial', 20)
self.font_small = pygame.font.SysFont('Arial', 14)
```

### Use `pygame.draw` Instead of Images

Drawing circles/lines is faster than loading/blitting images for simple shapes.

---

## Summary — What You Learned

1. **Pygame basics:** Surface, coordinate system, game loop
2. **Coordinate transformation:** Map coordinates → screen pixels
3. **Drawing:** Circles, lines, rectangles, text
4. **Animation:** Interpolation, smooth movement
5. **User input:** Keyboard, mouse hover
6. **Complete visualizer:** Full working implementation

Your visualizer shows:
- The map layout with colored zones
- Drones moving smoothly along paths
- Real-time info (turn, delivery count)
- Interactive controls (pause, speed up/down)

This will make debugging and presenting your project much easier.