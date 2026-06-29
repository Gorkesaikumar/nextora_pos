import logging
import time

from celery.signals import task_postrun, task_prerun
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Global Celery metrics
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total count of Celery tasks processed",
    ["task_name", "status"],
)

CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Duration of Celery tasks in seconds",
    ["task_name"],
)

# Store task start times in memory mapping
_task_start_times: dict[str, float] = {}


@task_prerun.connect
def on_task_prerun(sender, task_id, task, **kwargs) -> None:
    _task_start_times[task_id] = time.time()


@task_postrun.connect
def on_task_postrun(sender, task_id, task, retval, state, **kwargs) -> None:
    start = _task_start_times.pop(task_id, None)
    if start is not None:
        duration = time.time() - start
        CELERY_TASK_DURATION.labels(task_name=task.name).observe(duration)

    CELERY_TASKS_TOTAL.labels(task_name=task.name, status=state).inc()


def setup_celery_monitoring() -> None:
    """Invoked in AppConfig.ready to initialize Celery signals."""
    logger.info("Celery monitoring instrumentation successfully loaded.")
