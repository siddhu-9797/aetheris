import random
import sys
from faker import Faker

import os
import django

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticcmdb.models import ConfigurationItem
from syntheticad.models import ADUser, DomainController
from syntheticemployees.models import Employee


fake = Faker()

# === Department to AD Group mapping for asset type control ===
# Asset mapping and usage rules from uploaded CMDB_Assets.txt
ASSET_TYPE_RULES = {
    "Finance": ["Workstation", "Laptop", "Printer", "Server", "Enterprise Application"],
    "HR": ["Workstation", "Laptop", "Printer", "Enterprise Application"],
    "IT": ["Server", "Switch", "Firewall", "Router", "Hypervisor", "VM", "Storage Array", "Workstation"],
    "Sales": ["Laptop", "Mobile Device", "Workstation", "Enterprise Application"],
    "Marketing": ["Laptop", "Mobile Device", "Workstation"],
    "Engineering": ["Laptop", "Workstation", "VM", "Server", "Container", "Enterprise Application"],
    "QA": ["Workstation", "Server", "VM", "Container"],
    "Security": ["Firewall", "SIEM", "Workstation", "Server", "Storage Array"],
    "Facilities": ["IP Camera", "Switch", "Router", "Building Access Control"]
}

ASSET_METADATA = {
    "Workstation": {
        "os": ["Windows 10 Enterprise", "Windows 11 Pro", "macOS Ventura"],
        "hardware": ["Dell", "HP", "Lenovo"],
        "software": ["Office 365", "Chrome", "Endpoint Security"]
    },
    "Firewall": {
        "os": ["PAN-OS 10.2", "FortiOS 7.2"],
        "hardware": ["Palo Alto Networks", "Fortinet", "Cisco"],
        "software": ["Firewall", "VPN"]
    },
    "Laptop": {
        "os": ["Windows 11 Pro", "macOS Sonoma"],
        "hardware": ["Apple", "Dell", "Lenovo"],
        "software": ["Office 365", "Slack"]
    },
    "Server": {
        "os": ["Windows Server 2019", "RedHat Enterprise Linux", "Ubuntu Server 22.04"],
        "hardware": ["Dell", "HP", "Supermicro"],
        "software": ["Active Directory", "Docker", "Database"]
    },
    "Switch": {
        "os": ["Cisco IOS", "JunOS"],
        "hardware": ["Cisco", "Juniper"],
        "software": ["Switching Software"]
    },
    "Router": {
        "os": ["Cisco IOS XR", "VyOS"],
        "hardware": ["Cisco", "Ubiquiti"],
        "software": ["Routing Software"]
    },
    "Hypervisor": {
        "os": ["VMware ESXi", "Microsoft Hyper-V"],
        "hardware": ["Dell", "HP"],
        "software": ["vCenter", "Hyper-V Manager"]
    },
    "VM": {
        "os": ["Ubuntu 22.04", "CentOS 7", "Windows Server 2016"],
        "hardware": ["Virtual"],
        "software": ["Web Server", "Database", "Security Agent"]
    },
    "Storage Array": {
        "os": ["NetApp ONTAP", "Dell Unity OS"],
        "hardware": ["NetApp", "Dell"],
        "software": ["Storage Manager", "Backup Agent"]
    },
    "Mobile Device": {
        "os": ["iOS 17", "Android 14"],
        "hardware": ["Apple", "Samsung"],
        "software": ["Email", "Mobile Security"]
    },
    "Enterprise Application": {
        "os": ["Cloud"],
        "hardware": ["SaaS"],
        "software": ["Salesforce", "Workday", "SAP", "Netsuite"]
    },
    "IP Camera": {
        "os": ["Embedded Linux"],
        "hardware": ["Axis", "Hikvision"],
        "software": ["Surveillance"]
    },
    "Container": {
        "os": ["Alpine Linux"],
        "hardware": ["Virtual"],
        "software": ["Microservice"]
    },
    "SIEM": {
        "os": ["Linux"],
        "hardware": ["HP", "Dell"],
        "software": ["Splunk", "ELK Stack", "LogRhythm"]
    },
    "Printer": {
        "os": ["Embedded"],
        "hardware": ["HP", "Canon"],
        "software": ["Print Management"]
    },
    "Building Access Control": {
        "os": ["Firmware"],
        "hardware": ["Honeywell", "Bosch"],
        "software": ["Access Control"]
    }
}

# Try to match a DomainController by city or fallback to country
matching_dcs = DomainController.objects.filter(location__iexact=Employee.country)
# Fallback: pick random if nothing matches (to avoid crash)
domain_controller = matching_dcs.order_by("?").first() or DomainController.objects.order_by("?").first()

def generate_hostname(asset_type, domain_controller):
    base = asset_type.lower().replace(" ", "")
    dc_hostname = domain_controller.hostname.lower().replace(" ", "-")
    return f"{base}-{random.randint(10, 99)}.{dc_hostname}.aetheris.security"


def generate_semver():
    return f"{random.randint(1, 5)}.{random.randint(0, 20)}.{random.randint(0, 10)}"

def regenerate_cmdb():
    ConfigurationItem.objects.all().delete()
    assets_created = 0

    for ad_user in ADUser.objects.select_related("employee", "ou").all():
        emp = ad_user.employee
        dept = emp.department
        allowed_assets = ASSET_TYPE_RULES.get(dept, ["Workstation"])

        for _ in range(random.randint(1, 2)):
            asset_type = random.choice(allowed_assets)
            hostname = generate_hostname(asset_type, domain_controller)
            ip_address = fake.ipv4_private()

            os_choice = random.choice(ASSET_METADATA[asset_type]["os"])
            hardware_vendor = random.choice(ASSET_METADATA[asset_type]["hardware"])
            software = ASSET_METADATA[asset_type]["software"]

            ConfigurationItem.objects.create(
                hostname = hostname,
                asset_type=asset_type,
                os=os_choice,
                os_version=generate_semver(),
                hardware_vendor=hardware_vendor,
                model=fake.word().capitalize() + str(random.randint(100, 999)),
                software=software,
                software_version=generate_semver(),
                employee_id=emp.employee_id,
                employee_email=emp.email,
                city=emp.city,
                country=emp.country,
                department=emp.department,
                ip_address=ip_address,
                domain=ad_user.ou.domain if ad_user.ou else None,
                ad_user=ad_user,
                business_unit=emp.department,
                security_software=", ".join(software),
                network_zone=random.choice(["Dev", "Test", "Prod", "DMZ"]),
                connectivity=random.choice(["Wired", "Wireless", "VPN"]),
                owner=ad_user.display_name,
                security_posture=random.choice(["compliant", "non-compliant", "patch-needed"]),
            )

            assets_created += 1

    print(f"[✓] {assets_created} realistic CMDB assets generated.")

if __name__ == "__main__":
    regenerate_cmdb()
