"""Small linear index shared by database keys and hash fields."""


class Index:
    def __init__(self):
        self.entries = []

    def get(self, key):
        for name, value in self.entries:
            if name == key:
                return value
        return None

    def put(self, key, value):
        for position, (name, _) in enumerate(self.entries):
            if name == key:
                self.entries[position] = (key, value)
                return
        self.entries.append((key, value))

    def delete(self, key):
        for position, (name, _) in enumerate(self.entries):
            if name == key:
                del self.entries[position]
                return
