import logging
import uuid
from datetime import datetime

import requests
from django.db import models
from django.utils.html import format_html
from django.utils.timezone import now

from .util import start_spider, close_spider

# Create your models here.
STATUE_CACHE_TIME = 120

logger = logging.getLogger(__name__)


class Worker(models.Model):
    name = models.CharField(max_length=128, default='A Worker')
    host = models.CharField('IP', max_length=32)
    port = models.IntegerField('端口', default=6800)
    max_proc = models.IntegerField('最大工作数', default=1)
    created = models.DateTimeField(auto_now_add=True)
    edited = models.DateTimeField(auto_now=True)

    def is_alive(self):
        try:
            addr = self.addr()
            response = requests.get(addr,timeout=1)
            return response.status_code == 200
        except:
            return False

    is_alive.boolean = True
    is_alive.short_description = '存活'

    @staticmethod
    def alive_workers():
        workers = Worker.objects.all()
        alive_workers = [w for w in workers if w.is_alive()]
        return alive_workers

    @staticmethod
    def auto_choose_worker(project):
        workers = [w for w in Worker.alive_workers() if project in w.project_set.all()]
        work = max(workers, key=lambda w: w.rest_count() / w.max_proc)  # 选取闲置率最大的节点
        return work

    def running_count(self):
        return self.status().get('running')

    running_count.short_description = '正在运行工作数'

    def finished_count(self):
        return self.status().get('finished')

    finished_count.short_description = '已结束工作数'

    def pending_count(self):
        return self.status().get('pending')

    pending_count.short_description = '排队工作数'

    def rest_count(self):
        max_proc = self.max_proc
        sta = self.status()
        rest = max_proc - sta['running'] - sta['pending']
        return rest

    def addr(self):
        return 'http://{0}:{1}'.format(self.host, self.port)

    def status(self):
        url = self.addr() + '/daemonstatus.json'
        try:
            result = requests.get(url,timeout=1).json()
            assert result['status'] == 'ok'
            return result
        except:
            logger.error('获取 {0} 节点状态失败'.format(self.host))
            return {}

    def import_projects(self):
        url = '{0}/listprojects.json'.format(self.addr())
        pros = []
        try:
            result = requests.get(url=url).json()
            assert result.get('status') == 'ok'
        except Exception as e:
            logger.error("{0} 导入数据失败".format(self.host))
            logger.error(e)
        else:
            for pname in result.get('projects', []):
                pro, created = Project.objects.get_or_create(name=pname)
                pro.workers.add(self)
                pro.save()
                pro.import_spiders()
                pros.append(pro)

        return pros

    def __str__(self):
        return self.addr()


class Project(models.Model):
    name = models.CharField('名称', max_length=128, unique=True)
    workers = models.ManyToManyField(Worker, help_text='部署节点')
    created = models.DateTimeField('创建时间', auto_now_add=True)
    edited = models.DateTimeField('上次编辑', auto_now=True)

    def import_spiders(self):
        workers = self.workers.all()
        spiders = []
        for w in workers:
            if w.is_alive() == True:
                url = '{0}/listspiders.json?project={1}'.format(w.addr(), self.name)
                try:
                    spiders_result = requests.get(url=url).json()
                    assert spiders_result.get('status') == 'ok'
                except Exception as e:
                    logger.error('{0} error in list spiders'.format(w.addr()))
                    logger.error(e)
                else:
                    for spider in spiders_result.get('spiders', []):
                        sp, created = Spider.objects.get_or_create(name=spider, project=self)
                        spiders.append(sp)
                    break
        return spiders

    def __str__(self):
        return self.name


class Spider(models.Model):
    name = models.CharField('名称', max_length=128)
    # code = models.TextField(null=True, blank=True)
    project = models.ForeignKey(Project, help_text='项目')
    created = models.DateTimeField('创建时间', auto_now_add=True)
    edited = models.DateTimeField('上次编辑', auto_now=True)

    def __str__(self):
        return self.name


