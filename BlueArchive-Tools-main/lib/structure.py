"""Store some structures."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator, Literal, overload
from urllib.parse import urljoin


# Database
@dataclass
class DBColumn:
    name: str
    data_type: str


@dataclass
class DBTable:
    name: str
    columns: list[DBColumn]
    data: list[list]


class SQLiteDataType(Enum):
    INTEGER = int
    REAL = float
    NUMERIC = float
    TEXT = str
    BLOB = bytes
    BOOLEAN = bool
    NULL = None


# Compiler
@dataclass
class Property:
    data_type: str
    name: str
    is_list: bool


@dataclass
class StructTable:
    name: str
    properties: list[Property]


@dataclass
class EnumMember:
    name: str
    value: str


@dataclass
class EnumType:
    name: str
    underlying_type: str
    members: list[EnumMember]
