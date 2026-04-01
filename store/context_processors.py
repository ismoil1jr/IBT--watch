"""
Context Processors - Global context for all templates
"""
from .models import SiteSettings, Category, Favorite


def site_settings(request):
    """Sayt sozlamalarini barcha sahifalarga berish"""
    try:
        settings = SiteSettings.get_settings()
    except:
        settings = None

    categories = Category.objects.filter(is_active=True)

    # User's favorite watch IDs (for heart button state)
    user_favorites = set()
    if request.user.is_authenticated:
        try:
            user_favorites = set(
                Favorite.objects.filter(user=request.user).values_list('watch_id', flat=True)
            )
        except Exception:
            pass

    return {
        'settings': settings,
        'categories': categories,
        'user_favorites': user_favorites,
    }