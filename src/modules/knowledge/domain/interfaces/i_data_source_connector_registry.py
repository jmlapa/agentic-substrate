from typing import Protocol, runtime_checkable

from src.modules.knowledge.domain.interfaces.i_data_source_connector import (
    IDataSourceConnector,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)


@runtime_checkable
class IDataSourceConnectorRegistry(Protocol):
    def register(
        self, connector_type: DataSourceType, connector: IDataSourceConnector
    ) -> None: ...

    def get_connector(
        self, connector_type: DataSourceType
    ) -> IDataSourceConnector: ...
