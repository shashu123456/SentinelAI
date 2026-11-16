"""Deliberately vulnerable demo module for the kind=code (SAST) scanner.

Every function here is unsafe on purpose so the pattern scanner has obvious
sinks to find: command injection, SQL injection, unsafe deserialization,
path traversal and a hardcoded secret. Do not copy any of this into real code.
"""

import os
import pickle
import sqlite3
import subprocess

API_TOKEN = "sk-live-demo-not-a-real-key-000000"


def ping_host(host: str) -> str:
    """Command injection: an f-string is passed straight to the shell."""
    return subprocess.check_output(f"ping -c 1 {host}", shell=True).decode()


def get_user(conn: sqlite3.Connection, username: str):
    """SQL injection: user input concatenated into the query string."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = '" + username + "'")
    return cursor.fetchone()


def load_session(blob: bytes):
    """Unsafe deserialization: pickle.loads on untrusted request data."""
    return pickle.loads(blob)


def read_file(name: str) -> str:
    """Path traversal: the caller controls the path with no containment check."""
    path = os.path.join("/var/data", name)
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def run_expression(expr: str):
    """Code execution: eval on a caller-supplied string."""
    return eval(expr)
