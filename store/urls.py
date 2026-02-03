from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('watches/', views.all_watches, name='all_watches'),
    path('watch/<int:pk>/', views.product_detail, name='product_detail'),
    path('about/', views.about, name='about'),
    # path('category/<slug:slug>/', views.category_watches, name='category_watches'),
    path('api/order/', views.submit_order, name='submit_order'),
    # path('api/search/', views.search_watches, name='search_watches'),
]