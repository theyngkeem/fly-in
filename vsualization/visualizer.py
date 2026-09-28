import pygame
from elemnts import Scheduler, Zone, Drone


class DroneAnimation:
    """Animates a drone moving from A to B"""
    def __init__(self, drone: Drone, from_zone: Zone, to_zone: Zone,
                 duration_ms: int = 800, start_fraction: float = 0.0,
                 end_fraction: float = 1.0):
        """Animate one turn's fraction of a drone's movement."""
        self.drone = drone
        self.from_zone = from_zone
        self.to_zone = to_zone
        self.duration = duration_ms
        self.start_fraction = start_fraction
        self.end_fraction = end_fraction
        self.elapsed = 0
        self.complete = False

    def update(self, dt: int) -> None:
        """Update progress. dt = milliseconds since last frame"""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.complete = True

    def get_progress(self) -> float:
        """Return the animation progress between zero and one."""
        return min(1.0, self.elapsed / self.duration)

    def get_position(self, scale: float, offset_x: float,
                     offset_y: float) -> tuple[float, float]:
        """Return the interpolated screen position for this turn."""
        t = self.start_fraction + (
            self.end_fraction - self.start_fraction
        ) * self.get_progress()
        from_x = self.from_zone.x * scale + offset_x
        from_y = self.from_zone.y * scale + offset_y
        to_x = self.to_zone.x * scale + offset_x
        to_y = self.to_zone.y * scale + offset_y
        x = from_x + (to_x - from_x) * t
        y = from_y + (to_y - from_y) * t
        return (x, y)


