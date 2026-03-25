import asyncio

import pytest

from src.core.di import DependencyContainer


@pytest.mark.asyncio
async def test_dependency_container_creates_singleton_once_under_concurrency():
    container = DependencyContainer()
    calls = 0

    async def create_service():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return {"instance": calls}

    container._register_singleton("expensive_service", create_service)

    instances = await asyncio.gather(
        container.get("expensive_service"),
        container.get("expensive_service"),
        container.get("expensive_service"),
    )

    assert calls == 1
    assert instances[0] is instances[1] is instances[2]
    assert instances[0]["instance"] == 1


@pytest.mark.asyncio
async def test_dependency_container_retries_after_failed_singleton_creation():
    container = DependencyContainer()
    calls = 0

    async def create_service():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        if calls == 1:
            raise RuntimeError("boom")
        return {"instance": calls}

    container._register_singleton("flaky_service", create_service)

    with pytest.raises(RuntimeError, match="boom"):
        await container.get("flaky_service")

    instance = await container.get("flaky_service")

    assert calls == 2
    assert instance["instance"] == 2
