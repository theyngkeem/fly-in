from typing import Optional
from enum import Enum


class ZoneType(Enum):
    """zone type enum used to represent the type of zone"""
    normal = "normal"
    blocked = "blocked"
    restricted = "restricted"
    priority = "priority"


class Zone:
    """zone class used to repsenet zone in the program"""
    def __init__(self, name: str, color: Optional[str],
                 zone_type: ZoneType, capacity: int, is_srtend: str, x: int,
                 y: int):
        self.name = name
        self.color = color if color is not None else "white"
        self.zone_type = zone_type if zone_type is not None else ZoneType.normal
        self.capacity = capacity if capacity is not None else 1
        self.is_srt = True if is_srtend == "start_hub" else False
        self.is_end = True if is_srtend == "end_hub" else False
        if self.is_srt or self.is_end:
            self.capacity = 9999
        self.cost = 1 if zone_type != ZoneType.restricted else 2
        self.accecible = False if zone_type == ZoneType.blocked else True
        self.x = x
        self.y = y


class Bridge:
    """connection between zones"""
    def __init__(self, first_zone: Zone, second_zone: Zone, capacity: int = 1):
        self.first_zone = first_zone
        self.second_zone = second_zone
        self.capacity = capacity if capacity is not None else 1

    def next_zone(self, zone: Zone) -> Zone:
        """get the other zone of the bridge"""
        if zone == self.first_zone:
            return self.second_zone
        elif zone == self.second_zone:
            return self.first_zone
        else:
            raise ValueError("zone not in bridge")

    def dup_check(self) -> tuple[str, str]:
        """depass a-b b-a naming"""
        zones = sorted([self.first_zone.name, self.second_zone.name])
        return (zones[0], zones[1])
