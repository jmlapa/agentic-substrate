from typing import Any, Protocol, TypeVar, runtime_checkable

from src.kernel.domain.result import Result

TReq_contra = TypeVar("TReq_contra", contravariant=True)
TRes_co = TypeVar("TRes_co", covariant=True)


@runtime_checkable
class UseCase(Protocol[TReq_contra, TRes_co]):
    async def execute(self, request: TReq_contra) -> Result[TRes_co, Any]: ...
