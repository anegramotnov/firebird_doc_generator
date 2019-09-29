from dataclasses import dataclass
from typing import Optional
from doc_generator.models import ObjectTypes, ParameterTypes


@dataclass
class CountRow:
    """
    Результат выборки количества сущностей
    """

    count: int


@dataclass
class ProcedureRow:
    """
    Результата выборки процедур
    """

    name: str
    description: str
    source: str


@dataclass
class ProcedureParameterRow:
    """
    Результат выборки параметров сущностей
    """

    procedure_name: str
    dependency_field: Optional[str]
    name: str
    type: ParameterTypes


@dataclass
class ProcedureDependencyRow:
    """
    Результат выборки зависимостей процедуры
    """

    procedure_name: str
    name: str
    field: str
    type: ObjectTypes


@dataclass
class TableRow:
    """
    Результат выборки таблиц
    """

    name: str
    description: str


@dataclass
class FieldRow:
    """
    Результат выборки полей таблиц
    """

    table_name: str
    name: str
    type: int
    length: int
    description: Optional[str]
