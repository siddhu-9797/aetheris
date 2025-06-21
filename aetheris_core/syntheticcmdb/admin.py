# your_app/admin.py

from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import ConfigurationItem
from syntheticad.models import ADUser, Domain

class ConfigurationItemResource(resources.ModelResource):
    class Meta:
        model = ConfigurationItem
        # Use hostname as the natural key for idempotency
        import_id_fields = ('hostname',)
        # Expose both simple and FK lookups via __ notation
        fields = (
            'id',
            'asset_type',
            'hostname',
            'os',
            'os_version',
            'software',
            'software_version',
            'hardware_vendor',
            'model',
            'network_zone',
            'connectivity',
            'security_software',
            'ip_address',
            'business_unit',
            'department',
            'employee_id',
            'employee_email',
            'country',
            'city',
            'ad_user',   # import by sAMAccountName
            'domain',              # import by Domain.name
            'owner',
            'security_posture',
            'last_updated',
        )

@admin.register(ConfigurationItem)
class ConfigurationItemAdmin(ImportExportModelAdmin):
    resource_class = ConfigurationItemResource

    # Surface the most important columns in the changelist view
    list_display = (
        'hostname',
        'asset_type',
        'os',
        'os_version',
        'model',
        'network_zone',
        'connectivity',
        'security_software',
        'ad_user',
        'domain',
        'security_posture',
        'last_updated',
    )
    list_filter = ('security_posture', 'domain', 'network_zone')
    search_fields = ('hostname', 'asset_type', 'owner', 'employee_email')
