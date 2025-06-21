from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    Domain,
    DomainController,
    OrganizationalUnit,
    ADUser,
    ADGroup,
    ServiceAccount,
)

# 1. Define a Resource for each model
class DomainResource(resources.ModelResource):
    class Meta:
        model = Domain
        import_id_fields = ('name',)
        fields = ('id', 'name',)

class DomainControllerResource(resources.ModelResource):
    class Meta:
        model = DomainController
        import_id_fields = ('domain', 'location')
        fields = ( 'id', 'domain', 'hostname', 'location',)

class OrganizationalUnitResource(resources.ModelResource):
    class Meta:
        model = OrganizationalUnit
        import_id_fields = ('name', 'domain')
        fields = ('id', 'name', 'parent', 'domain',)

class ADUserResource(resources.ModelResource):
    class Meta:
        model = ADUser
        import_id_fields = ('sAMAccountName',)
        fields = (
            'id',
            'employee',
            'sAMAccountName',
            'display_name',
            'mail',
            'department',
            'country',
            'ou',
        )

class ADGroupResource(resources.ModelResource):
    class Meta:
        model = ADGroup
        import_id_fields = ('name',)
        fields = ('id', 'name', 'description', 'scope',)

class ServiceAccountResource(resources.ModelResource):
    class Meta:
        model = ServiceAccount
        import_id_fields = ('name',)
        fields = ('id', 'name', 'purpose', 'domain', 'created_for',)

# 2. Create Admin classes that use ImportExportModelAdmin
@admin.register(Domain)
class DomainAdmin(ImportExportModelAdmin):
    resource_class = DomainResource
    list_display = ('name',)

@admin.register(DomainController)
class DomainControllerAdmin(ImportExportModelAdmin):
    resource_class = DomainControllerResource
    list_display = ('hostname', 'domain', 'location',)

@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(ImportExportModelAdmin):
    resource_class = OrganizationalUnitResource
    list_display = ('name', 'domain', 'parent',)

@admin.register(ADUser)
class ADUserAdmin(ImportExportModelAdmin):
    resource_class = ADUserResource
    list_display = ('sAMAccountName', 'display_name', 'mail', 'department', 'country',)

@admin.register(ADGroup)
class ADGroupAdmin(ImportExportModelAdmin):
    resource_class = ADGroupResource
    list_display = ('name', 'scope',)

@admin.register(ServiceAccount)
class ServiceAccountAdmin(ImportExportModelAdmin):
    resource_class = ServiceAccountResource
    list_display = ('name', 'domain', 'created_for',)
    
