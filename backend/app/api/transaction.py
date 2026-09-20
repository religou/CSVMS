"""请求 seam 上的事务归属（见 ADR-0004）.

service 层不提交，提交由本模块的 `@transactional` 装饰器在请求 seam 上执行。
"""

import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

#: 装饰器在被包裹的函数上留下的标记，供 tests/test_transaction_seam.py 断言覆盖率。
TRANSACTIONAL_MARKER = "__is_transactional__"


def transactional(handler: F) -> F:
    """把一次请求变成一个事务：处理函数返回后、响应生成前提交。

    提交**不能**放在 yield 依赖的 teardown 里。在本项目实际安装的
    FastAPI 0.141 / Starlette 1.6 上，teardown 运行时响应已开始发送，此时抛出的
    HTTPException 会退化成 ``RuntimeError: Caught handled exception, but response
    already started.``，提交失败无法报告给客户端。详见 ADR-0004。

    约定与契约：

    * 被装饰的端点必须持有一个 ``AsyncSession`` 参数（约定命名为 ``db``）。
    * 处理函数抛出任何异常（含 ``BusinessError``）时都不提交；未提交的工作由
      ``get_db`` 的安全网回滚。
    * 提交时的 ``IntegrityError`` 兜底翻译为 409。已知的唯一约束仍应在 service
      内显式预检，不要依赖此兜底。
    * 必须写在路由装饰器**之下**：``@router.put(...)`` 在外，``@transactional`` 在内。
    """

    @functools.wraps(handler)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await handler(*args, **kwargs)
        session = _require_session(kwargs)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise BusinessError("数据冲突，请重试", status_code=409) from exc
        return result

    setattr(wrapper, TRANSACTIONAL_MARKER, True)
    return wrapper  # type: ignore[return-value]


def _require_session(kwargs: dict[str, Any]) -> AsyncSession:
    """从端点实参中取出会话。FastAPI 以关键字参数调用处理函数。"""
    session = kwargs.get("db")
    if isinstance(session, AsyncSession):
        return session
    for value in kwargs.values():
        if isinstance(value, AsyncSession):
            return value
    raise RuntimeError(
        "@transactional 要求端点持有一个 AsyncSession 参数（约定命名为 db）"
    )
