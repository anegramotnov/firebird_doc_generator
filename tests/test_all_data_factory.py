import pytest
from unittest.mock import MagicMock

from doc_generator.fb_gateway import FirebirdGateway
from doc_generator.fb_row_models import (
    ProcedureRow,
    CountRow,
    ProcedureParameterRow,
    ProcedureDependencyRow,
)
from doc_generator.models import Procedure, DependentProcedure
from doc_generator.generate_doc import ProcedureDataFactory


@pytest.fixture()
def procedures_summary():
    gateway = FirebirdGateway("", "", "", "")

    gateway.get_procedures_count = MagicMock(return_value=CountRow(count=10))
    gateway.get_procedures_description_count = MagicMock(return_value=CountRow(count=5))

    all_data_factory = ProcedureDataFactory(gateway=gateway)

    all_data_factory._get_procedures = MagicMock()
    all_data_factory._add_procedures_parameters = MagicMock()
    all_data_factory._add_procedures_dependencies = MagicMock()
    all_data_factory._add_dependency_trees = MagicMock()

    _procedures_summary, _ = all_data_factory.get_data()

    return _procedures_summary


def test_procedures_summary(procedures_summary):
    assert procedures_summary.total_count == 10
    assert procedures_summary.description_count == 5


@pytest.fixture()
def procedures():
    fixture_procedures = [
        ProcedureRow(name="PROCEDURE1", description=None, source="AaBb.."),
        ProcedureRow(name="PROCEDURE2", description="description", source=""),
    ]

    gateway = FirebirdGateway("", "", "", "")

    gateway.get_procedures = MagicMock(side_effect=lambda: fixture_procedures)
    all_data_factory = ProcedureDataFactory(gateway=gateway)

    all_data_factory._get_procedures_summary = MagicMock()
    all_data_factory._add_procedures_parameters = MagicMock()
    all_data_factory._add_procedures_dependencies = MagicMock()
    all_data_factory._add_dependency_trees = MagicMock()

    _, _procedures = all_data_factory.get_data()

    return _procedures


def test_get_procedures(procedures):
    assert len(procedures) == 2
    assert set(procedures.keys()) == {"PROCEDURE1", "PROCEDURE2"}

    first_procedure = procedures["PROCEDURE1"]
    assert first_procedure.name == "PROCEDURE1"
    assert first_procedure.description is None
    assert first_procedure.source.text == "AaBb.."

    second_procedure = procedures["PROCEDURE2"]
    assert second_procedure.name == "PROCEDURE2"
    assert second_procedure.description == "description"
    assert second_procedure.source.text == ""


@pytest.fixture()
def procedures_with_parameters(procedures):
    fixture_parameters = [
        ProcedureParameterRow(
            procedure_name="PROCEDURE1",
            dependency_field=None,
            name="PARAMETER1",
            type=0,
        ),
        ProcedureParameterRow(
            procedure_name="PROCEDURE1",
            dependency_field="FIELD1",
            name="PARAMETER2",
            type=1,
        ),
        ProcedureParameterRow(
            procedure_name="PROCEDURE2",
            dependency_field=None,
            name="PARAMETER3",
            type=0,
        ),
        ProcedureParameterRow(
            procedure_name="PROCEDURE2",
            dependency_field=None,
            name="PARAMETER4",
            type=1,
        ),
    ]

    gateway = FirebirdGateway("", "", "", "")

    gateway.get_procedure_parameters = MagicMock(side_effect=lambda: fixture_parameters)

    all_data_factory = ProcedureDataFactory(gateway=gateway)

    all_data_factory._add_procedures_parameters(procedures)

    return procedures


