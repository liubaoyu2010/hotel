from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "hotel_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)
celery_app.conf.update(
    task_always_eager=settings.celery_eager,
    timezone="Asia/Shanghai",
    beat_schedule={
        "generate-weekly-reports-every-monday-09": {
            "task": "tasks.generate_weekly_reports_all_users",
            "schedule": crontab(minute=0, hour=9, day_of_week=1),
        },
        "push-daily-digest-09": {
            "task": "tasks.push_daily_digest_all_users",
            "schedule": crontab(minute=0, hour=9),
        },
        "collect-activities-daily-06": {
            "task": "tasks.collect_activities_all_users",
            "schedule": crontab(minute=0, hour=6),
        },
    },
)
