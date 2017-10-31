import time
from django.test import TestCase
from .models import Cron


def say_hello():
    print('hello')


# Create your tests here.
# class TestJobs(TestCase):
    # def test_cron(self):
    #     from .signals import scheduler, _gen_trigger_args
    #     from datetime import datetime
    #     cron = Cron(minute='28-30')
    #     start_date = datetime.now()
    #     cron_trigger = _gen_trigger_args(cron, start_date)
    #     aps_job = scheduler.add_job(say_hello, 'cron', **cron_trigger, replace_existing=True)
    #     while True:
    #         time.sleep(2)

    # def test_close_spider(self):
    #     from .util import close_spider
    #     close_spider('lc_video_platform',worker_addr='http://47.94.145.72:6800',scrapyd_id='78af2890b24611e7aaf1005056c00008')
    #

    # def test_last_statue(self):
    #     from .statue import last_job_statue
    #     print(last_job_statue('fake_job'))

# class TestSignals(TestCase):
#     def test_parse_args(self):
#         from .signals import parse_arg_str
#         print(parse_arg_str('a=1,b=2'))

class TestStatue(TestCase):
    def test_last_statue(self):
        from .statue import last_job_statue
        doc = last_job_statue(260)
        print('doc',doc)
        if doc:
            print(doc.get('item_scraped_count', 0))

    def test_job_context(self):
        from .statue import job_data,job_context
        context = job_context('week',21)
        for k in context.keys():
            print(k,context.get(k))

    # def test_task_context(self):
    #     job_datas = []
    #     from  .statue import megre_data,job_data
    #     for job in ('job2','job1'):
    #         jobdata = job_data('day', job)
    #         print(jobdata)
    #         job_datas.append(jobdata)
    #     taskdata = megre_data(job_datas)
    #     print(taskdata)





