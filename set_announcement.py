from core.models import SiteContent

banner = SiteContent.objects.filter(key='homepage_banner').first()
if banner:
    banner.announcement_text = '<i class="fas fa-truck me-2"></i>Free shipping on orders over ₦15,000 | <i class="fas fa-tag me-2"></i>Use code DFLOW10 for 10% off'
    banner.save()
    print('Announcement text set successfully!')
else:
    print('No homepage_banner found')
