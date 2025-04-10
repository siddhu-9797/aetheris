from django.db import models
from syntheticemployees.models import Employee

class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class DomainController(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    hostname = models.CharField(max_length=255)
    location = models.CharField(max_length=100)  # set to country only

    def __str__(self):
        return f"{self.hostname} ({self.location})"

class OrganizationalUnit(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.domain.name}"

class ADUser(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    sAMAccountName = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=255)
    mail = models.EmailField()
    department = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    ou = models.ForeignKey(OrganizationalUnit, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.display_name

class ADGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(ADUser, related_name="groups")
    scope = models.CharField(max_length=50, choices=[
        ('global', 'Global'),
        ('domain-local', 'Domain Local'),
        ('universal', 'Universal')
    ])

    def __str__(self):
        return self.name

class ServiceAccount(models.Model):
    name = models.CharField(max_length=255)
    purpose = models.TextField()
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    created_for = models.ForeignKey(OrganizationalUnit, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name
