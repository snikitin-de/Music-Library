# Исправление действия «Разложить эту запись»

Проблема была в настройках beets для веб-операций:

```yaml
copy: true
move: false
```

Из-за этого файл не переезжал в папку исполнителя и альбома.

## Что исправлено

Для действия `layout` в режиме `Реальная обработка` теперь создаётся временный конфиг:

```yaml
directory: текущая папка библиотеки из HTML-отчёта
import:
  copy: false
  move: true
  write: true
  timid: false
  resume: false
  incremental: false
  duplicate_action: skip
```

Команда `layout` запускается с `--noautotag`, то есть beets использует уже имеющиеся теги файла и раскладывает его по правилам `paths` из `beets-config.yaml`.

Например:

```yaml
paths:
  default: $albumartist/$year - $album/$track - $title
  singleton: Singles/$artist/$title
  comp: Compilations/$year - $album/$track - $title
```

## Важно

Чтобы файл разложился по исполнителю и альбому, у него должны быть заполнены теги:

- `albumartist` или `artist`;
- `album`;
- `title`.

Если альбом пустой, beets может отправить файл в `Singles/...` или использовать fallback из конфига.

## После замены файлов

Пересобери отчёт:

```bat
python scripts\generate_html_report.py --csv "reports\duplicates.csv" --library "\\TRUENAS\vault_storage\music\All music\My music\Music Test" --out "reports\duplicates.html"
```

Перезапусти сервер:

```bat
python scripts\report_server.py --open
```
