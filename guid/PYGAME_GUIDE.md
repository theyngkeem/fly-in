# 🎮 Pygame Visualization Guide — From Zero to Working
## Building a Turn-by-Turn Drone Routing Visualizer

---

## 📋 What We're Building

A pygame window that shows:
- **Zones** as colored circles positioned by their (x, y) coordinates
- **Connections** as lines between zones
- **Drones** as moving sprites (images or circles)
- **Turn-by-turn playback** — press SPACE to advance each turn
- **Status panel** showing current turn, drones delivered, etc.
- **Automatic color fallback** for invalid colors

---

## 🎯 Build Strategy — 7 Testable Steps

```
Step 1: Empty window that opens and closes ✓
Step 2: Draw static zones as circles ✓
Step 3: Add colors from map file ✓
Step 4: Draw connections between zones ✓
Step 5: Add turn-by-turn control (SPACE key) ✓
Step 6: Animate drones moving between zones ✓
Step 7: Add UI panel and polish ✓
```

Each step builds on the previous. Test before moving on.

---

## 📁 File Structure

```
fly-in/
├── visual/
│   ├── __init__.py
│   ├── colors.py              ← Step 3
│   └── visualizer.py          ← Steps 1-7
├── maps/
│   └── test_tiny.txt          ← Test map
└── main.py                    ← Modified to launch pygame
```

---

## 🚀 STEP 1 — Empty Window

**Goal:** Open a pygame window that you can close.

Create `visual/__init__.py`:
```python
# Empty file
```

Create `visual/visualizer.py`:

```python
import pygame
import sys

class Visualizer:
    def __init__(self):
        pygame.init()
        
        # Window setup
        self.width = 1200
        self.height = 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fly-in Visualizer")
        
        # Timing
        self.clock = pygame.time.Clock()
        self.fps = 60
        
        print("Visualizer initialized")
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Draw background
            self.screen.fill((20, 30, 48))  # Dark blue
            
            # Update display
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
        print("Closed")
```

**Test:**
```python
# test_step1.py
from visual.visualizer import Visualizer

vis = Visualizer()
vis.run()
```

**Expected:** Dark blue window opens. Press ESC to close. If this works, move to Step 2.

---

## 🎨 STEP 2 — Draw Static Zones

**Goal:** Draw circles for each zone from the graph.

Modify `visual/visualizer.py` — add scheduler parameter and drawing:

```python
import pygame
import sys
from elemnts.schedular import Scheduler

class Visualizer:
    def __init__(self, scheduler: Scheduler):
        pygame.init()
        
        self.scheduler = scheduler
        self.graph = scheduler.graph
        
        # Window setup
        self.width = 1200
        self.height = 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fly-in Visualizer")
        
        # Timing
        self.clock = pygame.time.Clock()
        self.fps = 60
        
        # Calculate viewport (fit all zones on screen)
        self.calculate_viewport()
        
        # Font
        self.font = pygame.font.Font(None, 20)
        
        print(f"Visualizer initialized: {len(self.graph.zones)} zones")
    
    def calculate_viewport(self):
        """Calculate scale and offset to fit all zones"""
        if not self.graph.zones:
            self.scale = 50
            self.offset_x = self.width // 2
            self.offset_y = self.height // 2
            return
        
        # Find bounding box
        zones_list = list(self.graph.zones.values())
        min_x = min(z.x for z in zones_list)
        max_x = max(z.x for z in zones_list)
        min_y = min(z.y for z in zones_list)
        max_y = max(z.y for z in zones_list)
        
        # Calculate scale to fit
        padding = 100
        usable_width = self.width - 2 * padding
        usable_height = self.height - 2 * padding
        
        if max_x > min_x:
            scale_x = usable_width / (max_x - min_x)
        else:
            scale_x = 50
        
        if max_y > min_y:
            scale_y = usable_height / (max_y - min_y)
        else:
            scale_y = 50
        
        self.scale = min(scale_x, scale_y, 80)  # Cap at 80
        
        # Center offset
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        self.offset_x = self.width // 2 - center_x * self.scale
        self.offset_y = self.height // 2 - center_y * self.scale
    
    def zone_to_screen(self, zone):
        """Convert zone (x, y) to screen pixels"""
        x = int(zone.x * self.scale + self.offset_x)
        y = int(zone.y * self.scale + self.offset_y)
        return (x, y)
    
    def draw_zones(self):
        """Draw all zones as circles"""
        for zone in self.graph.zones.values():
            pos = self.zone_to_screen(zone)
            
            # Draw circle
            pygame.draw.circle(self.screen, (100, 100, 100), pos, 20)
            
            # Draw zone name
            text = self.font.render(zone.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(pos[0], pos[1] + 35))
            self.screen.blit(text, text_rect)
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Draw
            self.screen.fill((20, 30, 48))
            self.draw_zones()
            
            # Update
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
        print("Closed")
```

