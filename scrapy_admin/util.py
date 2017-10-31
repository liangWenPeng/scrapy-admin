# -*- coding: utf-8 -*-
import logging

import requests

logger = logging.getLogger(__name__)


def parse_arg_str(scrapy_args):
    kvs = scrapy_args.split(',')
    args = {}
    for kv in kvs:
        kv = kv.strip()
        if kv:
            try:
                strs = kv.split('=')
                args[strs[0]] = strs[1]
            except:
                logger.warning('爬虫启动参数格式错误')
    return args


def strip_or_none(str_field):
    if not isinstance(str_field, str):
        return str_field
    if str_field and str_field.strip():
        return str_field.strip()
    else:
        return None


def start_spider(project, spider, worker_addr, spider_args, scrapyd_id, job_id, closespider_timeout=None):
    print('接收到启动爬虫信号')
    url = worker_addr + '/schedule.json'
    args = parse_arg_str(spider_args)
    data = {
        'project': project,
        'spider': spider,
        'jobid': scrapyd_id,
        'setting': ["JOB_ID={0}".format(job_id), 'CLOSESPIDER_TIMEOUT={0}'.format(closespider_timeout)],  # 保存状态时用
    }
    data.update(args)
    try:
        result = requests.post(url=url, data=data).json()
        logger.debug(result)
        assert result['status'] == 'ok'
    except Exception as e:
        logger.error('启动爬虫失败:{0}  {1}  {2}  {3}'.format(spider, spider_args, worker_addr, scrapyd_id))
        logger.error(e)
    else:
        print('启动爬虫成功:{0}  {1}  {2}  {3}  {4}'.format(spider, spider_args, project, worker_addr, scrapyd_id))
        logger.debug('启动爬虫成功:{0}  {1}  {2}  {3}'.format(spider, spider_args, worker_addr, scrapyd_id))
        return True
    return False


def close_spider(project, worker_addr, scrapyd_id):
    print('接收到关闭爬虫信号')
    url = worker_addr + '/cancel.json'
    data = {
        'project': project,
        'job': scrapyd_id,
    }
    try:
        result = requests.post(url=url, data=data).json()
        assert result['status'] == 'ok'
    except Exception as e:
        logger.error('停止爬虫失败:{0}  {1}  {2}'.format(worker_addr, project, scrapyd_id))
        logger.error(e)
    else:
        print('停止爬虫成功:{0}  {1}'.format(worker_addr, scrapyd_id))
        logger.info('停止爬虫成功:{0}  {1}  {2}'.format(worker_addr, project, scrapyd_id))


def gen_trigger_args(cron, start_date):
    args = {}
    if cron.year and cron.year.strip():
        args['year'] = cron.year
    if cron.month and cron.month.strip():
        args['month'] = cron.month
    if cron.day and cron.day.strip():
        args['day'] = cron.day
    if cron.week and cron.week.strip():
        args['week'] = cron.week
    if cron.day_of_week and cron.day_of_week.strip():
        args['day_of_week'] = cron.day_of_week
    if cron.hour and cron.hour.strip():
        args['hour'] = cron.hour
    if cron.minute and cron.minute.strip():
        args['minute'] = cron.minute
    if cron.second and cron.second.strip():
        args['second'] = cron.second

    if start_date:
        args['start_date'] = start_date
    if cron.end_date:
        args['end_date'] = cron.end_date

    return args


def gen_fake_status_data(minutes, job_id, start_time):
    from pymongo import MongoClient
    from scrapy_admin.settings import MONGODB_URI, MONGODB_DATABASE, MONGO_STATES_COLLECTION
    from datetime import datetime, timedelta
    import random
    mongo_client = MongoClient(MONGODB_URI)
    states_collection = mongo_client[MONGODB_DATABASE][MONGO_STATES_COLLECTION]
    request_count = 0
    response_count = 0
    item_scraped_count = 0
    file_count = 0
    for i in range(0, minutes):
        request_count += random.randint(2, 11)
        response_count += random.randint(0, 11)
        item_scraped_count += random.randint(0, 3)
        file_count += random.randint(0, 3)
        fake_statue = {
            'datetime': start_time + timedelta(minutes=i),
            'item_rate': random.randint(0, 3),
            'page_rate': random.randint(2, 9),
            'downloader/request_count': request_count,
            'downloader/response_count': response_count,
            'item_scraped_count': item_scraped_count,
            'file_count': file_count,
            'job_id': job_id
        }
        states_collection.insert(fake_statue)
    mongo_client.close()


if __name__ == '__main__':
    from datetime import datetime, timedelta
    gen_fake_status_data(60, 121, datetime.now() - timedelta(hours=1))

