from django.contrib import admin
from django.utils.html import format_html

from .models import Worker, Project, Spider, Job, Cron, Task, Group
from .statue import job_scrapyd_ratio, last_job_statue


class WorkerAdmin(admin.ModelAdmin):
    list_display = (
        'host', 'port', 'max_proc', 'pending_count', 'running_count', 'finished_count', 'item_scrapyd_count',
        'is_alive')
    readonly_fields = ('created', 'edited')
    actions = ['import_proj', 'import_job']

    def import_proj(self, request, queryset):
        p_count = 0
        for w in queryset:
            p_count = len(w.import_projects())
        self.message_user(request, "{0} projects was imported successfully.".format(p_count))

    import_proj.short_description = "Import existing projects from the selected workers"

    def item_scrapyd_count(self, obj):
        job_pks = [job.pk for job in obj.job_set.all()]
        data = job_scrapyd_ratio(job_pks)
        if data:
            values = [v[0] for v in data.values()]
            return sum(values)

    item_scrapyd_count.short_description = '已抓取数'


class SpiderAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'item_scrapyd_count')
    list_filter = ['project']
    readonly_fields = ['created', 'edited']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.name and 'name' not in self.readonly_fields:
            self.readonly_fields.append('name')
        if obj and obj.project and 'project' not in self.readonly_fields:
            self.readonly_fields.append('project')
        return self.readonly_fields

    def item_scrapyd_count(self, obj):
        job_pks = [job.pk for job in obj.job_set.all()]
        data = job_scrapyd_ratio(job_pks)
        if data:
            values = [v[0] for v in data.values()]
            return sum(values)

    item_scrapyd_count.short_description = '已抓取数'


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'edited', 'item_scrapyd_count', 'chart_href')
    readonly_fields = ['created', 'edited']
    actions = ['import_spiders']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.name and 'name' not in self.readonly_fields:
            self.readonly_fields.append('name')
        return self.readonly_fields

    def import_spiders(self, request, queryset):
        spider_count = 0
        for p in queryset:
            spider_count = len(p.import_jobs())
        self.message_user(request, "{0} spiders was imported successfully.".format(spider_count))

    import_spiders.short_description = "Import spiders of the selected projects"

    def item_scrapyd_count(self, obj):
        job_pks = [job.pk for job in obj.job_set.all()]
        data = job_scrapyd_ratio(job_pks)
        if data:
            values = [v[0] for v in data.values()]
            return sum(values)

    item_scrapyd_count.short_description = '已抓取数'

    def chart_href(self, obj):
        return format_html(
            '<a href={}>statistics</a>',
            "/scrapyadmin/chart/project/{0}/".format(obj.pk),
        )

    chart_href.short_description = '统计'


class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'chart_href']

    def chart_href(self, obj):
        return format_html(
            '<a href={}>statistics</a>',
            "/scrapyadmin/chart/group/{0}/".format(obj.pk),
        )

    chart_href.short_description = '统计'


class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'group', 'project', 'worker', 'cron', 'spider', 'spider_args', 'run_type',
                    'plan_run_time', 'start_date',
                    'running_jobs', 'finished_jobs', 'is_active', 'item_scrapyd_count', 'chart_href']
    readonly_fields = ('created', 'edited')
    actions = ['stop_tasks', 'start_tasks']

    def stop_tasks(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "{0} tasks was stoped successfully.".format(queryset.count()))

    stop_tasks.short_description = "停止选中的tasks"

    def start_tasks(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "{0} tasks was started successfully.".format(queryset.count()))

    start_tasks.short_description = "开始选中的tasks"

    def item_scrapyd_count(self, obj):
        job_pks = [job.pk for job in obj.job_set.all()]
        data = job_scrapyd_ratio(job_pks)
        if data:
            values = [v[0] for v in data.values()]
            return sum(values)

    item_scrapyd_count.short_description = '已抓取数'

    def chart_href(self, obj):
        return format_html(
            '<a href={}>statistics</a>',
            "/scrapyadmin/statue/task/{0}/".format(obj.pk),
        )

    chart_href.short_description = '统计'


class JobAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'task', 'worker', 'spider', 'spider_args', 'start_time', 'end_time', 'run_statue', 'get_run_time',
        'item_scrapyd_count', 'log_href', 'chart_href')

    readonly_fields = (
        'task', 'group', 'scrapyd_id', 'project', 'worker', 'spider', 'plan_run_time',
        'spider_args', 'item_scrapyd_count', 'start_time', 'end_time', 'run_time',
        'log_file')
    actions = ['stop_job']

    def has_add_permission(self, request):
        return False

    def log_href(self, obj):
        return format_html(
            '<a href={}>log</a>',
            obj.log_file,
        )

    log_href.short_description = '日志'

    def chart_href(self, obj):
        return format_html(
            '<a href={}>statistics</a>',
            "/scrapyadmin/statue/job/{0}/".format(obj.pk),
        )

    chart_href.short_description = '统计'

    def item_scrapyd_count(self, obj):
        doc = last_job_statue(obj.pk)
        if doc:
            return doc.get('item_scraped_count', 0)

    item_scrapyd_count.short_description = '已抓取数'

    def stop_job(self, request, queryset):
        for job in queryset:
            job.stop()
        self.message_user(request, "{0} jobs stop successfully.".format(len(queryset)))

    stop_job.short_description = "停止选中的job"


admin.site.register(Worker, WorkerAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Spider, SpiderAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Cron)
admin.site.register(Group, GroupAdmin)
admin.site.site_header = 'Scrapy Admin'
