from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404

from .models import *
# Create your views here.
from .statue import job_context, multi_job_context
from datetime import timedelta

logger = logging.getLogger(__name__)


def job_statue(request, job_id):
    return render_to_response('scrapy_admin/chartframe.html', {'entry': 'job', 'entry_id': job_id})


def task_statue(request, task_id):
    return render_to_response('scrapy_admin/chartframe.html', {'entry': 'task', 'entry_id': task_id})


def job_chart(request, time_type, job_id):
    job = get_object_or_404(Job, pk=job_id)
    context = job_context(time_type, job.pk)
    context['job_name'] = job.name
    return render_to_response('scrapy_admin/jobchart.html', context=context)


def task_chart(request, time_type, task_id):
    task = get_object_or_404(Task, pk=task_id)
    job_pks = [job.pk for job in task.job_set.all()]
    context = multi_job_context(job_pks=job_pks, time_type=time_type)
    context['pie_data'] = [{'name': Job.objects.get(pk=k).name, 'value': v[0]} for k, v in
                           context['job_scrapyd_ratio'].items()]
    context['task_name'] = task.name
    return render_to_response('scrapy_admin/taskchart.html', context=context)


def group_chart(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    job_pks = [job.pk for job in group.job_set.all()]
    start_time = min(datetime.now() - timedelta(days=15),group.created.replace(tzinfo=None))
    context = multi_job_context(job_pks=job_pks, time_type='month', start_time=start_time)
    context['group_name'] = group.name
    item_pie_data = []
    file_pie_data = []
    for task in group.task_set.all():
        jobs = [job.pk for job in task.job_set.all()]
        item = 0
        file = 0
        for k, v in context['job_scrapyd_ratio'].items():
            if k in jobs:
                item += v[0]
                file += v[1]
        item_pie_data.append({'name': task.name, 'value': item})
        file_pie_data.append({'name': task.name, 'value': file})

    context['item_pie_data'] = item_pie_data
    context['file_pie_data'] = file_pie_data
    context['total_item'] = sum([v[0] for v in context['job_scrapyd_ratio'].values()])
    context['total_file'] = sum([v[1] for v in context['job_scrapyd_ratio'].values()])
    return render_to_response('scrapy_admin/groupchart.html', context=context)


def project_chart(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    job_pks = [job.pk for job in project.job_set.all()]
    start_time = min(datetime.now() - timedelta(days=15), project.created.replace(tzinfo=None))
    context = multi_job_context(job_pks=job_pks, time_type='month', start_time=start_time)
    context['project_name'] = project.name
    item_pie_data = []
    file_pie_data = []
    for group in project.group_set.all():
        jobs = [job.pk for job in group.job_set.all()]
        item = 0
        file = 0
        for k, v in context['job_scrapyd_ratio'].items():
            if k in jobs:
                item += v[0]
                file += v[1]
        item_pie_data.append({'name': group.name, 'value': item})
        file_pie_data.append({'name': group.name, 'value': file})
    context['item_pie_data'] = item_pie_data
    context['file_pie_data'] = file_pie_data
    context['total_item'] = sum([v[0] for v in context['job_scrapyd_ratio'].values()])
    context['total_file'] = sum([v[1] for v in context['job_scrapyd_ratio'].values()])
    return render_to_response('scrapy_admin/projectchart.html', context=context)


def init_data(request):
    # for i in range(0, 24):
    #     cron = Cron(name='每天{0}点开始'.format(i), hour=i)
    #     cron.save()
    # w1 = Worker(name='阿里云ubuntu', host='118.190.112.31')
    # w1.save()
    # w1.import_projects()
    # w2 = Worker(name='阿里云测试机', host='47.94.145.72')
    # w2.save()
    # w2.import_projects()
    chs = ['funny', 'sport', 'music', 'game', 'erciyuan', 'yule', 'society', 'edu', 'meng', 'tour', 'paike', 'food',
           'world', 'science', ]
    # for c in chs:
    #     g = Group(name=c)
    #     g.save()
    # p = Project.objects.first()
    # s = Spider.objects.first()
    # for i in range(0, 12):
    #     channel = chs[i]
    #     group = Group.objects.get(name=channel)
    #     cron = Cron.objects.get(hour=i * 2)
    #     for j in range(0, 4):
    #         task = Task(project=p, group=group, cron=cron, run_type='cron', is_active=False,
    #                     spider=s,spider_args='channel=' + group.name,plan_run_time=120,
    #                     start_date=now())
    #         task.save()
    for t in Task.objects.all():
        t.name = t.spider.name + ' '+t.group.name
    return HttpResponseRedirect('/')
