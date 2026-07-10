from typing import Any

class Block:
    """
    Represents a Minecraft block with a name and a position coordinate.
    """
    def __init__(self, name: str, position: Any) -> None:
        self.name: str = name
        self.position: Any = position

    def __repr__(self) -> str:
        return f"Block({self.name}, {self.position})"
