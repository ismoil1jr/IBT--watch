"""
Context Processors - Global context for all templates
"""
from .models import SiteSettings, Category


def site_settings(request):
    """Sayt sozlamalarini barcha sahifalarga berish"""
    try:
        settings = SiteSettings.get_settings()
    except:
        settings = None
    
    categories = Category.objects.filter(is_active=True)
    
    return {
        'settings': settings,
        'categories': categories,
    }