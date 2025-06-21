from import_export import resources
from .models import Employee

class EmployeeResource(resources.ModelResource):
    class Meta:
        model = Employee
        # Natural key for idempotency
        import_id_fields = ('employee_id',)
        # All fields you want to support in import/export
        fields = (
            'id',
            'employee_id',
            'name',
            'email',
            'department',
            'business_unit',
            'country',
            'city',
        )


from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Employee
from .admin import EmployeeResource  # adjust import path if needed

@admin.register(Employee)
class EmployeeAdmin(ImportExportModelAdmin):
    resource_class = EmployeeResource

    # Surface key columns in the admin list view
    list_display = (
        'employee_id',
        'name',
        'email',
        'department',
        'business_unit',
        'country',
        'city',
    )
    # Quick filters for common slices of your workforce
    list_filter = ('department', 'business_unit', 'country')
    # Fast lookup by ID, name, or email
    search_fields = ('employee_id', 'name', 'email')
