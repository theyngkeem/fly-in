import sys
from map_parsing import MapParser
from elemnts import Graph
from elemnts.schedular import Scheduler
from elemnts.simulator import Simulator

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <map_file>")
        sys.exit(1)
    
    try:
        print("Parsing map...")
        parser = MapParser(sys.argv[1])
        parser.parse_map()

        print("Building graph...")
        graph = Graph(parser.zones, parser.coonection, parser.nb_drones)
        print(f"Graph built: {len(graph.zones)} zones, {len(graph.drones)} drones")

        print("Scheduling drones...")
        scheduler = Scheduler(graph)
        print(f"Scheduled {len(scheduler.stiemal_zaman)} drones")

        print("\nRunning simulation...")
        simulator = Simulator(scheduler)
        simulator.goo_goo_dolls()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
