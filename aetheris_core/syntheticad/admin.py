from django.contrib import admin
from .models import Domain, DomainController, OrganizationalUnit, ADUser, ADGroup, ServiceAccount

admin.site.register(Domain)
admin.site.register(OrganizationalUnit)
admin.site.register(ADGroup)
admin.site.register(ServiceAccount)

@admin.register(ADUser)
class ADUserAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "employee")
    search_fields = ("employee_id", "employee")

@admin.register(DomainController)
class DomainControllerAdmin(admin.ModelAdmin):
    list_display = ("domain", "hostname", "location")
    search_fields = ("domain__name", "hostname", "location")