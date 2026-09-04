from django.contrib import admin
from .models import BusySlot, Meeting

admin.site.register(Meeting)
admin.site.register(BusySlot)

