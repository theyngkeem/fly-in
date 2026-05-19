import pygame
import sys
from elemnts import Scheduler


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
        from_x = self.from_zone.x * scale + offset_x
        from_y = self.from_zone.y * scale + offset_y
        to_x = self.to_zone.x * scale + offset_x
        to_y = self.to_zone.y * scale + offset_y
        x = from_x + (to_x - from_x) * t
        y = from_y + (to_y - from_y) * t
        return (x, y)


class Visualizer:
    def __init__(self, schudeler: Scheduler, width: int = 1200,
                 hieght: int = 800):
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
        pygame.display.set_caption("most random visualization")
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.cal_offset()
        self.animations: list[DroneAnimation] = []

    def goo_goo(self):
        """runing the main loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset()
                    if event.key == pygame.K_SPACE:
                        self.update_move()
                    if event.key == pygame.K_EQUALS:
                        self.scale *= 1.1
                    if event.key == pygame.K_MINUS:
                        self.scale *= 0.9
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
        sys.exit()

    def reset(self):
        """Reset to turn 0"""
        self.curr_turn = 0
        self.animations.clear()

    def cal_offset(self):
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
        padding = 100
        usable_width = self.width - 2 * padding
        usable_height = self.hieght - 2 * padding
        if max_x > min_x:
            scale_x = usable_width / (max_x - min_x)
        else:
            scale_x = 50

        if max_y > min_y:
            scale_y = usable_height / (max_y - min_y)
        else:
            scale_y = 50
        self.scale = min(scale_x, scale_y, 80)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.offset_x = self.width // 2 - center_x * self.scale
        self.offset_y = self.hieght // 2 - center_y * self.scale

    def zone_to_screen(self, zone):
        """Convert zone (x, y) to screen pixels"""
        x = int(zone.x * self.scale + self.offset_x)
        y = int(zone.y * self.scale + self.offset_y)
        return (x, y)

    def draw_zones(self):
        """Draw all zones as circles with their colors"""
        for zone in self.graph.zones.values():
            pos = self.zone_to_screen(zone)
            color = self.get_color(zone.color)
            pygame.draw.circle(self.screen, color, pos, 20)
            pygame.draw.circle(self.screen, (255, 255, 255), pos, 20, 2)
            text = self.font.render(zone.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(pos[0], pos[1] - 35))
            self.screen.blit(text, text_rect)

    def draw_connections(self):
        """Draw lines between connected zones"""
        for bridge in self.graph.connections:
            pos1 = self.zone_to_screen(bridge.first_zone)
            pos2 = self.zone_to_screen(bridge.second_zone)
            pygame.draw.line(self.screen, (70, 70, 90), pos1, pos2, 2)

    def get_color(self, color_name: str):
        """tuple for a color name"""
        if color_name is None:
            return tuple(pygame.Color("gray"))[:3]

        color_name = color_name.lower().strip()
        try:
            return tuple(pygame.Color(color_name))[:3]
        except ValueError:
            return tuple(pygame.Color("gray"))[:3]

    def draw_drones(self):
        """Draw all drones (animating or static)"""
        for anim in self.animations:
            pos = anim.get_position(self.scale, self.offset_x, self.offset_y)
            pygame.draw.circle(self.screen, (0, 255, 255),
                               (int(pos[0]), int(pos[1])), 8)
            text = self.font.render(f"D{anim.drone.drone_id}",
                                    True, (255, 255, 255))
            text_rect = text.get_rect(center=(pos[0], pos[1] - 15))
            self.screen.blit(text, text_rect)
        for drone in self.scheduler.stiemal_zaman:
            if any(a.drone == drone for a in self.animations):
                continue
            if drone.drone_state.value == "delivered":
                continue
            current_zone = None
            for zone, turn in drone.path_schdl:
                if turn <= self.curr_turn:
                    current_zone = zone
                else:
                    break
            if current_zone:
                pos = self.zone_to_screen(current_zone)
                pygame.draw.circle(self.screen, (100, 255, 100), pos, 6)

    def draw_u(self):
        """Ultra minimal just turn number"""
        text = self.font.render(f"{self.curr_turn}/{self.max_turn}",
                                True, (120, 120, 120))
        self.screen.blit(text, (10, 10))

    def update_animations(self, dt):
        """Update all active animations"""
        for anim in self.animations:
            anim.update(dt)
        self.animations = [a for a in self.animations if not a.complete]

    def build_events(self):
        """Build dict: turn list"""
        from collections import defaultdict
        events = defaultdict(list)
        for drone in self.scheduler.stiemal_zaman:
            path = drone.path_schdl
            for i in range(len(path) - 1):
                zone, turn = path[i]
                next_zone, _ = path[i + 1]
                if zone != next_zone:
                    events[turn + 1].append((drone, zone, next_zone))
        return events

    def fmax_turn(self):
        """Find last turn where any drone moves"""
        max_t = 0
        for drone in self.scheduler.stiemal_zaman:
            if drone.path_schdl:
                _, last_turn = drone.path_schdl[-1]
                max_t = max(max_t, last_turn)
        return max_t

    def update_move(self):
        """Move to next turn"""
        if self.curr_turn < self.max_turn:
            self.curr_turn += 1
            moves = self.turn_events.get(self.curr_turn, [])
            for drone, from_z, to_z in moves:
                an = DroneAnimation(drone, from_z, to_z)
                self.animations.append(an)
        else:
            print("Simulation complete!")
