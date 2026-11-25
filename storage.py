"""Replay and durably append batches of database changes."""

import json
import os
import time

from index import Index


class Database:
    def __init__(self, path):
        self.index = Index()
        self.pending = None
        with open(path, "a+b") as log:
            log.seek(0)
            for line in log:
                if not line.endswith(b"\n"):
                    # Drop an incomplete final batch before appending again.
                    log.truncate(log.tell() - len(line))
                    log.flush()
                    os.fsync(log.fileno())
                    break
                self.apply(json.loads(line))
        self.log = open(path, "ab")

    def apply(self, changes):
        for action, *args in changes:
            if action == "put":
                key, kind, value, deadline = args
                self.index.put(key, (kind, value, deadline))
            elif action == "delete":
                self.index.delete(args[0])
            elif action == "clear":
                self.index.entries.clear()

    def append(self, changes):
        if changes:
            self.log.write(json.dumps(changes).encode("utf-8") + b"\n")
            self.log.flush()
            os.fsync(self.log.fileno())

    def write(self, *changes):
        if self.pending is None:
            self.append(changes)
        else:
            self.pending.extend(changes)
        self.apply(changes)

    def get(self, key):
        entry = self.index.get(key)
        if entry is not None:
            deadline = entry[2]
            if deadline is None or deadline > time.time():
                return entry
        return None

    def begin(self):
        if self.pending is not None:
            raise ValueError("transaction already active")
        self.saved_entries = self.index.entries.copy()
        self.pending = []

    def end(self, commit):
        if self.pending is None:
            raise ValueError("no active transaction")
        if commit:
            self.append(self.pending)
        else:
            self.index.entries = self.saved_entries
        self.pending = None
        self.saved_entries = None
