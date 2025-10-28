# main/services/error_parser.py

from datetime import datetime, timezone

from ..models import ContainerError  # Исправленный импорт

ERROR_KEYWORDS = ['ERROR', 'Error', 'Exception', 'Traceback', 'Stacktrace']

def parse_logs_and_save_errors(
    source_type: str,
    container_id: str,
    container_name: str,
    logs: str,
    service_name: str | None = None,
    default_level: str = 'Error',
) -> int:
    """
    Простой парсер: при встрече ключевого слова начинает копить блок до пустой строки или следующего ключевого слова.
    Возвращает число сохранённых ошибок.
    """
    if not logs:
        return 0

    lines = logs.splitlines()
    errors_found = 0
    buf: list[str] = []
    capturing = False

    def flush():
        nonlocal errors_found, buf
        if not buf:
            return
        full = '\n'.join(buf)
        short = full.split('\n', 1)[0][:1024]
        ContainerError.objects.create(
            source_type=source_type,
            container_id=container_id,
            container_name=container_name,
            timestamp=datetime.now(timezone.utc),
            error_message=full,
            short_message=short,
            level=default_level,
            service_name=service_name or '',
        )
        errors_found += 1
        buf = []

    for line in lines:
        has_kw = any(k in line for k in ERROR_KEYWORDS)
        if has_kw:
            # новый блок ошибки — сбрасываем предыдущий
            flush()
            capturing = True
            buf.append(line)
            continue
        if capturing:
            # завершаем блок по пустой строке — удобно для Java/Kotlin stacktrace
            if line.strip() == '':
                flush()
                capturing = False
            else:
                buf.append(line)

    # финальный сброс
    if capturing:
        flush()

    return errors_found