class Entity[TId]:
    def __init__(self, id: TId) -> None:
        self._id = id

    @property
    def id(self) -> TId:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return bool(self._id == other.id)

    def __hash__(self) -> int:
        return hash(self._id)