**Test:**
```python
# In main.py, after scheduler:
from visual.visualizer import Visualizer

vis = Visualizer(scheduler)
vis.run()
```

**Expected:** Gray circles appear at zone positions with names below. If you see circles, move to Step 3.

---

## 🎨 STEP 3 — Add Colors

**Goal:** Use colors from map file, with fallback for invalid colors.

Create `visual/colors.py`:

```python
# Color name → RGB mapping
COLORS = {
    # Map colors
    "green": (34, 197, 94),
    "orange": (249, 115, 22),
    "red": (239, 68, 68),
    "purple": (168, 85, 247),
    "blue": (59, 130, 246),
    "cyan": (6, 182, 212),
    "yellow": (234, 179, 8),
    "gold": (245, 158, 11),
    "magenta": (217, 70, 239),
    "brown": (180, 83, 9),
    "lime": (132, 204, 22),
    "white": (255, 255, 255),
    "gray": (156, 163, 175),
    "black": (30, 30, 30),
}

def get_color(color_name):
    """
    Get RGB tuple for a color name.
    Returns gray if color not found.
    """
    if color_name is None:
        return COLORS["gray"]
    
    color_name = color_name.lower().strip()
    
    if color_name in COLORS:
        return COLORS[color_name]
    
    # Common variations
    if color_name == "grey":
        return COLORS["gray"]
    
    # Unknown color → fallback
    print(f"Warning: Unknown color '{color_name}', using gray")
    return COLORS["gray"]
```

Update `visual/visualizer.py` — import and use colors:

```python
from visual.colors import get_color, COLORS

# In draw_zones():
def draw_zones(self):
    """Draw all zones as circles with their colors"""
    for zone in self.graph.zones.values():
        pos = self.zone_to_screen(zone)
        
        # Get zone color
        color = get_color(zone.color)
        
        # Draw circle
        pygame.draw.circle(self.screen, color, pos, 20)
        pygame.draw.circle(self.screen, (255, 255, 255), pos, 20, 2)  # white border
        
        # Draw zone name
        text = self.font.render(zone.name, True, (255, 255, 255))
        text_rect = text.get_rect(center=(pos[0], pos[1] + 35))
        self.screen.blit(text, text_rect)
```

**Test:** Run again. Zones should now show their actual colors from the map file. Invalid colors become gray.

---

## 📊 STEP 4 — Draw Connections

**Goal:** Draw lines between connected zones.

Update `visual/visualizer.py` — add connection drawing:

```python
def draw_connections(self):
    """Draw lines between connected zones"""
    for bridge in self.graph.connections:
        pos1 = self.zone_to_screen(bridge.first_zone)
        pos2 = self.zone_to_screen(bridge.second_zone)
        
        # Draw line
        pygame.draw.line(self.screen, (70, 70, 90), pos1, pos2, 2)

# In run() method, draw connections BEFORE zones:
def run(self):
    # ...
    while running:
        # ...
        # Draw
        self.screen.fill((20, 30, 48))
        self.draw_connections()  # ← Add this
        self.draw_zones()
        # ...
```

**Test:** Lines should appear connecting zones. If you see the full graph structure, move to Step 5.

---

## ⏯️ STEP 5 — Turn-by-Turn Control

**Goal:** Press SPACE to advance turns one at a time.

Update `visual/visualizer.py` — add turn control:

