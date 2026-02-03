"""
IBT Watches - Views
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Watch, Category, Brand, Order, SiteSettings
from .telegram_bot import send_order_to_telegram


def home(request):
    """Bosh sahifa"""
    # Trendda bo'lgan soatlar
    trending_watches = Watch.objects.filter(
        is_active=True, is_trending=True
    ).select_related('category', 'brand')[:8]
    
    # Agar kam bo'lsa, yangi soatlarni qo'shish
    if trending_watches.count() < 8:
        remaining = 8 - trending_watches.count()
        extra = Watch.objects.filter(is_active=True).exclude(
            id__in=trending_watches.values_list('id', flat=True)
        ).select_related('category', 'brand')[:remaining]
        trending_watches = list(trending_watches) + list(extra)
    
    # Yangi soatlar
    new_watches = Watch.objects.filter(
        is_active=True, is_new=True
    ).select_related('category', 'brand')[:4]
    
    context = {
        'trending_watches': trending_watches,
        'new_watches': new_watches,
    }
    return render(request, 'index.html', context)


def all_watches(request):
    """Barcha soatlar - filter va search"""
    watches = Watch.objects.filter(is_active=True).select_related('category', 'brand')
    
    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        watches = watches.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )
    
    # Category filter
    category_slug = request.GET.get('category', '')
    if category_slug:
        watches = watches.filter(category__slug=category_slug)
    
    # Gender filter
    gender = request.GET.get('gender', '')
    if gender in ['male', 'female', 'unisex']:
        watches = watches.filter(gender=gender)
    
    # Brand filter
    brand_slug = request.GET.get('brand', '')
    if brand_slug:
        watches = watches.filter(brand__slug=brand_slug)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = ['price', '-price', 'name', '-name', '-created_at', '-views_count']
    if sort_by in valid_sorts:
        watches = watches.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(watches, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    # Categories for filter
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    
    context = {
        'watches': page_obj,
        'categories': categories,
        'brands': brands,
        'search_query': search_query,
        'current_category': category_slug,
        'current_gender': gender,
        'current_brand': brand_slug,
        'current_sort': sort_by,
    }
    return render(request, 'all_watches.html', context)


def product_detail(request, pk):
    """Soat batafsil sahifasi"""
    watch = get_object_or_404(
        Watch.objects.select_related('category', 'brand').prefetch_related('images'),
        pk=pk, is_active=True
    )
    
    # Ko'rishlar sonini oshirish
    watch.increment_views()
    
    # O'xshash soatlar
    related_watches = Watch.objects.filter(
        is_active=True, category=watch.category
    ).exclude(pk=pk).select_related('category')[:4]
    
    context = {
        'watch': watch,
        'related_watches': related_watches,
    }
    return render(request, 'product_detail.html', context)


def about(request):
    """Biz haqimizda"""
    return render(request, 'about.html')


def category_watches(request, slug):
    """Kategoriya bo'yicha soatlar"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    watches = Watch.objects.filter(
        is_active=True, category=category
    ).select_related('category', 'brand')
    
    paginator = Paginator(watches, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {
        'category': category,
        'watches': page_obj,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'all_watches.html', context)


@require_POST
def submit_order(request):
    """Buyurtma yuborish (AJAX)"""
    try:
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        product_url = request.POST.get('product_url', '').strip()
        product_id = request.POST.get('product_id')
        
        # Validatsiya
        errors = {}
        if len(full_name) < 3:
            errors['full_name'] = "Ism kamida 3 ta belgidan iborat bo'lishi kerak"
        if len(phone) < 9:
            errors['phone'] = "To'g'ri telefon raqam kiriting"
        if len(address) < 10:
            errors['address'] = "Manzilni to'liq kiriting"
        
        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        
        # Soatni olish
        try:
            watch = Watch.objects.get(pk=product_id, is_active=True)
        except Watch.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Mahsulot topilmadi'}, status=404)
        
        # Buyurtma yaratish
        order = Order.objects.create(
            watch=watch,
            full_name=full_name,
            phone=phone,
            address=address,
            product_url=product_url,
            product_price=watch.price
        )
        
        # Telegramga yuborish
        telegram_sent = send_order_to_telegram(order)
        
        return JsonResponse({
            'success': True,
            'message': 'Buyurtma muvaffaqiyatli yuborildi!',
            'order_number': order.order_number
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def search_watches(request):
    """Soatlarni qidirish (AJAX)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    watches = Watch.objects.filter(is_active=True).filter(
        Q(name__icontains=query) | Q(brand__name__icontains=query)
    ).select_related('category')[:10]
    
    results = [{
        'id': w.pk,
        'name': w.name,
        'price': str(w.price),
        'image': w.image.url if w.image else '',
        'url': w.get_absolute_url(),
    } for w in watches]
    
    return JsonResponse({'results': results})


# Error handlers
def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)


