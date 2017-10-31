"""spider_site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^statue/job/(?P<job_id>[0-9a-zA-Z]+)/$', views.job_statue),
    url(r'^statue/task/(?P<task_id>[0-9a-zA-Z]+)/$', views.task_statue),
    url(r'^chart/job/(?P<time_type>[a-z]{3,6})/(?P<job_id>[0-9a-zA-Z]+)/$', views.job_chart),
    url(r'^chart/task/(?P<time_type>[a-z]{3,6})/(?P<task_id>[0-9a-zA-Z]+)/$', views.task_chart),
    url(r'^chart/group/(?P<group_id>[0-9a-zA-Z]+)/$', views.group_chart),
    url(r'^chart/project/(?P<project_id>[0-9a-zA-Z]+)/$', views.project_chart),
    url(r'^init', views.init_data),
]