```python
class Visualizer:
    def __init__(self, scheduler: Scheduler):
        # ... existing init code ...
        
        # Turn state
        self.current_turn = 0
        self.max_turn = self.find_max_turn()
        
        # Build turn events
        self.turn_events = self.build_turn_events()
        
        print(f"Ready: {self.max_turn} turns total")
    
    def find_max_turn(self):
        """Find last turn where any drone moves"""
        max_t = 0
        for drone in self.scheduler.stiemal_zaman:
            if drone.path_schdl:
                _, last_turn = drone.path_schdl[-1]
                max_t = max(max_t, last_turn)
        return max_t
    
    def build_turn_events(self):
        """Build dict: turn → list of (drone, from_zone, to_zone)"""
        from collections import defaultdict
        events = defaultdict(list)
        
        for drone in self.scheduler.stiemal_zaman:
            path = drone.path_schdl
            
            for i in range(len(path) - 1):
                zone, turn = path[i]
                next_zone, _ = path[i + 1]
                
                if zone != next_zone:  # actual move
                    events[turn].append((drone, zone, next_zone))
        
        return events
    
    def advance_turn(self):
        """Move to next turn"""
        if self.current_turn < self.max_turn:
            self.current_turn += 1
            print(f"\n=== Turn {self.current_turn} ===")
            
            moves = self.turn_events.get(self.current_turn, [])
            for drone, from_z, to_z in moves:
                print(f"  D{drone.drone_id}: {from_z.name} → {to_z.name}")
        else:
            print("Simulation complete!")
    
    def draw_ui(self):
        """Draw turn counter"""
        text = self.font.render(f"Turn: {self.current_turn}/{self.max_turn}  |  SPACE=Next  ESC=Quit",
                                True, (255, 255, 255))
        self.screen.blit(text, (20, 20))
    
    def run(self):
        """Main game loop"""
        running = True
        
        print("\nPress SPACE to advance turns")
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE:
                        self.advance_turn()  # ← Add this
            
            # Draw
            self.screen.fill((20, 30, 48))
            self.draw_connections()
            self.draw_zones()
            self.draw_ui()  # ← Add this
            
            # Update
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
        print("Closed")
```

**Test:** Press SPACE. Terminal should print turn info. Counter at top should increase. If working, move to Step 6.

---

## 🎬 STEP 6 — Animate Drones

**Goal:** Show drones moving smoothly between zones.

Update `visual/visualizer.py` — add animation:

```python
class DroneAnimation:
    """Animates a drone moving from A to B"""
    def __init__(self, drone, from_zone, to_zone, duration_ms=800):
        self.drone = drone
        self.from_zone = from_zone
        self.to_zone = to_zone
        self.duration = duration_ms
        self.elapsed = 0
        self.complete = False
    
    def update(self, dt):
        """Update progress. dt = milliseconds since last frame"""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.complete = True
    
    def get_progress(self):
        """Returns 0.0 to 1.0"""
        return min(1.0, self.elapsed / self.duration)
    
    def get_position(self, scale, offset_x, offset_y):
        """Get current interpolated position"""
        t = self.get_progress()
        
        # Interpolate between from and to
        from_x = self.from_zone.x * scale + offset_x
        from_y = self.from_zone.y * scale + offset_y
        to_x = self.to_zone.x * scale + offset_x
        to_y = self.to_zone.y * scale + offset_y
        
        x = from_x + (to_x - from_x) * t
        y = from_y + (to_y - from_y) * t
        
        return (x, y)


class Visualizer:
    def __init__(self, scheduler: Scheduler):
        # ... existing init ...
        
        # Animation state
        self.animations = []
    
    def advance_turn(self):
        """Move to next turn and start animations"""
        if self.current_turn < self.max_turn:
            self.current_turn += 1
            print(f"\n=== Turn {self.current_turn} ===")
            
            # Start animations for this turn's moves
            moves = self.turn_events.get(self.current_turn, [])
            for drone, from_z, to_z in moves:
                anim = DroneAnimation(drone, from_z, to_z, duration_ms=800)
                self.animations.append(anim)
                print(f"  D{drone.drone_id}: {from_z.name} → {to_z.name}")
        else:
            print("Simulation complete!")
    
    def update_animations(self, dt):
        """Update all active animations"""
        for anim in self.animations:
            anim.update(dt)
        
        # Remove completed
        self.animations = [a for a in self.animations if not a.complete]
    
    def draw_drones(self):
        """Draw all drones (animating or static)"""
        # Draw animating drones
        for anim in self.animations:
            pos = anim.get_position(self.scale, self.offset_x, self.offset_y)
            
            # Draw drone circle
            pygame.draw.circle(self.screen, (0, 255, 255), 
                             (int(pos[0]), int(pos[1])), 8)
            
            # Draw ID
            text = self.font.render(f"D{anim.drone.drone_id}", True, (255, 255, 255))
            text_rect = text.get_rect(center=(pos[0], pos[1] - 15))
            self.screen.blit(text, text_rect)
        
        # Draw static drones (not currently animating)
        for drone in self.scheduler.stiemal_zaman:
            # Skip if animating
            if any(a.drone == drone for a in self.animations):
                continue
            
            # Skip if delivered
            if drone.drone_state.value == "delivered":
                continue
            
            # Find current position
            current_zone = None
            for zone, turn in drone.path_schdl:
                if turn == self.current_turn:
                    current_zone = zone
                    break
            
            if current_zone:
                pos = self.zone_to_screen(current_zone)
                pygame.draw.circle(self.screen, (100, 255, 100), pos, 6)
    
    def run(self):
        """Main game loop"""
        running = True
        
        print("\nPress SPACE to advance turns")
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE:
                        self.advance_turn()
            
            # Update animations
            dt = self.clock.get_time()
            self.update_animations(dt)
            
            # Draw
            self.screen.fill((20, 30, 48))
            self.draw_connections()
            self.draw_zones()
            self.draw_drones()  # ← Add this
            self.draw_ui()
            
            # Update
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
        print("Closed")
```

