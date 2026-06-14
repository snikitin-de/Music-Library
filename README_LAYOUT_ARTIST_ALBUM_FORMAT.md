# Формат раскладки

Действие `Разложить эту запись` теперь использует формат:

```text
\Исполнитель\Альбом\Исполнитель - Альбом.ext
```

Пример:

```text
Music Test\Рубеж Веков\Бабушкин компот\Рубеж Веков - Бабушкин компот.flac
```

Если исполнитель или альбом не заполнены, используются fallback-значения:

```text
Unknown Artist
Unknown Album
```

Важно: если файл с таким именем уже есть, новый файл не перезаписывается. К имени будет добавлен номер:

```text
Исполнитель - Альбом (2).flac
```

После замены файлов:

```bat
python scripts\generate_html_report.py --csv "reports\duplicates.csv" --library "\\TRUENAS\vault_storage\music\All music\My music\Music Test" --out "reports\library.html"
python scripts\report_server.py --open
```
