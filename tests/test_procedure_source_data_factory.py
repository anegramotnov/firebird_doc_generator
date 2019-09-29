from doc_generator.generate_doc import ProcedureSourceDataFactory


def test_procedure_source_data_factory_positive():
    data_factory = ProcedureSourceDataFactory(text="SELECT COUNT(*) FROM data_table;")

    procedure_source = data_factory.get_procedure_source_code()

    assert procedure_source.length == 32
    assert procedure_source.lower_percent == 37.5
    assert procedure_source.upper_percent == 62.5


def test_procedure_source_data_factory_empty():
    data_factory = ProcedureSourceDataFactory(text="")

    procedure_source = data_factory.get_procedure_source_code()

    assert procedure_source.length == 0
    assert procedure_source.lower_percent == 0
    assert procedure_source.upper_percent == 0
