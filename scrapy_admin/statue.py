# -*- coding: utf-8 -*-
from datetime import timedelta, datetime

import pymongo
from pymongo import MongoClient

from .settings import MONGODB_URI, MONGODB_DATABASE, MONGO_STATES_COLLECTION

mongo_client = MongoClient(MONGODB_URI)


def _aggregate(match, group_by):
    """Mongo聚合查询"""
    states_collection = mongo_client[MONGODB_DATABASE][MONGO_STATES_COLLECTION]
    agg_args = [
        {"$match": match},
        {"$sort": {"datetime": 1}},
        {
            "$group":
                {
                    "_id": group_by,
                    "datetime": {"$last": "$datetime"},
                    "item_rate": {"$avg": "$item_rate"},
                    "page_rate": {"$avg": "$page_rate"},
                    "downloader/request_count": {"$last": "$downloader/request_count"},
                    "downloader/response_count": {"$last": "$downloader/response_count"},
                    "file_count": {"$last": "$file_count"},
                    "item_scraped_count": {"$last": "$item_scraped_count"},
                }
        },
    ]
    docs = states_collection.aggregate(agg_args)
    return docs


def _start_time(time_type):
    now_time = datetime.now()
    if time_type == 'hour':
        start_time = datetime(year=now_time.year, month=now_time.month, day=now_time.day, hour=now_time.hour,
                              minute=now_time.minute) - timedelta(minutes=59)
    elif time_type == 'day':
        start_time = datetime(year=now_time.year, month=now_time.month, day=now_time.day,
                              hour=now_time.hour) - timedelta(
            hours=23)
    elif time_type == 'week':
        start_time = datetime(year=now_time.year, month=now_time.month, day=now_time.day) - timedelta(days=6)
    elif time_type == 'month':
        start_time = datetime(year=now_time.year, month=now_time.month, day=now_time.day) - timedelta(days=29)
    else:
        raise ValueError('time_type 只能为hour/day/week/month')
    return start_time


def _group_by_time(time_type):
    if time_type == 'hour':
        group_by = {'$minute': "$datetime"}
    elif time_type == 'day':
        group_by = {'$hour': "$datetime"}
    elif time_type == 'week':
        group_by = {'$dayOfMonth': "$datetime"}
    elif time_type == 'month':
        group_by = {'$dayOfMonth': "$datetime"}
    else:
        raise ValueError('time_type 只能为hour/day/week/month')
    return group_by


def _xdata(time_type, start_time=None):
    """生成x轴坐标"""
    start_date = start_time or _start_time(time_type)
    cur_date = start_date
    xaxis_data = []
    # print(start_date,end_date,cur_date)
    while cur_date < datetime.now():
        if time_type == 'hour':
            xaxis_data.append(cur_date.minute)
            cur_date += timedelta(minutes=1)
        elif time_type == 'day':
            xaxis_data.append(cur_date.hour)
            cur_date += timedelta(hours=1)
        elif time_type in ('week', 'month'):
            xaxis_data.append(cur_date.day)
            cur_date += timedelta(days=1)
    return xaxis_data


def extrct_data(doc):
    """从mongo文档提取数据"""
    if doc:
        data = (doc['_id'], doc.get('item_rate', 0), doc.get('page_rate', 0),
                doc.get('downloader/request_count', 0), doc.get('downloader/response_count', 0),
                doc.get('item_scraped_count', 0), doc.get('file_count', 0))
        data = [d or 0 for d in data]
        return data


def clean_data(xdatas, ydatas):
    """数据清洗，补全去补全缺失的数据"""
    datas = []
    for x in xdatas:
        for y in ydatas:
            if x == y[0]:
                data = y
                break
        else:
            if datas:
                last_data = datas[max(len(datas) - 1, 0)]
                data = [x, 0, 0, last_data[3], last_data[4], last_data[5], last_data[6]]
            else:
                data = [x, 0, 0, 0, 0, 0, 0]
        datas.append(data)
    return datas


