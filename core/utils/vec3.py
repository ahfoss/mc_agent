class Vec3:
    def __init__(self, x=0, y=0, z=0):
        if isinstance(x, dict):
            self.x = float(x.get("x", 0))
            self.y = float(x.get("y", 0))
            self.z = float(x.get("z", 0))
        elif hasattr(x, "x") and hasattr(x, "y") and hasattr(x, "z"):
            self.x = float(getattr(x, "x"))
            self.y = float(getattr(x, "y"))
            self.z = float(getattr(x, "z"))
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def offset(self, dx, dy, dz):
        return Vec3(self.x + dx, self.y + dy, self.z + dz)

    def __add__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        elif isinstance(other, dict):
            return Vec3(self.x + other.get("x", 0), self.y + other.get("y", 0), self.z + other.get("z", 0))
        elif isinstance(other, (tuple, list)) and len(other) == 3:
            return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        elif isinstance(other, dict):
            return Vec3(self.x - other.get("x", 0), self.y - other.get("y", 0), self.z - other.get("z", 0))
        elif isinstance(other, (tuple, list)) and len(other) == 3:
            return Vec3(self.x - other[0], self.y - other[1], self.z - other[2])
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, (tuple, list)) and len(other) == 3:
            return Vec3(other[0] - self.x, other[1] - self.y, other[2] - self.z)
        elif isinstance(other, dict):
            return Vec3(other.get("x", 0) - self.x, other.get("y", 0) - self.y, other.get("z", 0) - self.z)
        return NotImplemented

    def __eq__(self, other):
        if not hasattr(other, 'x') or not hasattr(other, 'y') or not hasattr(other, 'z'):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __str__(self):
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def __repr__(self):
        return str(self)
