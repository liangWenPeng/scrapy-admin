# -*- coding: utf-8 -*-

from scrapy.extensions.logstats import LogStats, logger

from twisted.internet import task

from scrapy.exceptions import NotConfigured
from scrapy import signals
from datetime import datetime
from pymongo import MongoClient


class MongoStateStore(object):
    def __init__(self, stats, mongodb_uri, mongodb_database, mongo_states_collection, job_id, interval=60.0):
        self.stats = stats
        self.interval = interval
        self.multiplier = 60.0 / self.interval
        self.task = None
        self.mongo_client = MongoClient(mongodb_uri)
        self.state_collection = self.mongo_client.get_database(mongodb_database).get_collection(mongo_states_collection)
        self.job_id = job_id

    @classmethod
    def from_crawler(cls, crawler):
        mongodb_uri = crawler.settings.get('MONGODB_URI')
        mongodb_database = crawler.settings.get('MONGODB_DATABASE')
        mongo_states_collection = crawler.settings.get('MONGO_STATES_COLLECTION')
        job_id = crawler.settings.get('JOB_ID')
        try:
            job_id = int(job_id)
        except:
            pass
        if not job_id:
            raise NotConfigured
        interval = crawler.settings.getfloat('MONGO_STATES_INTERVAL')
        if not interval:
            raise NotConfigured
        o = cls(crawler.stats, mongodb_uri, mongodb_database, mongo_states_collection, job_id, interval)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        self.pagesprev = 0
        self.itemsprev = 0

        self.task = task.LoopingCall(self.store_state, spider)
        self.task.start(self.interval)

    def store_state(self, spider):
        items = self.stats.get_value('item_scraped_count', 0)
        pages = self.stats.get_value('response_received_count', 0)
        irate = (items - self.itemsprev) * self.multiplier
        prate = (pages - self.pagesprev) * self.multiplier
        self.pagesprev, self.itemsprev = pages, items
        stats = self.stats.get_stats()
        speed = {'item_rate': irate, 'page_rate': prate}
        store = {'job_id': self.job_id, 'datetime': datetime.now()}
        store.update(speed)
        for k, v in stats.items():
            store[k.replace('.', '-')] = v
        self.state_collection.insert(store)

    def spider_closed(self, spider, reason):
        if self.task and self.task.running:
            self.task.stop()
        self.mongo_client.close()
