from typing import Any, Dict
from core.utils.vec3 import Vec3

class SidecarEntityEmulator:
    """
    Emulates a sidecar entity, delegating position checks to a parent object.
    """
    def __init__(self, parent: Any) -> None:
        self.parent: Any = parent

    @property
    def position(self) -> Vec3:
        return self.parent.position


class PlayersDict(dict):
    """
    A custom dictionary class that queries players dynamically from a parent bot.
    """
    def __init__(self, parent: Any) -> None:
        super().__init__()
        self.parent: Any = parent

    def __getitem__(self, key: str) -> Any:
        pos = self.parent.find_player(key)
        if pos is None:
            return None
        class PlayerMock:
            class EntityMock:
                def __init__(self, p: Vec3) -> None:
                    self.position: Vec3 = p
            def __init__(self, p: Vec3) -> None:
                self.entity: PlayerMock.EntityMock = self.EntityMock(p)
        return PlayerMock(pos)


class RegistryItem:
    """
    Represents an item or block registry entry with a name and numerical ID.
    """
    def __init__(self, name: str, id_val: int) -> None:
        self.name: str = name
        self.id: int = id_val


class RegistryEmulator:
    """
    Emulates the Minecraft item/block registry for namespace lookups.
    """
    def __init__(self, items_by_name: Dict[str, RegistryItem], blocks_by_name: Dict[str, RegistryItem]) -> None:
        self.itemsByName: Dict[str, RegistryItem] = items_by_name
        self.blocksByName: Dict[str, RegistryItem] = blocks_by_name