**Test:** Press SPACE. Drones should smoothly animate between zones over ~0.8 seconds. If working, move to Step 7.

---

## ✨ STEP 7 — Polish UI

**Goal:** Add a nice status panel and better visuals.

Update `visual/visualizer.py` — enhance UI:

```python
def draw_ui(self):
    """Draw status panel"""
    # Panel background
    panel_rect = pygame.Rect(10, 10, 300, 120)
    pygame.draw.rect(self.screen, (40, 50, 70), panel_rect, border_radius=10)
    pygame.draw.rect(self.screen, (100, 120, 150), panel_rect, 2, border_radius=10)
    
    y = 25
    
    # Turn counter
    text = self.font.render(f"Turn: {self.current_turn} / {self.max_turn}", 
                           True, (255, 255, 255))
    self.screen.blit(text, (20, y))
    y += 30
    
    # Delivered count
    delivered = sum(1 for d in self.scheduler.stiemal_zaman 
                   if d.drone_state.value == "delivered")
    total = len(self.scheduler.stiemal_zaman)
    text = self.font.render(f"Delivered: {delivered} / {total}", 
                           True, (100, 255, 100))
    self.screen.blit(text, (20, y))
    y += 30
    
    # Moving count
    text = self.font.render(f"Moving: {len(self.animations)}", 
                           True, (255, 200, 100))
    self.screen.blit(text, (20, y))
    y += 30
    
    # Controls
    controls = self.font.render("SPACE=Next  R=Reset  ESC=Quit", 
                               True, (150, 150, 150))
    self.screen.blit(controls, (20, self.height - 30))
```

Add reset functionality:

```python
def reset(self):
    """Reset to turn 0"""
    self.current_turn = 0
    self.animations.clear()
    print("\nReset to turn 0")

# In run() event handling:
if event.key == pygame.K_r:
    self.reset()
```

**Final test:** Full visualization with smooth animations, colored zones, turn control, and status panel.

---

## 🎨 BONUS — Add Drone Images

If you have a `drone.png` image (24x24):

```python
# In __init__:
try:
    self.drone_image = pygame.image.load("assets/drone.png")
    self.drone_image = pygame.transform.scale(self.drone_image, (24, 24))
except:
    self.drone_image = None

# In draw_drones(), replace circle:
if self.drone_image:
    rect = self.drone_image.get_rect(center=(int(pos[0]), int(pos[1])))
    self.screen.blit(self.drone_image, rect)
else:
    pygame.draw.circle(self.screen, (0, 255, 255), ...)
```

---

## 📝 Quick Reference

| Key | Action |
|---|---|
| SPACE | Next turn |
| R | Reset |
| ESC | Quit |

| Color | Meaning |
|---|---|
| Colored circles | Zones (from map) |
| Cyan/Green dots | Drones |
| Gray lines | Connections |

---

## 🐛 Common Issues

**Issue:** "No module named 'pygame'"
**Fix:** `pip install pygame`

**Issue:** Zones off-screen
**Fix:** Check `calculate_viewport()` is called in `__init__`

**Issue:** Drones don't move
**Fix:** Check `drone.path_schdl` is filled by Scheduler

**Issue:** Color not showing
**Fix:** Add color to `COLORS` dict in `colors.py`

---

**You now have a complete, working visualization. Test each step before moving on. The whole thing is ~300 lines total.**
