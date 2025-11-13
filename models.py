from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

SCOPE_CHOICES = [
    ('scope1', 'Scope 1'),
    ('scope2', 'Scope 2'),
    ('scope3', 'Scope 3'),
]


class Organization(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class EmissionRecord(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='records')
    timestamp = models.DateField()
    activity = models.CharField(max_length=200, blank=True)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='scope1')
    value = models.FloatField(help_text="Emissions amount (metric tons CO2e)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.organization} - {self.timestamp} - {self.value}"


class Recommendation(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='recommendations')
    title = models.CharField(max_length=200)
    detail = models.TextField()
    estimated_reduction = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    applied = models.BooleanField(default=False)

    def __str__(self):
        return self.title
