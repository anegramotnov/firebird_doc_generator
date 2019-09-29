# pylint: disable=redefined-outer-name

from typing import Dict, Tuple, Callable, List, Optional
from collections import deque

import jinja2

from doc_generator.fb_gateway import FirebirdGateway
from doc_generator.models import (
    ParameterTypes,
    ObjectTypes,
    ProcedureParameter,
    ProceduresSummary,
    Dependency,
    DependentProcedure,
    DependencyTraverseTuple,
    ProcedureSource,
    Procedure,
    TablesSummary,
    Table,
    Field,
)
from doc_generator.utils import lazy_property


class ProcedureSourceDataFactory:  # pylint: disable=too-few-public-methods
    def __init__(self, text: str) -> None:
        self._text = text

    @staticmethod
    def _count(source: str, condition: Callable) -> int:
        return sum(1 for l in source if condition(l))

    @lazy_property
    def _length(self) -> int:
        return len(self._text)

    @lazy_property
    def _letters(self) -> int:
        return self._count(self._text, str.isalpha)

    @lazy_property
    def _lower(self) -> int:
        return self._count(self._text, str.islower)

    @lazy_property
    def _upper(self) -> int:
        return self._count(self._text, str.isupper)

    @lazy_property
    def _lower_percent(self) -> int:
        try:
            return self._lower / self._letters * 100
        except ZeroDivisionError:
            return 0

    @lazy_property
    def _upper_percent(self) -> int:
        try:
            return self._upper / self._letters * 100
        except ZeroDivisionError:
            return 0

    def get_procedure_source_code(self) -> ProcedureSource:
        return ProcedureSource(
            text=self._text, length=self._length, lower_percent=self._lower_percent, upper_percent=self._upper_percent
        )


class TablesDataFactory:
    FIELD_TYPE_MAP = {8: "integer", 10: "float", 14: "char", 27: "double precision", 37: "varchar({length})"}

    def __init__(self, gateway: FirebirdGateway) -> None:
        self._gateway = gateway

    def get_tables_summary(self) -> TablesSummary:
        return TablesSummary(
            total_count=self._gateway.get_tables_count().count,
            description_count=self._gateway.get_tables_description_count().count,
        )

    @classmethod
    def get_field_type(cls, field_index: int, field_length: Optional[int]) -> str:
        field_type = cls.FIELD_TYPE_MAP.get(field_index)
        return field_type.format(length=field_length) if field_type else "unknown"

    def get_tables(self) -> List[Table]:
        field_rows = self._gateway.get_fields()
        table_rows = self._gateway.get_tables()

        fields = dict()
        for field_row in field_rows:
            field = Field(
                name=field_row.name,
                type=self.get_field_type(field_row.type, field_row.length),
                description=field_row.description,
            )
            fields.setdefault(field_row.table_name, []).append(field)

        tables = []
        for table_row in table_rows:
            tables.append(Table(name=table_row.name, description=table_row.description, fields=fields[table_row.name]))

        return tables


