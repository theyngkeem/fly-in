from elemnts.drone import Drone
from .graph import Zone, Bridge, Graph
from collections import defaultdict
from typing import Tuple
import heapq


class ReservationPath:
    def __init__(self):
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
        self.max_wait = 100
        self.maz_retry = 10
        self.graph = graph
        self.reservation = ReservationPath()
        self.stiemal_zaman = self.schudle()

    def schudle(self) -> list[Drone]:
        """apply a star for each drone"""
        start_flow = self.calcul_flow()
        for i, drone in enumerate(self.graph.drones):
            path = self.a_star(drone, start_flow[i])
            retry = 0
            start_turn = start_flow[i]
            while path is None and retry < self.maz_retry:
                start_turn += 1
                path = self.a_star(drone, start_turn)
                retry += 1
            if path is None:
                raise Exception(f"Drone {drone.drone_id} could not find path")
            drone.path_schdl = path
            self.reservation.use_path(path, self.graph)
        return self.graph.drones

    def calcul_flow(self) -> list[int]:
        """calculate how much can i sed in the firt turn"""
        outflow = 0
        for nighbor, bridge in self.graph.get_nighbor(self.graph.start_hub):
            outflow += min(bridge.capacity, nighbor.capacity)
        if outflow == 0:
            raise ValueError("no valid exit from start zone")
        start_flow = []
        curr_turn = 0
        c = 0
        for i in range(len(self.graph.drones)):
            start_flow.append(curr_turn)
            c += 1
            if c == outflow:
                c = 0
                curr_turn += 1
        return start_flow

    def a_star(self, drone: Drone, start_turn: int) -> list[Tuple[Zone, int]] | None:
        """a star to find the best path for drone"""
        tobo = []
        start = (self.graph.start_hub, start_turn)
        g = 0
        f = g + self.graph.best_op[self.graph.start_hub]
        heapq.heappush(tobo, (f, g, start[0], start[1]))
        visited = set()
        from_zone = {}
        g_arch = {start: 0}
        while tobo:
            f, g, zone, turn = heapq.heappop(tobo)
            if (zone, turn) in visited:
                continue
            visited.add((zone, turn))
            if zone.is_end:
                return self.get_path(from_zone, (zone, turn), start_turn)
            for nighbor, bridge in self.graph.get_nighbor(zone):
                to_move = turn + nighbor.cost
                if to_move > self.max_wait:
                    continue
                if not self.reservation.can_enter(nighbor, to_move):
                    continue
                if not self.reservation.can_use_bridge(bridge, turn):
                    continue
                new_g = g + nighbor.cost
                new_zone = (nighbor, to_move)
                if new_zone in g_arch and new_g > g_arch[new_zone]:
                    continue
                g_arch[new_zone] = new_g
                from_zone[new_zone] = (zone, turn)
                new_f = new_g + self.graph.best_op[nighbor]
                heapq.heappush(tobo, (new_f, new_g, nighbor, to_move))
            
            wait_c = turn + 1
            if wait_c <= self.max_wait:
                if self.reservation.can_enter(zone, wait_c):
                    new_g = g + 1
                    wait_zone = (zone, wait_c)
                    if wait_zone not in g_arch or new_g < g_arch[wait_zone]:
                        g_arch[wait_zone] = new_g
                        from_zone[wait_zone] = (zone, turn)
                        new_f = new_g + self.graph.best_op[zone]
                        heapq.heappush(tobo, (new_f, new_g, zone, wait_c))
        return None

    def get_path(self, from_zone: dict, curr_zone: Tuple[Zone, int], start_turn: int) -> list[Tuple[Zone, int]]:
        """get path from a star result"""
        res = []
        while curr_zone in from_zone:
            res.append(curr_zone)
            curr_zone = from_zone[curr_zone]
        res.append((self.graph.start_hub, start_turn))
        res.reverse()
        return res
