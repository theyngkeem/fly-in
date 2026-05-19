import sys
from map_parsing import MapParser
from elemnts import Graph
from elemnts.schedular import Scheduler
from elemnts.simulator import Simulator
from vsualization import Visualizer
import pygame


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("try python pedri.py 'mapfile'")
        sys.exit(1)

    try:
        parser = MapParser(sys.argv[1])
        parser.parse_map()
        graph = Graph(parser.zones, parser.coonection, parser.nb_drones)
        scheduler = Scheduler(graph)
        simulator = Simulator(scheduler)
        simulator.goo_goo_dolls()
        vis = Visualizer(scheduler)
        vis.goo_goo()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pygame.quit()
        sys.exit()
