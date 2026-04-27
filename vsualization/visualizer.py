import pygame
import sys
from ..elemnts.schedular import Scheduler


COLORS = {
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

class Visualizer:
    def __init__(self, schudeler: Scheduler, width: int = 800, hieght: int = 600):
        self.width = width
        self.hieght = hieght
        self.graph = schudeler.graph
        pygame.init()
        self.screen = pygame.display.set_mode((width, hieght))
        pygame.display.set_caption("most random visualization")
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.cal_offset()
        self.goo_goo()

    def goo_goo(self):
        """runing the main loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.K_SPACE:
                    self.update_move()
            self.screen.fill((25, 25, 25))
            self.draw_map()
            self.draw_drones()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

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
        """Draw all zones as circles"""
        for zone in self.graph.zones.values():
            pos = self.zone_to_screen(zone)
            pygame.draw.circle(self.screen, (100, 100, 100), pos, 20)
            text = self.font.render(zone.name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(pos[0], pos[1] + 35))
            self.screen.blit(text, text_rect)

    def update_move(self):
        """update events"""
        ...


vv = Visualizer()
vv.goo_goo()