class Cron(models.Model):
    name = models.CharField('名称', max_length=265)
    description = models.CharField('描述', max_length=1024, blank=True)
    year = models.CharField(max_length=128, blank=True, null=True)
    month = models.CharField(max_length=128, blank=True, null=True)
    day = models.CharField(max_length=128, blank=True, null=True)
    week = models.CharField(max_length=128, blank=True, null=True)
    day_of_week = models.CharField(max_length=128, blank=True, null=True)
    hour = models.CharField(max_length=128, blank=True, null=True)
    minute = models.CharField(max_length=128, blank=True, null=True)
    second = models.CharField(max_length=128, blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField('创建时间', auto_now_add=True)
    edited = models.DateTimeField('上次编辑', auto_now=True)

    # def expression(self):
    #     template = '{0} {1} {2} {3} {4} {5} {6}'
    #     return template.format(self.second, self.minute, self.hour, self.day, self.month, self.day_of_week, self.year)

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField('名称', max_length=128, default='group name')
    description = models.CharField('描述', max_length=1024, blank=True)
    project = models.ForeignKey(Project, help_text='项目',blank=True,null=True)
    created = models.DateTimeField('创建时间', auto_now_add=True)
    edited = models.DateTimeField('上次编辑', auto_now=True)
    # plan_run_time = models.IntegerField('单次执行时间', blank=True, null=True, default=0)
    # start_date = models.DateTimeField('开始时间', blank=True)
    # cron = models.ForeignKey(Cron, blank=True, null=True, help_text='执行周期')

    def item_scrapyd_count(self):
        total = 0
        for task in self.task_set.all():
            total += task.item_scrapyd_count()
        return total

    item_scrapyd_count.short_description = '已抓取条目数'

    def __str__(self):
        return self.name


class Task(models.Model):
    RUN_TYPES = [('date', '单次执行'), ('cron', '周期执行')]
    group = models.ForeignKey(Group, blank=True, on_delete=models.SET_NULL, null=True, help_text='组')
    name = models.CharField('名称', max_length=128, default='task name')
    project = models.ForeignKey(Project, help_text='所属项目')
    spider = models.ForeignKey(Spider, help_text='蜘蛛')
    spider_args = models.CharField('蜘蛛参数', max_length=256, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    edited = models.DateTimeField(auto_now=True)
    apschulder_id = models.UUIDField(primary_key=False, default=uuid.uuid4, editable=False)
    start_date = models.DateTimeField('开始时间', blank=True)
    is_active = models.BooleanField('激活', default=True)
    cron = models.ForeignKey(Cron, blank=True, null=True, help_text='执行周期')
    total_run_time = models.IntegerField(default=0, editable=False)
    plan_run_time = models.IntegerField('单次执行时间', blank=True, null=True, default=0)
    worker = models.ForeignKey(Worker, null=True, blank=True, help_text='运行节点')
    run_type = models.CharField('执行方式', max_length=128, choices=RUN_TYPES, blank=True, default='date')

    def total_count(self):
        return self.job_set.count()

    def pending_jobs(self):
        jobs = self.job_set.filter(recorded_run_statue='pending').count()
        return '{0}/{1}'.format(jobs, self.total_count())

    def running_jobs(self):
        jobs = self.job_set.filter(recorded_run_statue='running').count()
        return '{0}/{1}'.format(jobs, self.total_count())

    running_jobs.short_description = '运行数'

    def finished_jobs(self):
        jobs = self.job_set.filter(recorded_run_statue='finished').count()
        return '{0}/{1}'.format(jobs, self.total_count())

    finished_jobs.short_description = '结束数'

    def __str__(self):
        return self.name


class Job(models.Model):
    scrapyd_id = models.CharField(max_length=128)
    name = models.CharField('名称', max_length=128, default='job name')
    run_time = models.DurationField('运行时间', blank=True, null=True)
    item_scrapyd = models.IntegerField(default=0, editable=False)
    start_time = models.DateTimeField('开始时间', null=True)
    end_time = models.DateTimeField('结束时间', null=True)
    log_file = models.URLField()
    task = models.ForeignKey(Task, null=True, help_text='所属任务')
    worker = models.ForeignKey(Worker, null=True, blank=True, help_text='运行节点')
    project = models.ForeignKey(Project, help_text='所属项目')
    spider = models.ForeignKey(Spider, help_text='蜘蛛')
    spider_args = models.CharField('蜘蛛参数', max_length=256, blank=True)
    plan_run_time = models.IntegerField(help_text='单次运行时间/分钟', blank=True, null=True, default=0)
    recorded_run_statue = models.CharField(max_length=64, editable=False, null=True)
    recorded_run_statue_time = models.DateTimeField(editable=False, null=True)
    group = models.ForeignKey(Group, blank=True, on_delete=models.SET_NULL, null=True, help_text='组')

    def __str__(self):
        return self.name

    def run_statue(self):
        if self.recorded_run_statue == 'finished':
            return self.recorded_run_statue
        if self.recorded_run_statue_time and (now() - self.recorded_run_statue_time).seconds < STATUE_CACHE_TIME:
            return self.recorded_run_statue
        else:
            import threading
            t =threading.Thread(target=self.update_run_statue)
            t.setDaemon(True)
            t.start()

        return self.recorded_run_statue

    run_statue.short_description = '运行状态'

    def update_run_statue(self):
        self.recorded_run_statue = self.query_scrapyd_run_statue()
        self.recorded_run_statue_time = now()
        if self.recorded_run_statue == 'finished':
            self.end_time = now()
        self.save()

    def query_scrapyd_run_statue(self):
        url = self.worker.addr() + '/listjobs.json' + '?project=' + self.project.name
        try:
            result = requests.get(url).json()
            assert result['status'] == 'ok'
            for item in result.get('pending', []):
                if item['id'] == self.scrapyd_id:
                    return 'pending'
            for item in result.get('running', []):
                if item['id'] == self.scrapyd_id:
                    return 'running'
            for item in result.get('finished', []):
                if item['id'] == self.scrapyd_id:
                    self.end_time = now()
                    return 'finished'
        except Exception as e:
            logging.error(e)
            return 'server error'
        return 'unknown'

    def start(self):
        return start_spider(**self.gen_start_kwargs())

    def stop(self):
        if self.recorded_run_statue not in ('running', 'pending'):
            return

        if not self.end_time:
            self.end_time = now()
        if self.start_time:
            self.run_time = self.end_time - self.start_time
        close_spider(**self.gen_close_kwargs())
        self.save()

    def get_run_time(self):
        if self.run_statue() == 'finished':
            return self.run_time
        elif self.run_time == 'pending':
            return None

        if self.run_statue() == 'running' and self.start_time:
            self.run_time = now() - self.start_time
        elif self.end_time and self.start_time:
            self.run_time = self.end_time - self.start_time
        self.save()
        return self.run_time

    get_run_time.short_description = '运行时间'

    def gen_start_kwargs(self):
        if self.plan_run_time:
            closespider_timeout = self.plan_run_time * 60
        else:
            closespider_timeout = 0
        start_kwargs = {
            'project': self.project.name,
            'spider': self.spider.name,
            'worker_addr': self.worker.addr(),
            'spider_args': self.spider_args,
            'scrapyd_id': self.scrapyd_id,
            'job_id': self.pk,
            'closespider_timeout': closespider_timeout
        }
        return start_kwargs

    def gen_close_kwargs(self):
        close_kwargs = {
            'project': self.project.name,
            'worker_addr': self.worker.addr(),
            'scrapyd_id': self.scrapyd_id,
        }
        return close_kwargs
