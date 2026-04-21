from .graph import Zone, Bridge, Graph
from collections import defaultdict
from typing import Tuple


class ReservationPath:
    def __init__(self, ):
        self.zone_reservation = defaultdict(lambda: defaultdict(int))
        self.bridge_reservation = defaultdict(lambda: defaultdict(int))

    def can_enter(self, zone: Zone, turn: int) -> bool:
        """check if drone can enter a zone"""
        if zone.is_srt or zone.is_end:
            return True
        return self.zone_reservation[zone.name][turn] < zone.capacity
    
    def reserve_zone(self, zone: Zone, turn: int) -> None:
        """reserve zone for a turn"""
        self.zone_reservation[zone.name][turn] += 1

    def reserve_bridge(self, bridge: Bridge, turn: int) -> None:
        """reserve bridge for a turn"""
        self.bridge_reservation[bridge.dup_check()][turn] += 1

    def can_use_bridge(self, bridge: Bridge, turn: int) -> bool:
        """check if bridge can be used"""
        return self.bridge_reservation[bridge.dup_check()][turn] < bridge.capacity

    def use_path(self, path: list[Tuple[Zone, int]], graph: Graph) -> None:
        """use a path for a drone"""
        for zone, turn in path:
            self.reserve_zone(zone, turn)
        for i in range(len(path) - 1):
            zone1, turn = path[i]
            zone2, _ = path[i + 1]
            flag = False
            for neighbor, bridge in graph.get_nighbor(zone1):
                if neighbor.name == zone2.name:
                    self.reserve_bridge(bridge, turn)
                    flag = True
                    break
            if not flag:
                raise ValueError(f"No bridge between {zone1.name}"
                                 f" and {zone2.name}")


class Scheduler:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.reservation = ReservationPath()
        self.schedule = self.schedule()

    def schudle(self):
        """a star for each drone"""
        conn = self.graph.get_nighbor(self.graph.start_hub)
        for zone, bridge in conn:
            bridge_outflow += bridge.capacity
            zone_outflow += zone.capacity
        outflow = min(bridge_outflow, zone_outflow)
        for drone in self.graph.drones:
            path = self.a_star(drone)
            self.reservation.use_path(path, self.graph)








