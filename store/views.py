"""
IBT Watches - Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

from .models import Watch, Category, Brand, Order, SiteSettings, Favorite
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


# ============ Favorite & Profile Views ============

@require_POST
def toggle_favorite(request, pk):
    """Sevimlilarga qo'shish/olib tashlash (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'login_required': True}, status=401)

    watch = get_object_or_404(Watch, pk=pk, is_active=True)
    fav, created = Favorite.objects.get_or_create(user=request.user, watch=watch)

    if not created:
        fav.delete()
        return JsonResponse({'success': True, 'action': 'removed', 'count': watch.favorites.count()})

    return JsonResponse({'success': True, 'action': 'added', 'count': watch.favorites.count()})


def profile_view(request):
    """Profil — sevimli soatlar"""
    if not request.user.is_authenticated:
        return redirect(f'/login/?next=/profile/')

    favorite_watches = Watch.objects.filter(
        favorites__user=request.user, is_active=True
    ).select_related('category', 'brand')

    context = {
        'favorite_watches': favorite_watches,
    }
    return render(request, 'profile.html', context)


# ============ Auth Views ============

def register_view(request):
    """Ro'yxatdan o'tish — faqat ism, telefon, parol"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '/')

        errors = {}

        if len(first_name) < 2:
            errors['first_name'] = "Ismingizni kiriting"

        clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        if len(clean_phone) < 9:
            errors['phone'] = "To'g'ri telefon raqam kiriting"
        elif User.objects.filter(username=clean_phone).exists():
            errors['phone'] = "Bu telefon raqam allaqachon ro'yxatdan o'tgan"

        if len(password) < 6:
            errors['password'] = "Parol kamida 6 ta belgidan iborat bo'lishi kerak"

        if errors:
            return render(request, 'auth/register.html', {
                'errors': errors,
                'first_name': first_name,
                'phone': phone,
                'next': next_url,
            })

        user = User.objects.create_user(
            username=clean_phone,
            password=password,
            first_name=first_name,
            last_name=phone,
        )

        login(request, user)
        messages.success(request, f"Xush kelibsiz, {first_name}!")
        return redirect(next_url if next_url else 'home')

    next_url = request.GET.get('next', '/')
    return render(request, 'auth/register.html', {'next': next_url})


def login_view(request):
    """Kirish"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '/')

        # Phone number → username
        clean = username.replace('+', '').replace(' ', '').replace('-', '')
        user = authenticate(request, username=clean, password=password)
        if not user:
            user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.first_name or user.username}!")
            return redirect(next_url if next_url else 'home')
        else:
            return render(request, 'auth/login.html', {
                'error': "Login yoki parol noto'g'ri",
                'username': username,
                'next': next_url,
            })

    next_url = request.GET.get('next', '/')
    return render(request, 'auth/login.html', {'next': next_url})


def logout_view(request):
    """Chiqish"""
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('home')


# Error handlers
def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)


