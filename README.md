[![Build Status](https://travis-ci.org/anegramotnov/firebird_doc_generator.svg?branch=master)](https://travis-ci.org/anegramotnov/firebird_doc_generator)
[![codecov](https://codecov.io/gh/anegramotnov/firebird_doc_generator/branch/master/graph/badge.svg)](https://codecov.io/gh/anegramotnov/firebird_doc_generator)

# Генератор документации для файлов баз данных Firebird

### Запуск:

Для переданного файла БД Firebird, генерирует HTML-документацию
со структурой и связями схемы данных в директории `dist`.

```
python run_doc_generator.py --dsn <firebird_connection_string>
```

### Тесты:
```
python -m pytest --cov
```

### Pylint
```
pylint ../firebird_doc_generatopr
```

### Flake8
```
flake8 .
```

### Интерфейс

![procedures](/images/procedures.png)

![procedure_detail](/images/procedure_detail.png)

![table_detail](/images/table_detail.png)
