from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.models import SiteContent
from core.forms import SiteContentForm
from admin_dashboard.views import admin_role_required

def get_or_create_content(key, title=None):
    obj, created = SiteContent.objects.get_or_create(key=key, defaults={'title': title or key.title()})
    return obj

@admin_role_required
