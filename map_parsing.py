from typing import Callable, Any
import re

# KEY: dict[str, Callable] = {
#     "nb_drones": lambda v: int(v),
#     "start_hub": lambda x, y: (int(x), int(y)),
#     "end_hub": lambda x, y: (int(x), int(y)),
#     "hub": lambda x, y: (int(x), int(y)),
#     "connection": lambda x, y: (int(x), int(y)),

# }


OP_KEY: dict[str, Callable] = {
    "max_drones": lambda x: int(x),
    "max_link_capacity": lambda x: int(x),
    "color": lambda v: str(v),
    "zone": lambda v: str(v)
}


ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}

ZONE_KEYS = {"max_drones", "color", "zone"}
CONN_KEYS = {"max_link_capacity"}

CHECK_KEY: list[str] = [
    "connection",
    "hub",
    "end_hub",
    "start_hub",
    "nb_drones"
]


class ParseError(Exception):
    pass


class MapParser:
    """respect OOP rule and parse the map"""
    def __init__(self, path: str):
        self.path = path
        self.nb_drones = 0
        self.coonection = []
        self.zones = {}
        self.start_hub_count = 0
        self.end_hub_count = 0
        self.current_line = 0
        self.seen_connections: set[tuple[str, str]] = set()

    def parse_map(self) -> None:
        """ignore comments and empty line"""
        with open(self.path, "r") as f:
            text = f.read()
            flag = True
            for line_num, line in enumerate(text.splitlines(), start=1):
                self.current_line = line_num
                line = line.strip()
                if line.startswith("#"):
                    continue
                if not line:
                    continue
                elif "#" in line:
                    tmp = line.split("#")
                    line = tmp[0]
                elif flag:
                    flag = False
                    if not line.startswith("nb_drones:"):
                        raise ParseError(
                            f"Line {self.current_line}: First"
                            "declaration must be nb_drones"
                        )
                self.parse_line(line)
            if self.nb_drones == 0:
                raise ParseError(f"Line {self.current_line}: Missing nb_drones"
                                 "declaration")
            if self.start_hub_count == 0:
                raise ParseError(f"Line {self.current_line}: "
                                 "No start_hub defined")
            if self.end_hub_count == 0:
                raise ParseError(f"Line {self.current_line}: "
                                 "No end_hub defined")

    def parse_line(self, line: str) -> None:
        """trait every line"""
        line_info = {}
        words = line.split()
        if not words[0].endswith(":"):
            raise ParseError(f"Line {self.current_line}: "
                             f"Invalid syntax '{words[0]}'")
        line_type = words[0][:-1]
        if line_type not in CHECK_KEY:
            raise ParseError(f"Line {self.current_line}: first word of "
                             "line must be valid")
        else:
            line_info["type"] = line_type
        if line_info["type"] == "connection":
            self.coonection.append(self.parse_connection(words[1:]))
            return
        elif line_info["type"] == "nb_drones":
            try:
                if len(words) != 2:
                    raise ParseError(f"Line {self.current_line}:"
                                     " use nb_drones: (int)")
                value = int(words[1])
            except (ValueError, TypeError):
                raise ParseError(f"Line {self.current_line}: nb_drones "
                                 "must be an integer")
            if self.nb_drones != 0:
                raise ParseError(f"Line {self.current_line}: nb_drones "
                                 "already declared")
            if value <= 0:
                raise ParseError(f"Line {self.current_line}: nb_drones "
                                 f"must be a positive integer, got '{value}'")
            self.nb_drones = value
            return
        if line_info["type"] == "start_hub":
            self.start_hub_count += 1
            if self.start_hub_count > 1:
                raise ParseError(f"Line {self.current_line}: Multiple "
                                 "start_hub definitions")
        elif line_info["type"] == "end_hub":
            self.end_hub_count += 1
            if self.end_hub_count > 1:
                raise ParseError(f"Line {self.current_line}: Multiple "
                                 "end_hub definitions")

        if len(words) < 4:
            raise ParseError(f"Line {self.current_line}: Zone requires "
                             "name, x, and y")
        line_info["name"] = words[1]
        if "-" in words[1]:
            raise ParseError(f"Line {self.current_line}: zone name cant "
                             "have - or space")
        try:
            line_info["x"] = int(words[2])
            line_info["y"] = int(words[3])
        except (ValueError, TypeError):
            raise ParseError(f"Line {self.current_line}: x and y must "
                             "be valid integers")
        if len(words) > 4:
            line_info["optional"] = self.parse_opsett(words[4:], ZONE_KEYS)
        if line_info["name"] in self.zones:
            raise ParseError(f"Line {self.current_line}: Zone "
                             f"'{line_info['name']}' "
                             "already defined")
        self.zones[line_info["name"]] = line_info

    def parse_opsett(self, words: list[str],
                     allowed_keys: set[str]) -> dict[str, Any]:
        """split optional params"""
        res = {}
        op = {}
        optional = " ".join(words)
        check = re.fullmatch(r"\[([^\]]+)\]", optional.strip())
        if not check:
            raise ParseError(f"line {self.current_line}: "
                             "probleme with optional params")
        grp = check.group(1)
        words = grp.split()
        for word in words:
            if "=" not in word:
                raise ParseError(f"Line {self.current_line}: optional params"
                                 " must be in format [key=value]")
            key, value = word.split("=", 1)
            if key in op:
                raise ParseError(
                    f"Line {self.current_line}: Duplicate metadata key '{key}'"
                )
            op[key] = value
        if "zone" in op and op["zone"] not in ZONE_TYPES:
            raise ParseError(f"Line {self.current_line}: Invalid zone "
                             f"type '{op['zone']}'")
        for key in op:
            if key not in allowed_keys:
                raise ParseError(f"Line {self.current_line}: Unknown metadata "
                                 f"key '{key}'")
        for key in allowed_keys:
            if key in op:
                try:
                    res[key] = OP_KEY[key](op[key])
                except Exception:
                    raise ParseError(
                        f"Line {self.current_line}: Invalid value for '{key}'"
                    )
            else:
                res[key] = None
        return res

    def parse_connection(self, words: list[str]) -> dict[str, Any]:
        """parse connection"""
        if not words:
            raise ParseError(
                f"Line {self.current_line}: Connection requires 'zone1-zone2'"
            )
        res = {}
        parts = words[0].split("-")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ParseError(f"Line {self.current_line}: Connection format "
                             "must be 'zone1-zone2'")
        zone1, zone2 = parts
        if zone1 == zone2:
            raise ParseError(
                f"Line {self.current_line}: Zone cannot connect to itself"
            )
        if zone1 not in self.zones or zone2 not in self.zones:
            raise ParseError(f"Line {self.current_line}: Connection must be "
                             "between existing zones")
        key = (min(zone1, zone2), max(zone1, zone2))
        if key in self.seen_connections:
            raise ParseError(
                f"Line {self.current_line}: Duplicate "
                f"connection '{zone1}-{zone2}'"
            )
        self.seen_connections.add(key)
        res["first_zone"] = zone1
        res["destination"] = zone2
        if len(words) > 1:
            res["optional"] = self.parse_opsett(words[1:], CONN_KEYS)
        return res
