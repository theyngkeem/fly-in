from typing import Any, Tuple
from .zone import Zone, Bridge, ZoneType
from .drone import Drone, DroneState
import heapq


class Graph:
    def __init__(self, zones: dict[str, Any], connection: list[dict],
                 nb_drone: int):
        self.start_hub = None
        self.end_hub = None
        self.zones = self.creat_zone(zones)
        self.connections = self.creat_conn(connection)
        self.map = self.creat_map()
        self.drones = self.creat_drone(nb_drone)
        self.best_op = self.djikstra()

    def creat_zone(self, zones: dict[str, Any]) -> dict[str, Zone]:
        """creat ZOnes that been parsed"""
        res = {}
        for zone in zones.values():
            optional = zone.get("optional", {})
            color = optional.get("color", "white")
            zone_type = ZoneType(optional.get("zone") or "normal")
            max_drones = optional.get("max_drones", 1)
            el = Zone(zone["name"], color,
                      zone_type,
                      max_drones,
                      zone["type"],
                      zone["x"], zone["y"])
            if el.is_srt:
                self.start_hub = el
            elif el.is_end:
                self.end_hub = el
            res[el.name] = el
        return res

    def creat_conn(self, connection: list[dict]) -> list[Bridge]:
        """creat bridges"""
        res = []
        for bridge in connection:
            optional = bridge.get("optional", {})
            capacity = optional.get("max_link_capacity", 1)
            el = Bridge(self.zones[bridge["first_zone"]],
                        self.zones[bridge["destination"]],
                        capacity)
            res.append(el)
        return res

    def creat_drone(self, nb_drones: int) -> list[Drone]:
        """creat drones"""
        res = []
        for i in range(nb_drones):
            res.append(Drone(i, DroneState.waiting, self.start_hub))
        return res
    
    def creat_map(self) -> dict[str, list[Bridge]]:
        """creat map of the graph"""
        res = {}
        for br in self.connections:
            if br.first_zone.name in res:
                res[br.first_zone.name].append(br)
            else:
                res[br.first_zone.name] = [br]
            if br.second_zone.name in res:
                res[br.second_zone.name].append(br)
            else:
                res[br.second_zone.name] = [br]
        return res

    def get_nighbor(self, zone: Zone) -> list[Tuple[Zone, Bridge]]:
        """get neighbor of a zone"""
        res = []
        for br in self.map.get(zone.name, []):
            nighbor = br.next_zone(zone)
            if nighbor.accecible:
                res.append((nighbor, br))
        return res

    def djikstra(self) -> dict[Zone, float]:
        """DJIKSTRA to get shortest path from end to zone givven"""
        tobo = []
        heapq.heappush(tobo, (0.0, self.end_hub.name, self.end_hub))
        costs = {self.end_hub: 0.0}
        while tobo:
            cost, _, zone = heapq.heappop(tobo)
            if cost > costs[zone]:
                continue
            for nighbor, _ in self.get_nighbor(zone):
                if not nighbor.accecible:
                    continue
                if nighbor.zone_type == ZoneType.priority:
                    ncost = cost + 0.9
                else:
                    ncost = cost + nighbor.cost
                if nighbor not in costs or ncost < costs[nighbor]:
                    costs[nighbor] = ncost
                    heapq.heappush(tobo, (ncost, nighbor.name, nighbor))
        return costs
