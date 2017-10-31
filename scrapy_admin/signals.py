# -*- coding: utf-8 -*-
import logging
import uuid
from datetime import datetime, timedelta

from django.db.models.signals import post_save, post_delete, pre_delete, post_init, pre_save
from django.dispatch import receiver
from django.utils.timezone import now

from .aps import scheduler
from .models import Job, Task, Worker, Project
from .util import close_spider, gen_trigger_args

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Project)
def create_project_receiver(instance, created, **kwargs):
    if created:
        instance.import_spiders()


def create_job(task_id):
    task = Task.objects.get(pk=task_id)
    job_name = '{0} job #{1}'.format(task.name, task.job_set.count())
    job = Job(name=job_name, project=task.project, spider=task.spider, spider_args=task.spider_args, task=task,
              scrapyd_id=uuid.uuid1().hex, plan_run_time=task.plan_run_time, group=task.group,start_time=now())
    if task.worker:
        job.worker = task.worker
    else:
        job.worker = Worker.auto_choose_worker(task.project)
    job.log_file = '{0}/logs/{1}/{2}/{3}.log'.format(job.worker.addr(), job.project, job.spider, job.scrapyd_id)
    job.save()


@receiver(post_save, sender=Task)
def update_task_receiver(instance, **kwargs):
    if instance.is_active:
        # 判断是否已经加入到任务队列
        aps_job = scheduler.get_job(instance.apschulder_id.hex)
        if aps_job:  # 是
            _modify_apscheduler_job(instance, aps_job)
        else:  # 否，加入
            _add_apscheduler_job(instance)
    else:
        apschulder_id = instance.apschulder_id.hex
        if scheduler.get_job(apschulder_id):
            try:
                scheduler.remove_job(job_id=apschulder_id)
            except Exception as e:
                logger.warning(e)


@receiver(post_delete, sender=Task)
def delete_task_receiver(instance, **kwargs):
    apschulder_id = instance.apschulder_id.hex
    if scheduler.get_job(apschulder_id):
        try:
            scheduler.remove_job(job_id=apschulder_id)
        except Exception as e:
            logger.warning(e)


@receiver(post_save, sender=Job)
def create_job_receiver(instance, created, **kwargs):
    if created:
        start_successly = instance.start()
        if start_successly and instance.plan_run_time:
            close_date = datetime.now() + timedelta(minutes=instance.plan_run_time)
            scheduler.add_job(close_spider, 'date', run_date=close_date, kwargs=instance.gen_close_kwargs())


# @receiver(post_init, sender=Job)
# def init_job_receiver(instance, **kwargs):
#     instance.__original_spider = instance.spider
#     instance.__original_spider_args = instance.spider_args
#     instance.__origina_plan_run_time = instance.plan_run_time

# @receiver(pre_save, sender=Job)
# def update_job_receiver(instance, **kwargs):
#     # if instance.imported:
#     #     return
#
#     start_successly = False
#     if not instance.pk:
#         created = True
#     else:
#         created = False
#     if created:
#         # if not instance.imported:
#         start_successly = instance.start()
#     # elif instance.__original_spider!=instance.spider or instance.__original_spider_args!=instance.spider_args \
#     #         or instance.__origina_plan_run_time!=instance.plan_run_time:
#     #     instance.stop()
#     #     start_successly = instance.start()
#
#     if start_successly:
#         plan_run_time = instance.plan_run_time
#         if plan_run_time:
#             close_date = datetime.now() + timedelta(minutes=plan_run_time)
#             scheduler.add_job(close_spider, 'date', run_date=close_date, kwargs=instance.gen_close_kwargs())
#

@receiver(pre_delete, sender=Job)
def del_job_receiver(instance, **kwargs):
    instance.stop()


def _add_apscheduler_job(instance):
    start_date = instance.start_date or datetime.now()
    if not instance.run_type or instance.run_type == 'date':
        scheduler.add_job(create_job, 'date', run_date=start_date, args=(instance.id,),
                          id=instance.apschulder_id.hex, name=instance.name)
    elif instance.run_type == 'cron':
        cron = instance.cron
        trigger_args = gen_trigger_args(cron, start_date)
        scheduler.add_job(create_job, 'cron', args=(instance.id,),
                          id=instance.apschulder_id.hex, name=instance.name, **trigger_args)


def _modify_apscheduler_job(instance, aps_job):

    start_date = instance.start_date or datetime.now()
    if not instance.run_type or instance.run_type == 'date':
        scheduler.reschedule_job(aps_job.id, trigger='date', run_date=start_date, )
    elif instance.run_type == 'cron':
        cron = instance.cron
        cron_trigger_args = gen_trigger_args(cron, start_date)
        scheduler.reschedule_job(aps_job.id, trigger='cron', **cron_trigger_args)
