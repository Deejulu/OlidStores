from .models import Category

def categories_footer(request):
    return {'categories': Category.objects.all()}
