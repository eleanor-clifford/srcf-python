from typing import TypeVar

from srcflib.plumbing.common import Collect, Result, State, Unset, require_host


T = TypeVar("T")


def default() -> Result[Unset]:
    return Result()


def unchanged() -> Result[Unset]:
    return Result(State.unchanged)


def success() -> Result[Unset]:
    return Result(State.success)


def success_value(value: T) -> Result[T]:
    return Result(State.success, value)


def created() -> Result[Unset]:
    return Result(State.created)


@Result.collect
def collect_unchanged() -> Collect[None]:
    yield unchanged()


@Result.collect
def collect_success() -> Collect[None]:
    yield success()


@Result.collect_value
def collect_success_value(value: T) -> Collect[T]:
    result = yield from success_value(value)
    return result.value


@Result.collect
def collect_pair() -> Collect[None]:
    yield unchanged()
    yield success()


@Result.collect_value
def collect_all() -> Collect[str]:
    yield unchanged()
    yield success()
    result = yield from success_value("test")
    yield created()
    return result.value


@require_host("here")
def require_here() -> Result[Unset]:
    return Result(State.success)