class Visualizer:
    """Display the scheduled graph and animate drone movements."""

    def __init__(self, schudeler: Scheduler, width: int = 1200,
                 hieght: int = 800) -> None:
        """Initialize the Pygame window and visualization state."""
        self.width = width
        self.hieght = hieght
        self.graph = schudeler.graph
        self.scheduler = schudeler
        self.curr_turn = 0
        self.max_turn = self.fmax_turn()
        self.turn_events = self.build_events()
        pygame.init()
        self.font = pygame.font.Font(None, 20)
        self.screen = pygame.display.set_mode((width, hieght))
        pygame.display.set_caption("fly-in")
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.scale: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.cal_offset()
        self.animations: list[DroneAnimation] = []

    def goo_goo(self) -> None:
        """runing the main loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_r:
                        self.reset()
                    if event.key == pygame.K_SPACE:
                        self.update_move()
                    if event.key in (pygame.K_EQUALS, pygame.K_PLUS,
                                     pygame.K_KP_PLUS):
                        self.scale = min(800.0, self.scale * 1.1)
                    if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.scale = max(0.0001, self.scale / 1.1)
                    if event.key == pygame.K_RIGHT:
                        self.offset_x -= 50
                    if event.key == pygame.K_LEFT:
                        self.offset_x += 50
                    if event.key == pygame.K_DOWN:
                        self.offset_y -= 50
                    if event.key == pygame.K_UP:
                        self.offset_y += 50

            dt = self.clock.get_time()
            self.update_animations(dt)
            self.screen.fill((25, 25, 25))
            self.draw_connections()
            self.draw_zones()
            self.draw_drones()
            self.draw_u()
            pygame.display.flip()
            self.clock.tick(self.fps)
        pygame.quit()

    def reset(self) -> None:
        """Reset to turn 0"""
        self.curr_turn = 0
        self.animations.clear()
        self.cal_offset()

    def cal_offset(self) -> None:
        """calculate offset to fit zones"""
        if not self.graph.zones:
            self.scale = 50
            self.offset_x = self.width // 2
            self.offset_y = self.hieght // 2
            return
        zones_list = list(self.graph.zones.values())
        min_x = min(z.x for z in zones_list)
        max_x = max(z.x for z in zones_list)
        min_y = min(z.y for z in zones_list)
        max_y = max(z.y for z in zones_list)
        padding = 120
        usable_width = self.width - 2 * padding
        usable_height = self.hieght - 2 * padding
        if max_x > min_x:
            scale_x = usable_width / (max_x - min_x)
        else:
            scale_x = usable_width

        if max_y > min_y:
            scale_y = usable_height / (max_y - min_y)
        else:
            scale_y = usable_height
        self.scale = min(scale_x, scale_y, 160)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.offset_x = self.width // 2 - center_x * self.scale
        self.offset_y = self.hieght // 2 - center_y * self.scale

    def zone_to_screen(self, zone: Zone) -> tuple:
        """Convert zone (x, y) to screen pixels"""
        x = int(zone.x * self.scale + self.offset_x)
        y = int(zone.y * self.scale + self.offset_y)
        return (x, y)

    def draw_zones(self) -> None:
        """Draw all zones as circles with their colors"""
        for zone in self.graph.zones.values():
            pos = self.zone_to_screen(zone)
            color = self.get_color(zone.color)
            pygame.draw.circle(self.screen, color, pos, 20)
            text = self.font.render(zone.name, True, (220, 220, 220))
            text_rect = text.get_rect(center=(pos[0], pos[1] - 35))
            pygame.draw.rect(self.screen, (25, 25, 25),
                             text_rect.inflate(8, 4))
            self.screen.blit(text, text_rect)
            kind = zone.zone_type.value
            if zone.is_srt:
                kind = "start"
            elif zone.is_end:
                kind = "end"
            elif kind == "normal":
                kind = ""
            if kind:
                label = self.font.render(kind, True, (140, 140, 140))
                self.screen.blit(label, label.get_rect(
                    center=(pos[0], pos[1] + 33)))

    def draw_connections(self) -> None:
        """Draw lines between connected zones"""
        for bridge in self.graph.connections:
            pos1 = self.zone_to_screen(bridge.first_zone)
            pos2 = self.zone_to_screen(bridge.second_zone)
            pygame.draw.line(self.screen, (80, 80, 80), pos1, pos2, 1)

    def get_color(self, color_name: str) -> tuple:
        """tuple for a color name"""
        if color_name is None:
            return tuple(pygame.Color("gray"))[:3]

        color_name = color_name.lower().strip()
        try:
            return tuple(pygame.Color(color_name))[:3]
        except ValueError:
            return tuple(pygame.Color("gray"))[:3]

    def position_at(self, drone: Drone, turn: int
                    ) -> tuple[float, float] | None:
        """Return map coordinates at a turn, or None after delivery."""
        path = drone.path_schdl
        if not path or turn >= path[-1][1]:
            return None
        if turn <= path[0][1]:
            return (path[0][0].x, path[0][0].y)
        for (zone, departure), (next_zone, arrival) in zip(path, path[1:]):
            if departure <= turn < arrival:
                progress = (turn - departure) / (arrival - departure)
                return (zone.x + (next_zone.x - zone.x) * progress,
                        zone.y + (next_zone.y - zone.y) * progress)
        return None

    def draw_drones(self) -> None:
        """Draw scheduled positions, grouping drones that share a spot."""
        active = {a.drone.drone_id: a for a in self.animations}
        positions: dict[tuple[int, int], list[int]] = {}
        for drone in self.scheduler.stiemal_zaman:
            if drone.drone_id in active:
                x, y = active[drone.drone_id].get_position(
                    self.scale, self.offset_x, self.offset_y)
            else:
                pos = self.position_at(drone, self.curr_turn)
                if pos is None:
                    continue
                x = pos[0] * self.scale + self.offset_x
                y = pos[1] * self.scale + self.offset_y
            positions.setdefault((int(x), int(y)), []).append(drone.drone_id)
        for pos, ids in positions.items():
            pygame.draw.circle(self.screen, (0, 220, 220), pos, 6)
            label = f"D{ids[0]}" if len(ids) == 1 else f"{len(ids)} drones"
            text = self.font.render(label, True, (220, 220, 220))
            rect = text.get_rect(center=(pos[0], pos[1] - 17))
            pygame.draw.rect(self.screen, (25, 25, 25), rect.inflate(6, 2))
            self.screen.blit(text, rect)

    def draw_u(self) -> None:
        """Show the turn, delivered count, and keyboard controls."""
        settled_turn = self.curr_turn - bool(self.animations)
        delivered = sum(d.path_schdl[-1][1] <= settled_turn
                        for d in self.scheduler.stiemal_zaman)
        total = len(self.scheduler.stiemal_zaman)
        status = (f"turn {self.curr_turn}/{self.max_turn}   "
                  f"arrived: {delivered}/{total}")
        self.screen.blit(self.font.render(status, True, (170, 170, 170)),
                         (10, 10))
        controls = ("space: next   r: restart   +/-: zoom   "
                    "arrows: move   esc: quit")
        self.screen.blit(self.font.render(controls, True, (140, 140, 140)),
                         (10, self.hieght - 25))

    def update_animations(self, dt: int) -> None:
        """Update all active animations"""
        for anim in self.animations:
            anim.update(dt)
        self.animations = [a for a in self.animations if not a.complete]

    def build_events(self) -> dict:
        """Build dict: turn list"""
        from collections import defaultdict
        events = defaultdict(list)
        for drone in self.scheduler.stiemal_zaman:
            path = drone.path_schdl
            for i in range(len(path) - 1):
                zone, turn = path[i]
                next_zone, arrival = path[i + 1]
                if zone != next_zone:
                    duration = arrival - turn
                    for step in range(1, duration + 1):
                        events[turn + step].append((
                            drone, zone, next_zone,
                            (step - 1) / duration, step / duration))
        return events

    def fmax_turn(self) -> int:
        """Find last turn where any drone moves"""
        max_t = 0
        for drone in self.scheduler.stiemal_zaman:
            if drone.path_schdl:
                _, last_turn = drone.path_schdl[-1]
                max_t = max(max_t, last_turn)
        return max_t

    def update_move(self) -> None:
        """Move to next turn"""
        if len(self.animations) > 0:
            return
        if self.curr_turn < self.max_turn:
            self.curr_turn += 1
            moves = self.turn_events.get(self.curr_turn, [])
            for drone, from_z, to_z, start, end in moves:
                an = DroneAnimation(drone, from_z, to_z,
                                    start_fraction=start, end_fraction=end)
                self.animations.append(an)
