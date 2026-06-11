"""异步任务管理器：内存任务状态存储 + 后台执行

MVP 阶段用 asyncio 替代 Celery，API 接口设计兼容未来迁移。
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AsyncTask:
    id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    total: int = 0
    result: Any = None
    error: str | None = None


# 内存任务存储
_tasks: dict[str, AsyncTask] = {}


def create_task(task_type: str) -> AsyncTask:
    task = AsyncTask(id=uuid.uuid4().hex, task_type=task_type)
    _tasks[task.id] = task
    return task


def get_task(task_id: str) -> AsyncTask | None:
    return _tasks.get(task_id)


async def run_task(task: AsyncTask, coro) -> AsyncTask:
    """在后台运行协程任务"""
    task.status = TaskStatus.RUNNING
    try:
        result = await coro
        task.result = result
        task.status = TaskStatus.COMPLETED
    except Exception as e:
        task.error = str(e)
        task.status = TaskStatus.FAILED
    return task
