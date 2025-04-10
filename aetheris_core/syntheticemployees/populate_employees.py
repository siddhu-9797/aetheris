import os
import sys
import django
import random
from faker import Faker

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticemployees.models import Employee

fake = Faker()

COUNTRIES = ["USA", "UK", "Germany", "Japan"]
CITIES = {
    "USA": ["New York", "Los Angeles", "Chicago"],
    "UK": ["London", "Manchester", "Edinburgh"],
    "Germany": ["Berlin", "Munich", "Frankfurt"],
    "Japan": ["Tokyo", "Osaka", "Kyoto"]
}
DEPARTMENTS = {
    "Finance": ["Accounting", "Treasury", "Audit"],
    "HR": ["Recruitment", "Payroll", "Employee Relations"],
    "Engineering": ["Software Development", "Hardware Engineering", "QA"],
    "Sales": ["Sales Team A", "Sales Team B", "Sales Operations"],
    "Marketing": ["Digital Marketing", "Content Creation", "PR"],
    "IT": ["Networking", "Systems Administration", "Security"],
    "Operations": ["Logistics", "Supply Chain", "Manufacturing"]
}
ALL_DEPARTMENTS = [d for sub in DEPARTMENTS.values() for d in sub]

def sync_employees():
    used_emails = set(Employee.objects.values_list("email", flat=True))  # existing emails

    for i in range(1, 2001):
        employee_id = f"EMP-{i:04d}"

        # Generate a unique email
        attempts = 0
        while True:
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@aetheris.security"
            if email not in used_emails:
                used_emails.add(email)
                break
            attempts += 1
            if attempts > 10:
                print(f"[!] Could not generate unique email after 10 attempts for ID {employee_id}. Skipping.")
                continue

        full_name = f"{first_name} {last_name}"
        country = random.choice(COUNTRIES)
        city = random.choice(CITIES[country])
        department = random.choice(ALL_DEPARTMENTS)

        Employee.objects.update_or_create(
            employee_id=employee_id,
            defaults={
                "name": full_name,
                "email": email,
                "country": country,
                "city": city,
                "department": department
            }
        )

    print("[✓] Employee sync complete. All emails are unique.")

if __name__ == "__main__":
    sync_employees()
