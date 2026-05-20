import sys
import importlib.util as im


def check_pckg():
    "checking the packages"
    if im.find_spec("pygame") is None:
        raise ImportError


if __name__ == "__main__":
    try:
        check_pckg()
        if len(sys.argv) < 2:
            print("try python pedri.py 'mapfile'")
            sys.exit(1)
        from map_parsing import MapParser
        from elemnts import Graph
        from elemnts.schedular import Scheduler
        from elemnts.simulator import Simulator
        from vsualization import Visualizer
    except ImportError:
        print("the packages not installed yet")
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
        sys.exit()