def test_add_procedures_parameters(procedures_with_parameters):
    first_procedure = procedures_with_parameters["PROCEDURE1"]
    assert len(first_procedure.parameters.input) == 1
    assert len(first_procedure.parameters.output) == 1
    assert first_procedure.parameters.input[0].name == "PARAMETER1"
    assert first_procedure.parameters.output[0].name == "PARAMETER2"
    assert first_procedure.parameters.output[0].used is True

    second_procedure = procedures_with_parameters["PROCEDURE2"]
    assert len(second_procedure.parameters.input) == 1
    assert len(second_procedure.parameters.output) == 1
    assert second_procedure.parameters.input[0].name == "PARAMETER3"
    assert second_procedure.parameters.output[0].name == "PARAMETER4"
    assert second_procedure.parameters.output[0].used is False


@pytest.fixture()
def procedures_with_dependencies(procedures):
    procedures["PROCEDURE5"] = Procedure(name="PROCEDURE5", description=None, source="")
    procedures["PROCEDURE6"] = Procedure(name="PROCEDURE6", description=None, source="")

    fixture_dependencies = [
        ProcedureDependencyRow(
            procedure_name="PROCEDURE1", name="PROCEDURE5", field="", type=5
        ),
        ProcedureDependencyRow(
            procedure_name="PROCEDURE1", name="TABLE1", field="", type=0
        ),
        ProcedureDependencyRow(
            procedure_name="PROCEDURE1", name="UDF1", field="", type=15
        ),
        ProcedureDependencyRow(
            procedure_name="PROCEDURE1", name="PROCEDURE6", field="", type=5
        ),
        ProcedureDependencyRow(
            procedure_name="PROCEDURE2", name="PROCEDURE2", field="", type=5
        ),
        ProcedureDependencyRow(
            procedure_name="PROCEDURE2", name="PROCEDURE1", field="", type=5
        ),
    ]

    gateway = FirebirdGateway("", "", "", "")

    gateway.get_procedure_dependencies = MagicMock(
        side_effect=lambda: fixture_dependencies
    )

    all_data_factory = ProcedureDataFactory(gateway=gateway)

    all_data_factory._add_procedures_dependencies(procedures)

    return procedures


def test_add_procedures_dependencies(procedures_with_dependencies):
    first_procedure = procedures_with_dependencies["PROCEDURE1"]
    assert len(first_procedure.dependencies.procedure) == 2
    assert len(first_procedure.dependencies.table) == 1
    assert len(first_procedure.dependencies.udf) == 1
    assert sorted(
        procedure.name for procedure in first_procedure.dependencies.procedure
    ) == sorted(["PROCEDURE5", "PROCEDURE6"])
    assert first_procedure.dependencies.table[0].name == "TABLE1"
    assert first_procedure.dependencies.udf[0].name == "UDF1"

    second_procedure = procedures_with_dependencies["PROCEDURE2"]
    assert len(second_procedure.dependencies.procedure) == 2
    assert len(second_procedure.dependencies.table) == 0
    assert len(second_procedure.dependencies.udf) == 0
    assert sorted(
        procedure.name for procedure in second_procedure.dependencies.procedure
    ) == sorted(["PROCEDURE1", "PROCEDURE2"])


@pytest.fixture()
def procedures_with_dependency_tree(procedures_with_dependencies):
    gateway = FirebirdGateway("", "", "", "")

    all_data_factory = ProcedureDataFactory(gateway=gateway)
    all_data_factory._add_dependency_trees(procedures_with_dependencies)

    return procedures_with_dependencies


def test_add_dependency_tree(procedures_with_dependency_tree):
    reference_first_tree = [
        DependentProcedure(name="PROCEDURE5"),
        DependentProcedure(name="PROCEDURE6"),
    ]

    first_procedure = procedures_with_dependency_tree["PROCEDURE1"]

    assert first_procedure.dependency_tree == reference_first_tree

    reference_second_tree = [
        DependentProcedure(name="PROCEDURE2", is_cycled=True),
        DependentProcedure(
            name="PROCEDURE1",
            dependency_tree=[
                DependentProcedure(name="PROCEDURE5"),
                DependentProcedure(name="PROCEDURE6"),
            ],
        ),
    ]

    second_procedure = procedures_with_dependency_tree["PROCEDURE2"]

    assert second_procedure.dependency_tree == reference_second_tree
