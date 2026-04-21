from typing import Any, Tuple
from .zone import Zone, Bridge, ZoneType
from .drone import Drone, DroneState


class Graph:
    def __init__(self, zones: dict[str, Any], connection: list[dict],
                 nb_drone: int):
        self.zones = self.creat_zone(zones)
        self.connections = self.creat_conn(connection)
        self.map = self.creat_map()
        self.drones = self.creat_drone(nb_drone)
        self.path = self.bfs()

    def creat_zone(self, zones: dict[str, Any]) -> dict[str, Zone]:
        """creat ZOnes that been parsed"""
        res = {}
        for zone in zones.values():
            optional = zone.get("optional", {})
            color = optional.get("color", "white")
            zone_type = optional.get("zone", "normal")
            max_drones = optional.get("max_drones", 1)
            el = Zone(zone["name"], color,
                      ZoneType(zone_type),
                      max_drones,
                      zone["type"],
                      zone["x"], zone["y"])
            if el.name == "start_hub":
                self.start_hub = el
            elif el.name == "end_hub":
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
