from django.db import models

class Employee(models.Model):
    employee_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    business_unit = models.CharField(max_length=100)
    country = models.CharField(max_length=50)
    city = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"