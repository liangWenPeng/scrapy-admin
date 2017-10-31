# -*- coding: utf-8 -*-
from apscheduler.schedulers.background import BackgroundScheduler

APS_SCHEDULER_CONFIG = {
    'apscheduler.jobstores.default': {
        'type': 'sqlalchemy',
        'url': 'sqlite:///jobs.sqlite3'
    },
    'apscheduler.executors.default': {
        'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
        'max_workers': '20'
    },
    'apscheduler.executors.processpool': {
        'type': 'processpool',
        'max_workers': '5'
    },
    'apscheduler.job_defaults.coalesce': 'true',
    'apscheduler.job_defaults.misfire_grace_time': '300',
    'apscheduler.job_defaults.max_instances': '3',
    'apscheduler.timezone': 'Asia/Shanghai',
}

scheduler = BackgroundScheduler(gconfig=APS_SCHEDULER_CONFIG)
scheduler.start()