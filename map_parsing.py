from typing import Callable, Any


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
    "color": lambda v : str(v),
    "zone": lambda v : str(v)
}


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
        self.graph = set()
        self.nb_drones = 0
        self.coonection = {}
        self.zones = {}

    def parse_map(self):
        """ignore comments and empty line"""
        with open(self.path, "r") as f:
            text = f.read()
            flag = True
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                elif "#" in line:
                    raise ParseError("line has '#' but doesnt start with it")
                elif flag:
                    flag = False
                    if "nb_drones" not in line:
                        raise ParseError("first non comment line must be nb_drones")
                self.parse_line(line)

    def parse_line(self, line:str) -> None:
        """trait every line"""
        line_info = {}
        words = line.split()
        if words[0].rstrip(":") not in CHECK_KEY:
            raise ParseError("first word of line must be valid")
        else:
            line_info["type"] = words[0].rstrip(":")
        if line_info["type"] == "connection":
            self.coonection.update(self.parse_connection(words[1:]))
            return
        elif line_info["type"] == "nb_drones":
            try:
                self.nb_drones = int(words[1])
                return
            except (ValueError, TypeError):
                raise ParseError("nb_drones must be a integer")
        else:
            line_info["name"] = words[1]
            try:
                line_info["x"] = int(words[2])
                line_info["y"] = int(words[3])
            except (ValueError, TypeError):
                raise ParseError("x and y must be valid integers")
            if words[4]:
                line_info["optional"] = self.parse_opsett(words[4:])
            self.zones.update(line_info)


    def parse_opsett(words: list[str]) -> dict[str, Any]:
        """split optional params"""
        res = {}
        op = {}
        for word in words:
            word = word.strip("[]")
            key, value = word.split("=")
            op[key] = value

        for key, cnv in OP_KEY.items():
            if key not in op.keys():
                res[key] = None
            try:
                res[key] = cnv(op[key])
            except Exception:
                raise ParseError("value of optional param isnt correct")
        return res

    def parse_connection(self, words: list[str]) -> dict[str, Any]:
        """parse connection"""
        res = {}
        res["first_zone"], res["destination"] = words[0].split("-")
        if words[1]:
            res["optional"] = self.parse_opsett(words[1:])
        return res
