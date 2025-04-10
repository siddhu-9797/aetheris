# generate_synthetic_ad.py
import os
import django
import random
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticad.models import Domain, DomainController, OrganizationalUnit, ADUser, ADGroup, ServiceAccount
from syntheticemployees.models import Employee

# === Constants ===
DC_COUNTRY_MAPPING = {
    "USA": 2,
    "UK": 2,
    "Germany": 2,
    "Japan": 1
}

GROUP_SCOPES = ["global", "domain-local", "universal"]
SERVICE_ACCOUNT_PURPOSES = [
    "Database connection for Finance DB",
    "Web application pool account",
    "Automation runner for CI/CD",
    "Monitoring agent",
    "Backup service account"
]

# === Step 1: Create Domains and Domain Controllers ===
def create_domains_and_dcs():
    print("[*] Creating Domains and Domain Controllers...")
    root_domain = Domain.objects.get_or_create(name="aetheris.security")[0]

    for country, count in DC_COUNTRY_MAPPING.items():
        for i in range(count):
            hostname = f"dc-{country.lower()}-{i+1}"
            DomainController.objects.get_or_create(
                domain=root_domain,
                hostname=hostname,
                location=country
            )
    print("  [✓] Domains and Domain Controllers created.")

# === Step 2: Create OU Hierarchy ===
def create_ous():
    print("[*] Creating Organizational Units...")
    domain = Domain.objects.get(name="aetheris.security")
    country_ou = {}

    countries = Employee.objects.values_list("country", flat=True).distinct()
    for country in countries:
        country_node = OrganizationalUnit.objects.get_or_create(
            name=country,
            parent=None,
            domain=domain
        )[0]
        country_ou[country] = country_node

        departments = Employee.objects.filter(country=country).values_list("department", flat=True).distinct()
        for dept in departments:
            OrganizationalUnit.objects.get_or_create(
                name=dept,
                parent=country_node,
                domain=domain
            )
    print("  [✓] Organizational Units created.")

# === Step 3: Create AD Users ===
def create_ad_users():
    print("[*] Creating AD users for all employees...")
    domain = Domain.objects.get(name="aetheris.security")

    for emp in Employee.objects.all():
        try:
            country_ou = OrganizationalUnit.objects.get(name=emp.country, domain=domain, parent=None)
            dept_ou = OrganizationalUnit.objects.get(name=emp.department, domain=domain, parent=country_ou)
        except OrganizationalUnit.DoesNotExist:
            print(f"[!] OU not found for {emp.department} in {emp.country}, skipping {emp.employee_id}")
            continue

        ADUser.objects.get_or_create(
            employee=emp,
            defaults={
                "sAMAccountName": emp.employee_id.lower(),
                "display_name": emp.name,
                "mail": emp.email,
                "department": emp.department,
                "country": emp.country,
                "ou": dept_ou
            }
        )
    print("  [✓] AD users created.")

# === Step 4: Create AD Groups ===
def create_ad_groups():
    print("[*] Creating AD groups...")
    ad_users = list(ADUser.objects.all())

    # Department-based groups
    departments = Employee.objects.values_list("department", flat=True).distinct()
    for dept in departments:
        group_name = f"{dept.replace(' ', '')}-Users"
        group, _ = ADGroup.objects.get_or_create(
            name=group_name,
            defaults={
                "description": f"Users in {dept} department",
                "scope": random.choice(GROUP_SCOPES)
            }
        )
        # Randomly assign 15–30 users to this group
        members = random.sample(ad_users, k=min(len(ad_users), random.randint(15, 30)))
        group.members.add(*members)

    print("  [✓] AD groups created.")

# === Step 5: Create Service Accounts ===
def create_service_accounts(n=25):
    print(f"[*] Creating {n} Service Accounts...")
    domain = Domain.objects.get(name="aetheris.security")
    all_ous = OrganizationalUnit.objects.all()

    for i in range(n):
        name = f"svc_account_{i+1}"
        purpose = random.choice(SERVICE_ACCOUNT_PURPOSES)
        ou = random.choice(all_ous)

        ServiceAccount.objects.get_or_create(
            name=name,
            purpose=purpose,
            domain=domain,
            created_for=ou
        )

    print("  [✓] Service accounts created.")

# === Main Entry Point ===
if __name__ == "__main__":
    create_domains_and_dcs()
    create_ous()
    create_ad_users()
    create_ad_groups()
    create_service_accounts()
    print("[✓] Synthetic Active Directory generation complete.")
