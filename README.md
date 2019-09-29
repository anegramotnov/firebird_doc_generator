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
