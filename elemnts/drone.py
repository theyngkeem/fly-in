from enum import Enum
from .zone import Zone
from typing import Any


class DroneState(Enum):
    """drone type enum used to represent the type of drone"""
    waiting = "waiting"
    moving = "moving"
    delivered = "delivered"
    in_bridge = "in_bridge"


class Drone:
    """drone class used to represent drone in the program"""
    def __init__(self, id: int, drone_state: DroneState,
                 current_zone: Zone | None):
        self.drone_id = id
        self.drone_state = drone_state
        self.current_zone = current_zone
        self.path: list = []
        self.path_schdl: list = []
        self.wait_c = 0
        self.path_index = 0

    def next_zone(self) -> Any:
        """get next zone from path"""
        if self.path_index + 1 < len(self.path):
            return self.path[self.path_index + 1]
        return None

    def is_delivered(self) -> bool:
        "checking if the drone is deliveed"
        if self.drone_state == DroneState.delivered:
            return True
        return False
