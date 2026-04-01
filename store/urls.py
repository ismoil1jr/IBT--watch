from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('watches/', views.all_watches, name='all_watches'),
    path('watch/<int:pk>/', views.product_detail, name='product_detail'),
    path('about/', views.about, name='about'),
    path('category/<slug:slug>/', views.category_watches, name='category_watches'),
    path('api/order/', views.submit_order, name='submit_order'),
    path('api/search/', views.search_watches, name='search_watches'),
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    # Profile & Favorites
    path('profile/', views.profile_view, name='profile'),
    path('api/favorite/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
]