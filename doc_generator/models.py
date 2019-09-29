from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, NamedTuple, Set, Dict, Optional


class ParameterTypes(enum.Enum):
    INPUT = 0
    OUTPUT = 1


class ObjectTypes(enum.Enum):
    """
    Типы объектов в Firebird
    """

    TABLE = 0
    TRIGGER = 2
    PROCEDURE = 5
    UDF = 15

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)


@dataclass
class ProcedureParameter:
    """
    Параметр процедуры (входной или выходной)
    """

    name: str
    used: bool = False


@dataclass
class ProcedureParameters:
    input: List[ProcedureParameter] = field(default_factory=list)
    output: List[ProcedureParameter] = field(default_factory=list)


@dataclass
class ProceduresSummary:
    """
    Общая информация о процедурах
    """

    total_count: int
    description_count: int


@dataclass
class TablesSummary:
    total_count: int
    description_count: int


@dataclass
class Dependency:
    name: str


@dataclass
class Dependencies:
    table: List[Dependency] = field(default_factory=list)
    trigger: List[Dependency] = field(default_factory=list)
    procedure: List[Procedure] = field(default_factory=list)  # pylint: disable=used-before-assignment
    index: List[Dependency] = field(default_factory=list)
    udf: List[Dependency] = field(default_factory=list)


# TODO: бред какой-то с неймингом: то dependent, то dependency_tree
@dataclass
class DependentProcedure:
    name: str
    is_cycled: bool = False
    in_depth_limit: bool = False
    dependency_tree: List[DependentProcedure] = field(default_factory=list)  # pylint: disable=undefined-variable


class DependencyTraverseTuple(NamedTuple):
    """
    Служебная структура для обхода зависимостей и построения дерева зависимостей
    """

    dependency: Procedure
    tree: List[DependentProcedure]
    passed: Set[str]
    depth: int


@dataclass
class ProcedureSource:
    text: str
    length: int
    lower_percent: int
    upper_percent: int


@dataclass
class Procedure:
    name: str
    description: Optional[str]
    source: ProcedureSource
    dependencies: Dependencies = field(default_factory=Dependencies)
    parameters: ProcedureParameters = field(default_factory=ProcedureParameters)
    _dependency_field_map: Dict[str, List[str]] = field(default_factory=dict)
    dependency_tree: List[DependentProcedure] = field(default_factory=list)


@dataclass
class Field:
    name: str
    type: str
    description: Optional[str]


@dataclass
class Table:
    name: str
    description: Optional[str]
    fields: List[Field] = field(default_factory=list)
