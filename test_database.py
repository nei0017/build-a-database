"""Black-box tests for commands, persistence, and recovery."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import execute
from storage import Database

MAIN = Path(__file__).with_name("main.py")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)

    def commands(self, *commands):
        result = subprocess.run(
            [sys.executable, str(MAIN)],
            input="\n".join(commands) + "\n",
            cwd=self.directory,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stderr, "")
        return result.stdout.splitlines()

    def test_strings_and_restart(self):
        self.assertEqual(
            self.commands("SET a one", "SET a two", "GET a", "EXIT", "DEL a"),
            ["OK", "OK", "two"],
        )
        self.assertEqual(
            self.commands("GET a", "EXISTS a", "DEL a", "EXISTS a", "GET a"),
            ["two", "1", "1", "0", ""],
        )
        self.assertEqual(self.commands("GET a"), [""])

    def test_multi_and_ranges(self):
        self.assertEqual(
            self.commands(
                "MSET e 5 d 4 c 3 b 2 a 1",
                "MGET c a missing",
                "RANGE b d",
                'RANGE "" c',
                'RANGE d ""',
                "MSET broken",
            ),
            [
                "OK",
                "3",
                "1",
                "(nil)",
                "b",
                "c",
                "d",
                "END",
                "a",
                "b",
                "c",
                "END",
                "d",
                "e",
                "END",
                "ERR MSET requires key-value pairs",
            ],
        )

    def test_transaction_commit_abort_and_eof(self):
        self.assertEqual(
            self.commands(
                "BEGIN",
                "SET a first",
                "GET a",
                "ABORT",
                "GET a",
                "BEGIN",
                "MSET a saved b also-saved",
                "COMMIT",
                "BEGIN",
                "FLUSHDB",
                "SET c unsaved",
            ),
            ["OK", "OK", "first", "OK", "", "OK", "OK", "OK", "OK", "OK", "OK"],
        )
        self.assertEqual(self.commands("MGET a b c"), ["saved", "also-saved", "(nil)"])

    def test_hash_list_counter_and_flush(self):
        self.assertEqual(
            self.commands(
                "HSET person name Natasha",
                "HSET person major Cybersecurity",
                "LPUSH items middle",
                "RPUSH items last",
                "LPUSH items first",
                "INCR count",
                "INCR count",
                "DECR count",
            ),
            ["1", "1", "1", "2", "3", "1", "2", "1"],
        )
        self.assertEqual(
            self.commands(
                "HGET person major",
                "HGETALL person",
                "LRANGE items 0 -1",
                "LPOP items",
                "GET count",
                "FLUSHDB",
            ),
            [
                "Cybersecurity",
                "name",
                "Natasha",
                "major",
                "Cybersecurity",
                "first",
                "middle",
                "last",
                "first",
                "1",
                "OK",
            ],
        )
        self.assertEqual(self.commands('RANGE "" ""'), ["END"])

    def test_expiration_survives_restart(self):
        path = self.directory / "data.db"
        with patch("time.time", return_value=100):
            db = Database(path)
            with db.log:
                execute(db, "SET", ["a", "value"])
                self.assertEqual(execute(db, "TTL", ["a"]), [-1])
                self.assertEqual(execute(db, "EXPIRE", ["a", "10"]), [1])
        with patch("time.time", return_value=105):
            db = Database(path)
            with db.log:
                self.assertEqual(execute(db, "TTL", ["a"]), [5])
        with patch("time.time", return_value=111):
            db = Database(path)
            with db.log:
                self.assertEqual(execute(db, "GET", ["a"]), [""])
                self.assertEqual(execute(db, "TTL", ["a"]), [-2])

    def test_replay_recovers_incomplete_tail(self):
        self.commands("SET first saved")
        with (self.directory / "data.db").open("ab") as log:
            log.write(b'[["put","incomplete"')
        self.assertEqual(self.commands("GET first", "SET next valid"), ["saved", "OK"])
        self.assertEqual(
            self.commands("MGET first incomplete next"), ["saved", "(nil)", "valid"]
        )


if __name__ == "__main__":
    unittest.main()
