from typing import Optional, Dict, Tuple, List, Any, Union, Iterator, Callable, Generator, Type
from functools import wraps
import itertools

import copy

import fdb

from doc_generator import my_logging
from doc_generator.fb_row_models import (
    ProcedureParameterRow,
    ProcedureRow,
    ProcedureDependencyRow,
    CountRow,
    TableRow,
    FieldRow,
)


logger = my_logging.Logger()  # pylint: disable=invalid-name


def with_caching(logging: bool = False) -> Callable:
    cache = {}

    def with_caching_decorator(method: Callable) -> Callable:
        @wraps(method)
        def with_caching_wrapper(self, *method_args: List[Any], **method_kwargs: Dict[str, Any]) -> Any:
            Tee: Type = itertools.tee([], 1)[0].__class__  # pylint: disable=invalid-name

            if logging:
                log = logger.log
            else:

                def log(*args, **kwargs):  # pylint: disable=unused-argument
                    pass

            def get_double(original: Any) -> Tuple[Any, Any]:
                if isinstance(original, (Generator, Tee)):
                    return original, itertools.tee(original, 1)[0]
                else:
                    return original, copy.deepcopy(original)

            formatted_args = ", ".join(method_args)
            log(f"Call {self.__class__.__name__}.{method.__name__}({formatted_args})")

            try:
                original, double = get_double(cache[method_args])
                log(f"get result from cache")
                return double
            except KeyError:
                log(f"execute {method.__name__}...")
                original, double = get_double(method(self, *method_args, **method_kwargs))
                cache[method_args] = original
                return double

        return with_caching_wrapper

    return with_caching_decorator


