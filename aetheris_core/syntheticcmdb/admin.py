from django.contrib import admin
from .models import ConfigurationItem

@admin.register(ConfigurationItem)
class ConfigurationItemAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'asset_type', 'os', 'owner', 'security_posture', 'last_updated')
    search_fields = ('hostname', 'os', 'owner')