class ProcedureDataFactory:  # pylint: disable=too-few-public-methods
    def __init__(self, gateway: FirebirdGateway) -> None:
        self._gateway = gateway

    def _get_procedures_summary(self) -> ProceduresSummary:

        return ProceduresSummary(
            total_count=self._gateway.get_procedures_count().count,
            description_count=self._gateway.get_procedures_description_count().count,
        )

    def _add_procedures_parameters(self, procedures: Dict[str, Procedure]) -> None:
        procedure_parameter_rows = self._gateway.get_procedure_parameters()

        for procedure_parameter_row in procedure_parameter_rows:
            procedure_parameter = ProcedureParameter(
                name=procedure_parameter_row.name, used=bool(procedure_parameter_row.dependency_field)
            )
            if procedure_parameter_row.type == ParameterTypes.INPUT.value:
                procedures[procedure_parameter_row.procedure_name].parameters.input.append(procedure_parameter)
            elif procedure_parameter_row.type == ParameterTypes.OUTPUT.value:
                procedures[procedure_parameter_row.procedure_name].parameters.output.append(procedure_parameter)

    def _add_procedures_dependencies(self, procedures: Dict[str, Procedure]) -> None:

        procedure_dependency_rows = self._gateway.get_procedure_dependencies()

        for procedure_dependency_row in procedure_dependency_rows:
            if ObjectTypes.has_value(procedure_dependency_row.type):
                procedure = procedures[procedure_dependency_row.procedure_name]
                if procedure_dependency_row.type == ObjectTypes.TABLE.value:
                    procedure.dependencies.table.append(Dependency(name=procedure_dependency_row.name))
                elif procedure_dependency_row.type == ObjectTypes.PROCEDURE.value:
                    procedure.dependencies.procedure.append(procedures[procedure_dependency_row.name])
                elif procedure_dependency_row.type == ObjectTypes.UDF.value:
                    procedure.dependencies.udf.append(Dependency(name=procedure_dependency_row.name))

    def _get_procedures(self) -> Dict[str, Procedure]:
        procedure_rows = self._gateway.get_procedures()
        procedures = dict()
        for procedure_row in procedure_rows:
            procedures[procedure_row.name] = Procedure(
                name=procedure_row.name,
                description=procedure_row.description,
                source=ProcedureSourceDataFactory(text=procedure_row.source).get_procedure_source_code(),
            )
        return procedures

    @staticmethod
    def _add_dependency_procedures_tree(procedure: Procedure, max_depth: int = 5) -> None:
        dependency_queue = deque()
        dependency_passed = {procedure.name}
        # TODO: mode=(write|count), чтобы можно было продолжать считать без записи в dict, только для статистики
        # TODO: Подумать еще про циклы (которые считать не надо). Наверное, хватит просто отдельного списка
        dependency_queue += [
            DependencyTraverseTuple(
                dependency=dependency_procedure, tree=procedure.dependency_tree, passed=dependency_passed, depth=0
            )
            for dependency_procedure in procedure.dependencies.procedure
        ]

        unique_procedures = set()
        tree_degree = 0

        while dependency_queue:
            traverse = dependency_queue.popleft()

            unique_procedures.add(traverse.dependency.name)

            # Зависимость встречалась ранее в ветке
            if traverse.dependency.name in traverse.passed:
                # TODO: вероятно, стоит сразу помечать заведомо циклические процедуры и кешировать,
                # TODO: но проверку отключать нельзя - может быть цикл в конкретной ветке

                cycled_dependent = DependentProcedure(name=traverse.dependency.name, is_cycled=True)
                traverse.tree.append(cycled_dependent)
            # Превышает максимально отображаемую глубину зависимостей
            elif traverse.depth >= max_depth - 1 and traverse.dependency.dependencies.procedure:
                depth_limited_dependent = DependentProcedure(name=traverse.dependency.name, in_depth_limit=True)
                traverse.tree.append(depth_limited_dependent)
            # лист дерева
            elif not traverse.dependency.dependencies.procedure:
                tree_degree += 1
                dangling_dependent = DependentProcedure(name=traverse.dependency.name)
                traverse.tree.append(dangling_dependent)
            else:
                tree_degree += 1
                next_passed = traverse.passed.union({traverse.dependency.name})
                subtree_root = DependentProcedure(name=traverse.dependency.name)
                traverse.tree.append(subtree_root)
                next_depth = traverse.depth + 1
                for next_dependency_procedure in traverse.dependency.dependencies.procedure:
                    dependency_queue.append(
                        DependencyTraverseTuple(
                            dependency=next_dependency_procedure,
                            tree=subtree_root.dependency_tree,
                            passed=next_passed,
                            depth=next_depth,
                        )
                    )

    def _add_dependency_trees(self, procedures: Dict[str, Procedure]) -> None:
        for procedure in procedures.values():
            self._add_dependency_procedures_tree(procedure)

    def get_data(self) -> Tuple[ProceduresSummary, Dict[str, Procedure]]:
        # TODO: внутри представлять в виде dict, но возвращать лучше list
        procedures_summary = self._get_procedures_summary()
        procedures = self._get_procedures()
        self._add_procedures_parameters(procedures)
        self._add_procedures_dependencies(procedures)
        self._add_dependency_trees(procedures)
        return procedures_summary, procedures


env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("doc_generator/template"),  # pylint: disable=invalid-name
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_to_file(template: str, output_file: str, *args, **kwargs):
    template = env.get_template(template)
    output = template.render(*args, **kwargs)

    with open(f"dist/{output_file}", "w", encoding="utf-8") as out:
        out.write(output)
