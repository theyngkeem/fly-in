from typing import Any
from .zone import Zone, Bridge, ZoneType
from .drone import Drone, DroneState


class Graph:
    def __init__(self, zones: dict[str, Any], connection: list[dict],
                 nb_drone: int):
        self.zones = self.creat_zone(zones)
        self.connections = self.creat_conn(connection)
        self.drones = self.creat_drone(nb_drone)
        self.path = self.bfs()

    def creat_zone(self, zones: dict[str, Any]) -> list[Zone]:
        """creat ZOnes that been parsed"""
        res = []
        for zone in zones.values():
            el = Zone(zone["name"], zone["optional"]["color"],
                      ZoneType(zone["optional"]["zone"]),
                      zone["optional"]["max_drones"],
                      zone["type"],
                      zone["x"], zone["y"])
            res.append(el)
        return res

    def creat_conn(self, connection: list[dict]) -> list[Bridge]:
        """creat bridges"""
        res = []
        for bridge in connection:
            el = Bridge(self.zones(bridge["first_zone"]),
                        self.zones(bridge["destination"]),
                        bridge["optional"]["max_link_capacity"])
            res.append(el)
        return res

    def creat_drone(self, nb_drones: int) -> list[Drone]:
        """creat drones"""
        res = []
        for i in range(nb_drones):
            res.append(Drone(i, DroneState.waiting, self.zones("start_hub"),
                             self.path))
        return res
