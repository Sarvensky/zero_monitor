"""Модуль для управления состоянием и статистикой в базе данных SQLite."""

import sqlite3
from datetime import date
import settings


def get_db_connection() -> sqlite3.Connection:
    """Создает и возвращает соединение с базой данных SQLite."""
    conn = sqlite3.connect(settings.DB_FILE)
    # Позволяет обращаться к колонкам по имени, что удобнее, чем по индексу
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    """
    Инициализирует базу данных: создает таблицы, если они не существуют,
    и заполняет начальные значения статистики.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Таблица для хранения состояния каждого отслеживаемого участника
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS member_states (
            node_id TEXT PRIMARY KEY,
            name TEXT,
            version_alert_sent BOOLEAN DEFAULT FALSE,
            offline_alert_level INTEGER DEFAULT 0,
            last_seen_seconds_ago INTEGER DEFAULT -1,
            problems_count INTEGER DEFAULT 0
        )
        """
        )

        # Для обратной совместимости с базами, созданными до этого изменения,
        # попробуем добавить столбец, если он отсутствует.
        try:
            cursor.execute(
                "ALTER TABLE member_states ADD COLUMN last_seen_seconds_ago INTEGER DEFAULT -1"
            )
            print(
                settings.t(
                    "column_added_to_table",
                    column="last_seen_seconds_ago",
                    table="member_states",
                )
            )
        except sqlite3.OperationalError as e:
            # Игнорируем ошибку, если столбец уже существует.
            # Сообщение об ошибке может отличаться в разных версиях SQLite.
            if "duplicate column name" not in str(e).lower():
                raise

        try:
            cursor.execute(
                "ALTER TABLE member_states ADD COLUMN problems_count INTEGER DEFAULT 0"
            )
            print(
                settings.t(
                    "column_added_to_table",
                    column="problems_count",
                    table="member_states",
                )
            )
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise

        # Сбрасываем сохраненное время последнего онлайна при каждом запуске,
        # чтобы избежать ложных срабатываний детектора аномалий после перезапуска.
        # Устанавливаем в -1, так как это значение используется для обозначения
        # отсутствия предыдущих данных о времени.
        cursor.execute("UPDATE member_states SET last_seen_seconds_ago = -1")

        # Таблица для хранения общей статистики работы скрипта (ключ-значение)
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS script_stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
        )

        # Инициализация статистики, если она еще не задана
        # INSERT OR IGNORE не будет ничего делать, если ключ уже существует
        today_str = str(date.today())
        initial_stats = [
            ("last_report_date", today_str),
            ("checks_today", "0"),
            ("problems_today", "0"),
            ("last_check_datetime", "N/A"),
            ("latest_zt_version", settings.ZT_FALLBACK_VERSION),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO script_stats (key, value) VALUES (?, ?)",
            initial_stats,
        )
        print(settings.t("db_initialized"))


def get_member_state(node_id: str) -> sqlite3.Row | None:
    """Получает состояние для одного участника из БД."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM member_states WHERE node_id = ?", (node_id,))
        return cursor.fetchone()


def update_member_state(
    node_id: str,
    name: str,
    version_alert_sent: bool,
    offline_alert_level: int,
    last_seen_seconds_ago: int,
    problems_count: int,
):
    """Обновляет или вставляет состояние участника в БД."""
    with get_db_connection() as conn:
        conn.execute(
            """
        INSERT INTO member_states (node_id, name, version_alert_sent, offline_alert_level, last_seen_seconds_ago, problems_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            name=excluded.name,
            version_alert_sent=excluded.version_alert_sent,
            offline_alert_level=excluded.offline_alert_level,
            last_seen_seconds_ago=excluded.last_seen_seconds_ago,
            problems_count=excluded.problems_count
        """,
            (
                node_id,
                name,
                version_alert_sent,
                offline_alert_level,
                last_seen_seconds_ago,
                problems_count,
            ),
        )


def get_stats() -> dict:
    """Загружает всю статистику из БД в виде словаря."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM script_stats")
        rows = cursor.fetchall()
        stats = {row["key"]: row["value"] for row in rows}
        # Преобразуем числовые значения в int для удобства использования
        stats["checks_today"] = int(stats.get("checks_today", 0))
        stats["problems_today"] = int(stats.get("problems_today", 0))
        return stats


def save_stats(stats: dict) -> None:
    """Сохраняет словарь со статистикой в БД."""
    with get_db_connection() as conn:
        for key, value in stats.items():
            conn.execute(
                "UPDATE script_stats SET value = ? WHERE key = ?", (str(value), key)
            )


def get_latest_zt_version_from_db() -> str | None:
    """Получает последнюю известную версию ZeroTier из БД."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM script_stats WHERE key = 'latest_zt_version'")
        row = cursor.fetchone()
        return row["value"] if row else None


def save_latest_zt_version(version: str) -> None:
    """Сохраняет последнюю версию ZeroTier в БД."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE script_stats SET value = ? WHERE key = 'latest_zt_version'",
            (version,),
        )
    # Выводим сообщение в консоль, но не в Telegram, т.к. это не событие-ошибка
    print(settings.t("zt_version_db_updated", version=version))


def get_problematic_members() -> list[sqlite3.Row]:
    """Возвращает список участников, у которых были проблемы за день."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name, problems_count FROM member_states
            WHERE problems_count > 0
            ORDER BY problems_count DESC
            """
        )
        return cursor.fetchall()


def reset_daily_problem_counts() -> None:
    """Сбрасывает счетчик дневных проблем для всех участников."""
    with get_db_connection() as conn:
        conn.execute("UPDATE member_states SET problems_count = 0")
        print(settings.t("daily_counters_reset"))
