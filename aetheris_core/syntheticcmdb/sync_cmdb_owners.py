import os
import sys
import django

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticemployees.models import Employee
from syntheticcmdb.models import ConfigurationItem

def sync_cmdb_with_employees():
    updated = 0
    missing = 0

    for ci in ConfigurationItem.objects.all():
        try:
            employee = Employee.objects.get(employee_id=ci.employee_id)
            ci.owner = employee.name
            ci.employee_email = employee.email
            ci.save()
            updated += 1
        except Employee.DoesNotExist:
            print(f"[!] No employee found for: {ci.employee_id}")
            missing += 1

    print(f"[✓] Synced {updated} Configuration Items with employee names and emails.")
    if missing:
        print(f"[!] {missing} Configuration Items had unmatched employee_ids.")

if __name__ == "__main__":
    sync_cmdb_with_employees()
