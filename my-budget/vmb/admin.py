from django.contrib import admin
from.models import Project, ExpenditureItem, ExpenditureDocument

# Register your models here.

admin.site.register(Project)
admin.site.register(ExpenditureItem)
admin.site.register(ExpenditureDocument)