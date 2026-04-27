import pygame
import sys


class Visualizer:
    def __init__(self, width: int = 800, hieght: int = 600):
        self.width = width
        self.hieght = hieght
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
        

    def update_move(self):
        """update events"""
        ...


vv = Visualizer()
vv.goo_goo()