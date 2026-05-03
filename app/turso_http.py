"""
turso_http.py  –  SQLAlchemy DBAPI shim for Turso using pure HTTP transport.

Why this exists
---------------
`sqlalchemy-libsql` + `libsql-experimental` connect to Turso over WebSocket
(wss://).  Vercel serverless functions block WebSocket upgrades, so every
connection attempt fails with:
    sqlite3.OperationalError: 505, message='Invalid response status'

`libsql-client` routes https:// URLs through Turso's HTTP API instead.
This module wraps `libsql-client` in a minimal sqlite3-compatible DBAPI 2.0
interface so Flask-SQLAlchemy / SQLAlchemy can use it transparently.

Usage (in app/__init__.py)
--------------------------
    from app.turso_http import build_engine
    engine = build_engine(turso_url, turso_token)
    db = SQLAlchemy(engine=engine)   # or app.config approach below
"""

from __future__ import annotations
import re
from typing import Any, Iterator, List, Optional, Sequence


# ── DBAPI 2.0 constants ───────────────────────────────────────────────────────

paramstyle = "qmark"
threadsafety = 1
apilevel = "2.0"


class Error(Exception):
    pass


class OperationalError(Error):
    pass


class DatabaseError(Error):
    pass


# ── Type objects (sqlite3 compatibility stubs) ────────────────────────────────

class _TypeObject:
    def __init__(self, *names):
        self.names = names

    def __eq__(self, other):
        return other in self.names


STRING    = _TypeObject("TEXT")
BINARY    = _TypeObject("BLOB")
NUMBER    = _TypeObject("INTEGER", "REAL")
DATETIME  = _TypeObject("TIMESTAMP", "DATETIME")
ROWID     = _TypeObject("INTEGER")


# ── Row ───────────────────────────────────────────────────────────────────────

class Row(tuple):
    """tuple subclass that also supports column-name indexing."""
    def __new__(cls, values, description):
        obj = tuple.__new__(cls, values)
        obj._description = description
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):
            for i, col in enumerate(self._description):
                if col[0] == key:
                    return tuple.__getitem__(self, i)
            raise KeyError(key)
        return tuple.__getitem__(self, key)


# ── Cursor ────────────────────────────────────────────────────────────────────

class Cursor:
    def __init__(self, client):
        self._client = client
        self.description: Optional[List] = None
        self.rowcount: int = -1
        self._rows: List[Row] = []
        self._pos: int = 0
        self.arraysize: int = 1
        self.lastrowid: Optional[int] = None

    # Convert SQLAlchemy's "?" placeholders — libsql-client wants "?" too,
    # but also accept ":name" style just in case.
    @staticmethod
    def _normalise(sql: str) -> str:
        return sql

    def execute(self, sql: str, parameters: Sequence = ()):
        sql = self._normalise(sql)
        try:
            result = self._client.execute(sql, list(parameters))
        except Exception as exc:
            raise OperationalError(str(exc)) from exc

        if result.columns:
            self.description = [
                (col, None, None, None, None, None, None)
                for col in result.columns
            ]
            self._rows = [Row(tuple(row), self.description) for row in result.rows]
        else:
            self.description = None
            self._rows = []

        self.rowcount = result.rows_affected if result.rows_affected is not None else len(self._rows)
        self.lastrowid = result.last_insert_rowid
        self._pos = 0

    def executemany(self, sql: str, seq_of_params):
        for params in seq_of_params:
            self.execute(sql, params)

    def fetchone(self) -> Optional[Row]:
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchmany(self, size: Optional[int] = None) -> List[Row]:
        size = size or self.arraysize
        rows = self._rows[self._pos: self._pos + size]
        self._pos += len(rows)
        return rows

    def fetchall(self) -> List[Row]:
        rows = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rows

    def __iter__(self) -> Iterator[Row]:
        return iter(self._rows[self._pos:])

    def close(self):
        self._rows = []
        self._pos = 0

    def setinputsizes(self, *args):
        pass

    def setoutputsize(self, *args):
        pass


# ── Connection ────────────────────────────────────────────────────────────────

class Connection:
    def __init__(self, url: str, auth_token: str):
        try:
            from libsql_client import create_client_sync
        except ImportError:
            raise ImportError(
                "libsql-client is required for Turso HTTP transport. "
                "Add `libsql-client==0.3.1` to requirements.txt"
            )
        # https:// scheme → HTTP transport (no WebSocket)
        self._client = create_client_sync(url=url, auth_token=auth_token)
        self._closed = False

    def cursor(self) -> Cursor:
        return Cursor(self._client)

    # Turso HTTP is auto-committed per statement; these are no-ops.
    def commit(self):
        pass

    def rollback(self):
        pass


    def create_function(self, name, num_params, func, **kwargs):
        # pysqlite dialect calls this to register REGEXP etc.
        # Turso does not support it — silently ignore.
        pass

    def close(self):
        if not self._closed:
            self._client.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── Module-level connect() — DBAPI 2.0 entry point ───────────────────────────

def connect(url: str, auth_token: str = "", **kwargs) -> Connection:
    return Connection(url=url, auth_token=auth_token)


# ── SQLAlchemy dialect ────────────────────────────────────────────────────────

def _register_dialect():
    """Register sqlite+tursohttp:// dialect with SQLAlchemy."""
    try:
        from sqlalchemy.dialects import registry
        from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
        from sqlalchemy import util
        from sqlalchemy.pool import NullPool
        import turso_http_dialect as _mod   # self-registration marker
    except Exception:
        pass


def build_engine(turso_url: str, auth_token: str):
    """
    Return a SQLAlchemy Engine that connects to Turso over HTTP.

    turso_url  : the TURSO_DATABASE_URL value, e.g. libsql://xxx.turso.io
    auth_token : the TURSO_AUTH_TOKEN value
    """
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import NullPool
    import turso_http as _self          # this module

    # Convert libsql:// → https:// so libsql-client uses HTTP transport
    https_url = re.sub(r'^libsql://', 'https://', turso_url)

    # Use in-memory SQLite as the "connection string" — the real connection
    # is established via the creator function below.
    def creator():
        return _self.connect(url=https_url, auth_token=auth_token)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        creator=creator,
        poolclass=NullPool,          # serverless: no persistent pool
        connect_args={},
    )
    return engine
