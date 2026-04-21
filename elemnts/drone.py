from enum import Enum
from .zone import Zone
from typing import List, Optional


class DroneState(Enum):
    """drone type enum used to represent the type of drone"""
    waiting = "waiting"
    moving = "moving"
    delivered = "delivered"
    in_bridge = "in_bridge"


class Drone:
    """drone class used to represent drone in the program"""
    def __init__(self, id: int, drone_state: DroneState, current_zone: Zone):
        self.drone_id = id
        self.drone_state = drone_state
        self.current_zone = current_zone
        self.path = []
        self.path_schdl = []
        self.wait_c = 0
        self.path_index = 0

    def next_zone(self) -> Zone | None:
        """get next zone from path"""
        if self.path_index + 1 < len(self.path):
            return self.path[self.path_index + 1]
        return None

    def is_delivered(self) -> bool:
        if self.drone_state == DroneState.delivered:
            return True
        return False
