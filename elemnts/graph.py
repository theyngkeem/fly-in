from typing import Any
from .zone import Zone, Bridge
from .drone import Drone


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
        for zone in zones.keys():
            el = Zone(zone["name"], zone["optional"]["color"],
                      zone["optional"]["zone"], zone["optional"]["max_drones"],
                      True
                      if zone["name"] == ("start_hub" | "end_hub") else False,
                      zone["x"], zone["y"])
            res.append(el)
        return res

    def creat_conn(self, connection: list[dict]) -> list[Bridge]:
        """creat bridges"""
        res = []
        for bridge in connection:
            el = Bridge(bridge["first_zone"], bridge["destination"],
                        bridge["optional"]["max_link_capacity"])
            res.append(el)
        return res

    def creat_drone(self, nb_drones: int) -> list[Drone]:
        """creat drones"""
        res = []
        for i in range(nb_drones):
            res.append(Drone(i, "waiting", "start_hub", self.path))
        res
