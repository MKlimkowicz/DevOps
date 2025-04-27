from enum import Enum

class PSQLType(str, Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    TIMESTAMP = "TIMESTAMP"
    SERIAL = "SERIAL"
    FLOAT = "DOUBLE PRECISION"
    DATE = "DATE"


def column(name: str, type_: PSQLType, primary_key: bool = False, not_null: bool = False, default: str | None = None):
    parts = [name, type_.value]
    if primary_key:
        parts.append("PRIMARY KEY")
    if not_null:
        parts.append("NOT NULL")
    if default is not None:
        parts.append(f"DEFAULT {default}")
    return " ".join(parts) 