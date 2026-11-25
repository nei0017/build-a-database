"""Read database commands from stdin and write results to stdout."""

import math
import sys
import time

from index import Index
from storage import Database

NIL = "(nil)"
ARITIES = (
    ("SET", 2),
    ("GET", 1),
    ("EXIT", 0),
    ("DEL", 1),
    ("EXISTS", 1),
    ("EXPIRE", 2),
    ("TTL", 1),
    ("RANGE", 2),
    ("BEGIN", 0),
    ("COMMIT", 0),
    ("ABORT", 0),
    ("HSET", 3),
    ("HGET", 2),
    ("HGETALL", 1),
    ("LPUSH", 2),
    ("RPUSH", 2),
    ("LRANGE", 3),
    ("LPOP", 1),
    ("INCR", 1),
    ("DECR", 1),
    ("FLUSHDB", 0),
)


def typed_value(entry, kind, default):
    if entry is None:
        return default
    if entry[0] != kind:
        raise ValueError("wrong value type")
    return entry[1]


def string_value(db, key):
    return typed_value(db.get(key), "string", "")


def put(key, value, kind="string", deadline=None):
    return ("put", key, kind, value, deadline)


def hash_command(db, command, args, entry):
    key = args[0]
    fields = Index()
    fields.entries = typed_value(entry, "hash", []).copy()
    if command == "HSET":
        added = fields.get(args[1]) is None
        fields.put(args[1], args[2])
        db.write(put(key, fields.entries, "hash", entry[2] if entry else None))
        return [int(added)]
    if command == "HGET":
        value = fields.get(args[1])
        return [NIL if value is None else value]
    return [part for pair in fields.entries for part in pair]


def list_command(db, command, args, entry):
    key = args[0]
    values = typed_value(entry, "list", []).copy()
    deadline = entry[2] if entry else None
    if command == "LRANGE":
        start, stop = map(int, args[1:])
        size = len(values)
        start = max(0, size + start) if start < 0 else start
        stop = size + stop if stop < 0 else stop
        return values[start : stop + 1] if stop >= 0 else []
    if command == "LPOP":
        if not values:
            return [NIL]
        value = values.pop(0)
        db.write(put(key, values, "list", deadline) if values else ("delete", key))
        return [value]
    if command == "LPUSH":
        values.insert(0, args[1])
    else:
        values.append(args[1])
    db.write(put(key, values, "list", deadline))
    return [len(values)]


def execute(db, command, args):
    if command == "MSET":
        if not args or len(args) % 2:
            raise ValueError("MSET requires key-value pairs")
        db.write(*(put(key, value) for key, value in zip(args[::2], args[1::2])))
        return ["OK"]
    if command == "MGET":
        if not args:
            raise ValueError("MGET requires at least one key")
        results = []
        for key in args:
            entry = db.get(key)
            results.append(entry[1] if entry and entry[0] == "string" else NIL)
        return results
    for name, count in ARITIES:
        if name == command:
            if len(args) != count:
                raise ValueError(f"{command} requires {count} argument(s)")
            break
    else:
        raise ValueError("unknown command")

    if command == "EXIT":
        return None
    if command == "BEGIN":
        db.begin()
        return ["OK"]
    if command in ("COMMIT", "ABORT"):
        db.end(commit=command == "COMMIT")
        return ["OK"]
    if command == "FLUSHDB":
        db.write(("clear",))
        return ["OK"]
    if command == "RANGE":
        start, end = args
        keys = sorted(
            name
            for name, _ in db.index.entries
            if (start == '""' or start <= name)
            and (end == '""' or name <= end)
            and db.get(name) is not None
        )
        return [*keys, "END"]

    key = args[0]
    entry = db.get(key)
    if command == "SET":
        db.write(put(key, args[1]))
        return ["OK"]
    if command == "GET":
        return [string_value(db, key)]
    if command in ("DEL", "EXISTS"):
        if command == "DEL" and entry is not None:
            db.write(("delete", key))
        return [int(entry is not None)]
    if command == "EXPIRE":
        seconds = int(args[1])
        if entry is None:
            return [0]
        if seconds <= 0:
            db.write(("delete", key))
        else:
            db.write(put(key, entry[1], entry[0], time.time() + seconds))
        return [1]
    if command == "TTL":
        if entry is None:
            return [-2]
        if entry[2] is None:
            return [-1]
        return [math.ceil(entry[2] - time.time())]
    if command in ("INCR", "DECR"):
        current = int(typed_value(entry, "string", "0"))
        result = current + (1 if command == "INCR" else -1)
        db.write(put(key, str(result), deadline=entry[2] if entry else None))
        return [result]
    if command.startswith("H"):
        return hash_command(db, command, args, entry)
    return list_command(db, command, args, entry)


def main():
    db = Database("data.db")
    for line in sys.stdin:
        tokens = line.split()
        if not tokens:
            continue
        command, *args = tokens
        try:
            output = execute(db, command.upper(), args)
        except (ValueError, OverflowError) as error:
            output = [f"ERR {error}"]
        if output is None:
            break
        if output:
            print(*output, sep="\n", flush=True)


if __name__ == "__main__":
    main()
