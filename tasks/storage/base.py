from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from tasks.models import Task


class BaseStorage(ABC):
    @abstractmethod
    def add(self, task: Task) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> List[Task]:
        raise NotImplementedError

    @abstractmethod
    def get(self, task_id: int) -> Optional[Task]:
        raise NotImplementedError

    @abstractmethod
    def update(self, task: Task) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        raise NotImplementedError
