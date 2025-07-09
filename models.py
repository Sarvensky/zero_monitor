"""Модуль, содержащий классы данных (модели) для проекта."""

from dataclasses import dataclass
import sqlite3


@dataclass
class MemberState:
    """
    Представляет полное сохраненное состояние участника сети.
    Инкапсулирует все данные, которые хранятся в БД для одного узла.
    """

    node_id: str
    name: str
    version_alert_sent: bool = False
    offline_alert_level: int = 0
    last_seen_seconds_ago: int = -1
    problems_count: int = 0

    @classmethod
    def from_db_row(cls, row: sqlite3.Row | None) -> "MemberState | None":
        """Создает экземпляр MemberState из строки базы данных."""
        if not row:
            return None
        return cls(**dict(row))


@dataclass
class OnlineStatusResult:
    """Представляет результат проверки онлайн-статуса."""

    report: str | None
    new_offline_alert_level: int
    seconds_ago: int
    last_online_str: str


@dataclass
class ProblematicMember:
    """Представляет данные о проблемном участнике для отчета."""

    name: str
    problems_count: int
