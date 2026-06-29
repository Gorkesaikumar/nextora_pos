from abc import ABC, abstractmethod
from uuid import UUID


class BaseSearchProvider(ABC):

    @abstractmethod
    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        """Performs search on a specific domain entity and returns standardized results.

        Standardized dict format:
        {
            "id": str,
            "type": str,
            "title": str,
            "subtitle": str,
            "rank": float,
            "url": str
        }
        """
        pass


class SearchRegistry:
    _registry: dict[str, BaseSearchProvider] = {}

    @classmethod
    def register(cls, name: str, provider: BaseSearchProvider) -> None:
        cls._registry[name] = provider

    @classmethod
    def get(cls, name: str) -> BaseSearchProvider | None:
        return cls._registry.get(name)

    @classmethod
    def list_providers(cls) -> dict[str, BaseSearchProvider]:
        return cls._registry