def edit_data(datas, start_data=None):
    """编辑数据，将总量修改为单位时间的产量"""
    new_datas = []
    for i in range(len(datas) - 1, 0, -1):
        d = datas[i]
        pred = datas[i - 1]
        new_datas.append((d[0], d[1], d[2], max(d[3] - pred[3], 0), max(d[4] - pred[4], 0),
                          max(d[5] - pred[5], 0), max(d[6] - pred[6], 0)))
    new_datas.reverse()
    if start_data:
        d = datas[0]
        pred = start_data
        new_datas.insert(0, (d[0], d[1], d[2], max(d[3] - pred[3], 0), max(d[4] - pred[4], 0),
                             max(d[5] - pred[5], 0), max(d[6] - pred[6], 0)))
    else:
        new_datas.insert(0, datas[0])
    return new_datas


def _single_job_docs(time_type, job_id, start_time=None):
    match = {'job_id': job_id, 'datetime': {"$gte": start_time or _start_time(time_type)}}
    docs = _aggregate(match=match, group_by=_group_by_time(time_type))
    return docs


def megre_data(job_datas):
    """合并多个job的数据"""
    if job_datas:
        megredata = job_datas[0]
        for jdata in job_datas[1:]:
            for i in range(0, len(jdata)):
                d = jdata[i]
                if len(megredata) > i:
                    tmp = [megredata[i][j] + d[j] for j in range(1, len(d))]
                    tmp.insert(0, d[0])
                    megredata[i] = tmp
                else:
                    megredata.append(jdata)
        return megredata


def last_job_statue(job_id, start_date=datetime.now()):
    """获取job的最新状态数据,截止到startdate"""
    states_collection = mongo_client[MONGODB_DATABASE][MONGO_STATES_COLLECTION]
    docs = states_collection.find({"job_id": job_id, 'datetime': {"$lt": start_date}}).sort(
        [('datetime', pymongo.DESCENDING), ]).limit(1)
    for d in docs:
        return d


def job_data(time_type, job_id, start_time=None):
    docs = _single_job_docs(time_type, job_id, start_time)
    order_docs = list(docs)
    order_docs.sort(key=lambda d: d['datetime'])
    xaxis_data = _xdata(time_type, start_time)
    # print(1,xaxis_data)
    ydatas = [extrct_data(doc) for doc in order_docs]
    # print(2,ydatas)
    datas = clean_data(xaxis_data, ydatas)
    # print(3,datas)
    befor_doc = last_job_statue(job_id, start_time or _start_time(time_type))
    start_data = extrct_data(befor_doc)
    datas = edit_data(datas=datas, start_data=start_data)
    # print(4,datas)
    return datas


def gen_context(datas):
    if datas:
        xaxis_data, item_rates, page_rates, request_counts, response_counts, item_scraped_counts, file_counts = zip(
            *datas)
        context = {
            'xaxis_data': list(xaxis_data),
            'item_rates': list(item_rates),
            'page_rates': list(page_rates),
            'request_counts': list(request_counts),
            'response_counts': list(response_counts),
            'item_scraped_counts': list(item_scraped_counts),
            'file_counts': list(file_counts),
        }
        # print(context)
        return context
    else:
        return {}


def job_context(time_type, job_id, start_time=None):
    data = job_data(time_type, job_id, start_time)
    return gen_context(datas=data)


def job_scrapyd_ratio(job_pks, start_time = None):
    match = {'job_id': {'$in': job_pks}}
    if start_time:
        match['datetime'] =  {"$gte": start_time}
    group_by = {"job_id": "$job_id"}
    docs = _aggregate(match, group_by)
    data = {}
    for doc in docs:
        pk = doc['_id'].get('job_id')
        data[pk] = (doc.get('item_scraped_count', 0) or 0, doc.get('file_count', 0) or 0)
    return data


def multi_job_data(time_type, job_pks, start_time=None):
    job_datas = []
    for pk in job_pks:
        jobdata = job_data(time_type, pk, start_time)
        job_datas.append(jobdata)
    return megre_data(job_datas)


def multi_job_context(time_type, job_pks, start_time=None):
    data = multi_job_data(time_type, job_pks, start_time)
    context = gen_context(datas=data)
    context['job_scrapyd_ratio'] = job_scrapyd_ratio(job_pks, start_time or _start_time(time_type))
    return context