class FirebirdGateway:
    _cursor: Optional[fdb.Cursor] = None

    def __init__(self, dsn: str, user: str, password: str, charset: str = "UTF8") -> None:
        self._dsn = dsn
        self._user = user
        self._password = password
        self._charset = charset

    @staticmethod
    def _get_normalized_str_or_none(source: Optional[str]) -> Optional[str]:
        """
        Обрезание лишних пробелов, которые зачем-то возвращаются из Firebird в названиях процедур, полей и т.д.
        """
        return source.strip() if source else source

    def _get_cursor(self) -> fdb.Cursor:
        if not self._cursor:
            connection = fdb.connect(dsn=self._dsn, user=self._user, password=self._password, charset=self._charset)
            self._cursor = connection.cursor()

        return self._cursor

    @with_caching()
    def get_procedures_count(self) -> CountRow:
        query = """
select count(*) from RDB$PROCEDURES;
        """
        cursor = self._get_cursor().execute(query)
        row = cursor.fetchonemap()

        return CountRow(count=row["COUNT"])

    @with_caching()
    def get_procedures_description_count(self) -> CountRow:
        query = """
select count(*) from RDB$PROCEDURES where RDB$DESCRIPTION is not null;
        """
        cursor = self._get_cursor().execute(query)
        row = cursor.fetchonemap()

        return CountRow(count=row["COUNT"])

    @with_caching()
    def get_tables_count(self) -> CountRow:
        query = """
select count(*)
from rdb$relations
where rdb$view_blr is null
and (rdb$system_flag is null or rdb$system_flag = 0);
            """
        cursor = self._get_cursor().execute(query)
        row = cursor.fetchonemap()

        return CountRow(count=row["COUNT"])

    @with_caching()
    def get_tables_description_count(self) -> CountRow:
        query = """
select count(*)
from rdb$relations
where rdb$view_blr is null
and (rdb$system_flag is null or rdb$system_flag = 0)
and not rdb$description is null;
        """
        cursor = self._get_cursor().execute(query)
        row = cursor.fetchonemap()

        return CountRow(count=row["COUNT"])

    @with_caching(logging=True)
    def get_procedures(self) -> Iterator[ProcedureRow]:
        query = """
select
    pr.RDB$PROCEDURE_NAME,
    pr.RDB$DESCRIPTION,
    pr.RDB$PROCEDURE_SOURCE
    from RDB$PROCEDURES as pr
;
        """
        cursor = self._get_cursor().execute(query)
        for row in cursor.itermap():
            procedure = ProcedureRow(
                name=self._get_normalized_str_or_none(row["RDB$PROCEDURE_NAME"]),
                description=row["RDB$DESCRIPTION"],
                source=row["RDB$PROCEDURE_SOURCE"],
            )
            yield procedure

    @with_caching(logging=True)
    def get_procedure_parameters(self) -> Iterator[ProcedureParameterRow]:
        query = """
select
    distinct
    pr.RDB$PROCEDURE_NAME,
    pp.RDB$PARAMETER_NAME,
    pp.RDB$PARAMETER_TYPE,
    pd.RDB$FIELD_NAME as DEPENDENCY_FIELD
    from RDB$PROCEDURES as pr
    left join RDB$PROCEDURE_PARAMETERS as pp on pp.RDB$PROCEDURE_NAME = pr.RDB$PROCEDURE_NAME
    left join rdb$dependencies as pd on
        pd.RDB$DEPENDED_ON_NAME = pr.RDB$PROCEDURE_NAME
        and pd.RDB$FIELD_NAME = pp.RDB$PARAMETER_NAME
    where pp.RDB$PARAMETER_TYPE is not null
;
        """

        cursor = self._get_cursor().execute(query)
        for row in cursor.itermap():
            parameter = ProcedureParameterRow(
                procedure_name=self._get_normalized_str_or_none(row["RDB$PROCEDURE_NAME"]),
                name=self._get_normalized_str_or_none(row["RDB$PARAMETER_NAME"]),
                type=row["RDB$PARAMETER_TYPE"],
                dependency_field=self._get_normalized_str_or_none(row["DEPENDENCY_FIELD"]),
            )
            yield parameter

    @with_caching(logging=True)
    def get_procedure_dependencies(self) -> Iterator[ProcedureDependencyRow]:
        query = """
select
    dp.RDB$DEPENDENT_NAME,
    dp.RDB$DEPENDED_ON_NAME,
    dp.RDB$FIELD_NAME,
    dp.RDB$DEPENDED_ON_TYPE
    from RDB$DEPENDENCIES as dp
    where
        dp.RDB$DEPENDENT_TYPE = 5
        and dp.RDB$DEPENDED_ON_TYPE in (0, 2, 5, 15)
        and dp.RDB$FIELD_NAME is null
;
        """
        cursor = self._get_cursor().execute(query)
        for row in cursor.itermap():
            procedure_dependency = ProcedureDependencyRow(
                procedure_name=self._get_normalized_str_or_none(row["RDB$DEPENDENT_NAME"]),
                name=self._get_normalized_str_or_none(row["RDB$DEPENDED_ON_NAME"]),
                type=row["RDB$DEPENDED_ON_TYPE"],
                field=row["RDB$FIELD_NAME"],
            )
            yield procedure_dependency

    @with_caching(logging=True)
    def get_dependency_procedures_with_fields(self) -> Iterator[Dict[str, Union[str, int]]]:
        query = """
select
    dp.RDB$DEPENDENT_NAME,
    dp.RDB$DEPENDED_ON_NAME,
    dp.RDB$FIELD_NAME
    from RDB$DEPENDENCIES as dp
    where
        dp.RDB$DEPENDENT_TYPE = 5
        and dp.RDB$DEPENDED_ON_TYPE = 5
        and dp.RDB$FIELD_NAME is not null
;
        """
        cursor = self._get_cursor().execute(query)
        for row in cursor.itermap():
            procedure = ProcedureRow(
                name=self._get_normalized_str_or_none(row["RDB$PROCEDURE_NAME"]),
                description=row["RDB$DESCRIPTION"],
                source=row["RDB$PROCEDURE_SOURCE"],
            )
            yield procedure

    @with_caching()
    def get_tables(self) -> Iterator[TableRow]:
        query = """
select rdb$relation_name, rdb$description
from rdb$relations
where rdb$view_blr is null
and (rdb$system_flag is null or rdb$system_flag = 0);
        """
        cursor = self._get_cursor().execute(query)
        for row in cursor.itermap():
            table = TableRow(name=row["rdb$relation_name"], description=row["rdb$description"])
            yield table

    @with_caching()
    def get_fields(self) -> Iterator[FieldRow]:
        query = """
select r.rdb$relation_name, rf.rdb$field_name, rf.rdb$description, f.rdb$field_type, f.rdb$field_length
from rdb$relations as r
left join rdb$relation_fields as rf on r.rdb$relation_name = rf.rdb$relation_name
left join rdb$fields as f on f.rdb$field_name = rf.rdb$field_source
where r.rdb$view_blr is null
and (r.rdb$system_flag is null or r.rdb$system_flag = 0)
order by rf.rdb$field_position;
        """
        cursor = self._get_cursor().execute(query)
        for row in cursor.itermap():
            table = FieldRow(
                table_name=row["rdb$relation_name"],
                name=row["rdb$field_name"],
                description=row["rdb$description"],
                type=row["rdb$field_type"],
                length=row["rdb$field_length"],
            )
            yield table
