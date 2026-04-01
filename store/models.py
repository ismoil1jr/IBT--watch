"""
IBT Watches - Database Models
"""
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth.models import User
import random
import string


class Category(models.Model):
    """Soat kategoriyalari"""
    name = models.CharField(max_length=100, verbose_name="Kategoriya nomi")
    slug = models.SlugField(unique=True, blank=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Rasm")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def watch_count(self):
        return self.watches.filter(is_active=True).count()


class Brand(models.Model):
    """Soat brendlari"""
    name = models.CharField(max_length=100, verbose_name="Brend nomi")
    slug = models.SlugField(unique=True, blank=True, verbose_name="Slug")
    logo = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name="Logo")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Brend"
        verbose_name_plural = "Brendlar"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Watch(models.Model):
    """Soat modeli - asosiy mahsulot"""
    GENDER_CHOICES = [
        ('male', 'Erkaklar'),
        ('female', 'Ayollar'),
        ('unisex', 'Unisex'),
    ]
    
    CONDITION_CHOICES = [
        ('new', 'Yangi'),
        ('like_new', 'Yangiday'),
        ('good', 'Yaxshi'),
    ]
    
    # Asosiy ma'lumotlar
    name = models.CharField(max_length=200, verbose_name="Soat nomi")
    slug = models.SlugField(unique=True, blank=True, verbose_name="Slug")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="SKU")
    
    # Kategoriya va Brend
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, 
        related_name='watches', verbose_name="Kategoriya"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, 
        related_name='watches', blank=True, null=True, verbose_name="Brend"
    )
    
    # Tavsif
    description = models.TextField(verbose_name="Tavsif")
    short_description = models.CharField(max_length=300, blank=True, verbose_name="Qisqa tavsif")
    
    # Narx
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Narxi (so'm)")
    old_price = models.DecimalField(
        max_digits=12, decimal_places=0, 
        blank=True, null=True, verbose_name="Eski narxi"
    )
    
    # Xususiyatlar
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unisex', verbose_name="Jinsi")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new', verbose_name="Holati")
    
    # Rasm
    image = models.ImageField(upload_to='watches/', verbose_name="Asosiy rasm")
    
    # Statuslar
    is_new = models.BooleanField(default=False, verbose_name="Yangi mahsulot")
    is_trending = models.BooleanField(default=False, verbose_name="Trendda")
    is_featured = models.BooleanField(default=False, verbose_name="Tanlangan")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    in_stock = models.BooleanField(default=True, verbose_name="Sotuvda bor")
    
    # Statistika
    views_count = models.PositiveIntegerField(default=0, verbose_name="Ko'rishlar")
    
    # Vaqt
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Soat"
        verbose_name_plural = "Soatlar"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Watch.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'pk': self.pk})
    
    @property
    def discount_percent(self):
        """Chegirma foizini hisoblash"""
        if self.old_price and self.old_price > self.price:
            discount = ((self.old_price - self.price) / self.old_price) * 100
            return int(discount)
        return None
    
    @property
    def is_on_sale(self):
        """Chegirmada yoki yo'q"""
        return self.old_price is not None and self.old_price > self.price
    
    def increment_views(self):
        """Ko'rishlar sonini oshirish"""
        self.views_count += 1
        self.save(update_fields=['views_count'])


class WatchImage(models.Model):
    """Qo'shimcha soat rasmlari"""
    watch = models.ForeignKey(Watch, on_delete=models.CASCADE, related_name='images', verbose_name="Soat")
    image = models.ImageField(upload_to='watches/gallery/', verbose_name="Rasm")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="Alt text")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Soat rasmi"
        verbose_name_plural = "Soat rasmlari"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.watch.name} - Rasm {self.order}"


class Order(models.Model):
    """Buyurtmalar"""
    STATUS_CHOICES = [
        ('new', 'Yangi'),
        ('confirmed', 'Tasdiqlangan'),
        ('processing', 'Jarayonda'),
        ('shipped', "Jo'natildi"),
        ('delivered', 'Yetkazildi'),
        ('completed', 'Bajarildi'),
        ('cancelled', 'Bekor qilindi'),
    ]
    
    # Buyurtma raqami
    order_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Buyurtma raqami")
    
    # Mahsulot
    watch = models.ForeignKey(Watch, on_delete=models.CASCADE, related_name='orders', verbose_name="Soat")
    
    # Mijoz ma'lumotlari
    full_name = models.CharField(max_length=200, verbose_name="To'liq ism")
    phone = models.CharField(max_length=20, verbose_name="Telefon raqam")
    address = models.TextField(verbose_name="Manzil")
    
    # Buyurtma ma'lumotlari
    product_url = models.URLField(verbose_name="Mahsulot havolasi")
    product_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Mahsulot narxi")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Holati")
    
    # Telegram
    telegram_sent = models.BooleanField(default=False, verbose_name="Telegramga yuborildi")
    telegram_message_id = models.CharField(max_length=50, blank=True, verbose_name="Telegram xabar ID")
    
    # Izohlar
    admin_notes = models.TextField(blank=True, verbose_name="Admin izohlari")
    
    # Vaqt
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.order_number} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # IBT-XXXXX formatida
            while True:
                number = ''.join(random.choices(string.digits, k=5))
                order_number = f"IBT-{number}"
                if not Order.objects.filter(order_number=order_number).exists():
                    self.order_number = order_number
                    break
        
        if not self.product_price and self.watch:
            self.product_price = self.watch.price
            
        super().save(*args, **kwargs)


class Favorite(models.Model):
    """Sevimli soatlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name="Foydalanuvchi")
    watch = models.ForeignKey(Watch, on_delete=models.CASCADE, related_name='favorites', verbose_name="Soat")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sevimli"
        verbose_name_plural = "Sevimlilar"
        unique_together = ['user', 'watch']

    def __str__(self):
        return f"{self.user.first_name} — {self.watch.name}"


class SiteSettings(models.Model):
    """Sayt sozlamalari - Singleton"""
    site_name = models.CharField(max_length=100, default="I.B.T Watches", verbose_name="Sayt nomi")
    site_description = models.TextField(blank=True, verbose_name="Sayt tavsifi")
    
    # Kontakt
    phone = models.CharField(max_length=20, default="+998909182842", verbose_name="Telefon")
    telegram_username = models.CharField(max_length=100, default="boburIBT", verbose_name="Telegram username")
    telegram_channel = models.CharField(max_length=100, default="IBTwatches", verbose_name="Telegram kanal")
    instagram_username = models.CharField(max_length=100, default="i.b.t_watches", verbose_name="Instagram")
    
    # Telegram Bot
    telegram_bot_token = models.CharField(max_length=200, blank=True, verbose_name="Bot Token")
    telegram_chat_id = models.CharField(max_length=50, blank=True, verbose_name="Chat ID")
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name="Meta Title")
    meta_description = models.TextField(blank=True, verbose_name="Meta Description")
    meta_keywords = models.CharField(max_length=500, blank=True, verbose_name="Meta Keywords")
    
    class Meta:
        verbose_name = "Sayt sozlamalari"
        verbose_name_plural = "Sayt sozlamalari"
    
    def __str__(self):
        return self.site_name
    
    def save(self, *args, **kwargs):
        # Faqat bitta bo'lishi kerak
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError("Faqat bitta SiteSettings bo'lishi mumkin")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Sozlamalarni olish yoki yaratish"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings