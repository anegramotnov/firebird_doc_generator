import jinja2
import argparse

from doc_generator.my_logging import Logger
from doc_generator.fb_gateway import FirebirdGateway
from doc_generator.generate_doc import (
    ProcedureDataFactory,
    TablesDataFactory,
    render_to_file,
)


logger = Logger()  # pylint: disable=invalid-name

if __name__ == "__main__":
    # pylint: disable=invalid-name, redefined-outer-name

    argument_parser = argparse.ArgumentParser(
        description="Генератор HTML-документации для схемы данных из FDB-файла"
    )
    argument_parser.add_argument('-dsn', '--data_source_name', required=True, type=str)
    argument_parser.add_argument('-u', '--user', type=str, default='sysdba')
    argument_parser.add_argument('-p', '--password', type=str, default='masterkey')
    argument_parser.add_argument('-c', '--charset', type=str, default='UTF8')

    args = argument_parser.parse_args()

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("template"), trim_blocks=True, lstrip_blocks=True
    )
    gateway = FirebirdGateway(
        dsn=args.data_source_name,
        user=args.user,
        password=args.password,
        charset=args.charset,
    )
    procedures_summary, procedures = ProcedureDataFactory(gateway=gateway).get_data()

    tables_data_factory = TablesDataFactory(gateway=gateway)
    tables_summary = tables_data_factory.get_tables_summary()
    tables = tables_data_factory.get_tables()

    logger.log("generate html...")

    render_to_file(template="index.html", output_file="index.html")
    render_to_file(
        template="procedures.html",
        output_file="procedures.html",
        procedures=procedures,
        procedures_summary=procedures_summary,
    )
    render_to_file(
        template="tables.html",
        output_file="tables.html",
        tables=tables,
        tables_summary=tables_summary,
    )
    for procedure_name, procedure in procedures.items():
        render_to_file(
            template="procedure.html",
            output_file=f"procedure-{procedure_name}.html",
            procedure=procedure,
        )

    for table in tables:
        render_to_file(
            template="table.html", output_file=f"table-{table.name}.html", table=table
        )
