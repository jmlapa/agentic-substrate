from src.modules.knowledge.domain.interfaces.i_data_source_connector import (
    IDataSourceConnector,
)
from src.modules.knowledge.domain.interfaces.i_data_source_connector_registry import (
    IDataSourceConnectorRegistry,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)


class DataSourceConnectorRegistry(IDataSourceConnectorRegistry):
    def __init__(self) -> None:
        self._connectors: dict[DataSourceType, IDataSourceConnector] = {}

    def register(self, connector_type: DataSourceType, connector: IDataSourceConnector) -> None:
        self._connectors[connector_type] = connector

    def get_connector(self, connector_type: DataSourceType) -> IDataSourceConnector:
        connector = self._connectors.get(connector_type)
        if connector is None:
            raise KeyError(f"No connector registered for DataSourceType '{connector_type}'")
        return connector
