from typing import Any, Tuple, Union

class Vec3:
    """
    Represents a 3D Vector coordinate (X, Y, Z) with helper math operations.
    """
    def __init__(self, x: Any = 0, y: Any = 0, z: Any = 0) -> None:
        if isinstance(x, dict):
            self.x: float = float(x.get("x", 0))
            self.y: float = float(x.get("y", 0))
            self.z: float = float(x.get("z", 0))
        elif hasattr(x, "x") and hasattr(x, "y") and hasattr(x, "z"):
            self.x = float(getattr(x, "x"))
            self.y = float(getattr(x, "y"))
            self.z = float(getattr(x, "z"))
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def offset(self, dx: float, dy: float, dz: float) -> "Vec3":
        """
        Returns a new Vec3 offset from this vector.
        """
        return Vec3(self.x + dx, self.y + dy, self.z + dz)

    def __add__(self, other: Any) -> "Vec3":
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        elif isinstance(other, dict):
            return Vec3(self.x + other.get("x", 0), self.y + other.get("y", 0), self.z + other.get("z", 0))
        elif isinstance(other, (tuple, list)) and len(other) == 3:
            return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])
        return NotImplemented

    def __radd__(self, other: Any) -> "Vec3":
        return self.__add__(other)

    def __sub__(self, other: Any) -> "Vec3":
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        elif isinstance(other, dict):
            return Vec3(self.x - other.get("x", 0), self.y - other.get("y", 0), self.z - other.get("z", 0))
        elif isinstance(other, (tuple, list)) and len(other) == 3:
            return Vec3(self.x - other[0], self.y - other[1], self.z - other[2])
        return NotImplemented

    def __rsub__(self, other: Any) -> "Vec3":
        if isinstance(other, (tuple, list)) and len(other) == 3:
            return Vec3(other[0] - self.x, other[1] - self.y, other[2] - self.z)
        elif isinstance(other, dict):
            return Vec3(other.get("x", 0) - self.x, other.get("y", 0) - self.y, other.get("z", 0) - self.z)
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if not hasattr(other, 'x') or not hasattr(other, 'y') or not hasattr(other, 'z'):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __str__(self) -> str:
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def __repr__(self) -> str:
        return str(self)
