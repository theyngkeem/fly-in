from enum import Enum
from .zone import Zone
from typing import List


class DroneState(Enum):
    """drone type enum used to represent the type of drone"""
    waiting = "waiting"
    moving = "moving"
    delivered = "delivered"
    in_bridge = "in_bridge"


class Drone:
    """drone class used to represent drone in the program"""
    def __init__(self, id: int, drone_state: DroneState, current_zone: Zone,
                 path: List[Zone]):
        self.id = id
        self.drone_type = drone_state
        self.current_zone = current_zone
        self.path = path
        self.wait_c = 0
        self.to_reach = 0
        self.path_id = 0

    def next_zone(self) -> Zone | None:
        """get next zone from path"""
        if self.path[self.path_id + 1]:
            return self.path[self.path_id + 1]
        return None

    def is_delivered(self) -> bool:
        if self.drone_type == DroneState.delivered:
            return True
        return False
