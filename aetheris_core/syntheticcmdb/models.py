from django.db import models
from syntheticad.models import ADUser, Domain

class ConfigurationItem(models.Model):
    asset_type = models.CharField(max_length=100)
    hostname = models.CharField(max_length=255)

    os = models.CharField(max_length=100)
    os_version = models.CharField(max_length=50)

    software = models.JSONField(default=list, blank=True)
    software_version = models.CharField(max_length=50)

    hardware_vendor = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    network_zone = models.CharField(max_length=100)
    connectivity = models.CharField(max_length=50)  # New
    security_software = models.CharField(max_length=100)  # New
    ip_address = models.GenericIPAddressField(null=True, blank=True)


    business_unit = models.CharField(max_length=100)
    department = models.CharField(max_length=100)  # New

    employee_id = models.CharField(max_length=20)  # New
    employee_email = models.EmailField()  # New
    country = models.CharField(max_length=50)  # New
    city = models.CharField(max_length=100)  # New
    ad_user = models.ForeignKey(ADUser, on_delete=models.SET_NULL, null=True, blank=True)
    domain = models.ForeignKey(Domain, on_delete=models.SET_NULL, null=True, blank=True)

    owner = models.CharField(max_length=100)
    security_posture = models.CharField(max_length=100, choices=[
        ('compliant', 'Compliant'),
        ('non-compliant', 'Non-Compliant'),
        ('patch-needed', 'Needs Patching'),
    ])

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hostname

