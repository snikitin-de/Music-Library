# Music Library Agent

Набор файлов для безопасной обработки музыкальной библиотеки через `beets` и вспомогательные скрипты.

## Что умеет

- Тегировать музыку через MusicBrainz.
- Раскладывать файлы по исполнителям и альбомам.
- Искать дубли по тегам.
- Оставлять файл с лучшим качеством.
- Переносить худшие дубли в карантин.
- Делать CSV-отчёт.

## Важное правило

Скрипты не должны сразу удалять файлы.

Безопасный сценарий:

```text
исходники остаются на месте
↓
обработанная музыка копируется в Sorted
↓
дубли переносятся в Duplicates
↓
пользователь проверяет отчёт
↓
только потом вручную удаляет лишнее
```

## Установка

```bash
pip install -r requirements.txt
```

## Настройка beets

Открой файл:

```text
beets-config.yaml
```

И поменяй пути:

```yaml
directory: D:\Music\Sorted
library: D:\Music\beets.db
```

## Тегирование и раскладка музыки

```bash
beet -c beets-config.yaml import "D:\Music\Unsorted"
```

По умолчанию конфиг настроен безопасно:

```yaml
copy: yes
move: no
write: yes
timid: yes
```

Это значит:

- исходные файлы не будут удалены;
- обработанные файлы будут скопированы;
- теги будут записаны в копии;
- спорные совпадения потребуют подтверждения.

## Поиск дублей

Только проверка:

```bash
python scripts/find_duplicates.py --library "D:\Music\Sorted" --dry-run
```

Перенос худших дублей в карантин:

```bash
python scripts/find_duplicates.py --library "D:\Music\Sorted" --quarantine "D:\Music\Duplicates"
```

С указанием отчёта:

```bash
python scripts/find_duplicates.py --library "D:\Music\Sorted" --quarantine "D:\Music\Duplicates" --report "reports\duplicates.csv"
```

## Как выбирается лучший файл

Приоритет:

1. FLAC / ALAC / WAV / AIFF.
2. Выше bitrate.
3. Выше bit depth.
4. Выше sample rate.
5. Больше заполненных тегов.
6. Есть встроенная обложка.
7. Больше размер файла.

## Что проверять руками

Перед удалением карантина проверь:

- remaster;
- deluxe edition;
- live;
- radio edit;
- explicit / clean;
- сборники;
- OST;
- разные релизы одного альбома.

## Полезные ссылки

- beets: https://beets.io/
- документация beets: https://beets.readthedocs.io/
- MusicBrainz Picard: https://picard.musicbrainz.org/

## Красивый HTML-отчёт

После поиска дублей можно собрать интерактивный HTML-отчёт:

```bash
python scripts/generate_html_report.py --csv "reports\duplicates.csv" --out "reports\library.html"
```

В отчёте есть:

- сводка по количеству групп и дублей;
- поиск по исполнителю, альбому и названию;
- сортировка;
- раскрывающиеся карточки;
- сравнение оставленного файла и файла в карантине;
- отображение формата, bitrate, bit depth, sample rate, тегов, обложки и размера.

HTML-файл автономный: его можно открыть в браузере без сервера.


Дополнительно:

- Верхняя панель отчёта не закреплена при прокрутке.
- Подписи технических параметров музыки в HTML-отчёте отображаются на русском.

## HTML-отчёт с анализом всей папки

Теперь HTML-отчёт может не только показывать дубли, но и анализировать всю музыкальную папку.

Команда:

```bash
python scripts/generate_html_report.py --csv "reports\duplicates.csv" --library "D:\Music\Sorted" --out "reports\library.html"
```

На странице отчёта будет показано:

- сколько всего аудиофайлов найдено в папке;
- сколько альбомов найдено по тегам `albumartist + album`;
- сколько исполнителей найдено по тегам `artist / albumartist`;
- сколько дублей найдено и сколько файлов предложено перенести в карантин;
- распределение файлов по форматам;
- текущий подробный отчёт по дублям.
