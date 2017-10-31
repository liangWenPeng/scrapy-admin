from django.apps import AppConfig

class ScrapykeeperConfig(AppConfig):
    name = 'scrapy_admin'

    def ready(self):
        from . import signals






