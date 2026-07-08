from core.utils.vec3 import Vec3

class SidecarEntityEmulator:
    def __init__(self, parent):
        self.parent = parent

    @property
    def position(self):
        return self.parent.position

class PlayersDict(dict):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def __getitem__(self, key):
        pos = self.parent.find_player(key)
        if pos is None:
            return None
        class PlayerMock:
            class EntityMock:
                def __init__(self, p):
                    self.position = p
            def __init__(self, p):
                self.entity = self.EntityMock(p)
        return PlayerMock(pos)

class RegistryItem:
    def __init__(self, name, id_val):
        self.name = name
        self.id = id_val

class RegistryEmulator:
    def __init__(self, items_by_name, blocks_by_name):
        self.itemsByName = items_by_name
        self.blocksByName = blocks_by_name
