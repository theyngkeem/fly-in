from .schedular import Scheduler
from .graph import Zone, Bridge
from .drone import DroneState
from collections import defaultdict


class Simulator:
    def __init__(self, sdl: Scheduler) -> None:
        self.turn_ev = self.turn_event(sdl)
        self.scdl = sdl

    def turn_event(self, sdl: Scheduler) -> dict:
        """read schudular"""
        res = defaultdict(list)
        for drone in sdl.stiemal_zaman:
            for i in range(len(drone.path_schdl) - 1):
                zone, turn = drone.path_schdl[i]
                next_zone, next_turn = drone.path_schdl[i + 1]
                if zone != next_zone:
                    res[turn].append((drone, zone, next_zone,
                                      (next_turn - turn)))
        return res

    def goo_goo_dolls(self) -> None:
        """run the simulator and print the result"""
        turn = 0
        while not self.check_all_delivered():
            moves = self.turn_ev.get(turn, [])
            turn += 1
            if not moves:
                continue
            output = []
            for drone, zone, to_zone, dur in moves:
                if dur == 2:
                    check = 1
                    if check == 1:
                        check = 2
                        el = f"D{drone.drone_id}-{zone.name}-{to_zone.name}"
                    else:
                        el = f"D{drone.drone_id}-{to_zone.name}"
                else:
                    el = f"D{drone.drone_id}-{to_zone.name}"
                drone.current_zone = to_zone
                if to_zone.is_end:
                    drone.drone_state = DroneState.delivered
                else:
                    drone.drone_state = DroneState.moving
                output.append(el)
            line = " ".join(output)
            print(f"{line}")
        print(f"wslat talabiya f {turn}")

    def find_con(self, zone: Zone, to_zone: Zone) -> Bridge:
        """find exact connection"""
        conn = self.scdl.graph.map[zone.name]
        for con in conn:
            check_z = con.next_zone(zone)
            if check_z == to_zone:
                return con
        raise ValueError("no connection found")

    def check_all_delivered(self) -> bool:
        """check if all drones are delivered"""
        for drone in self.scdl.stiemal_zaman:
            if not drone.is_delivered():
                return False
        return True
