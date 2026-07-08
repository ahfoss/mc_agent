class Block:
    def __init__(self, name, position):
        self.name = name
        self.position = position

    def __repr__(self):
        return f"Block({self.name}, {self.position})"
