from django.contrib import admin
from .models import Organization, EmissionRecord, Recommendation

admin.site.register(Organization)
admin.site.register(EmissionRecord)
admin.site.register(Recommendation)
