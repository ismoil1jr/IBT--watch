from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Brand, Watch, WatchImage, Order, SiteSettings, Favorite

try:
    from .telegram_bot import send_order_status_update
except ImportError:
    def send_order_status_update(order, old_status):
        pass


class WatchImageInline(admin.TabularInline):
    model = WatchImage
    extra = 1
    fields = ['image', 'alt_text', 'order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'watch_count', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'order']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']


@admin.register(Watch)
class WatchAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'name', 'category', 'price_display', 'gender', 'is_trending', 'is_active', 'in_stock']
    list_filter = ['category', 'brand', 'gender', 'is_new', 'is_trending', 'is_active', 'in_stock']
    search_fields = ['name', 'description', 'sku']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_trending', 'is_active', 'in_stock']
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    inlines = [WatchImageInline]
    
    fieldsets = (
        ('Asosiy', {'fields': ('name', 'slug', 'sku', 'category', 'brand')}),
        ('Tavsif', {'fields': ('short_description', 'description')}),
        ('Narx', {'fields': ('price', 'old_price')}),
        ('Xususiyatlar', {'fields': ('gender', 'condition')}),
        ('Rasm', {'fields': ('image',)}),
        ('Statuslar', {'fields': ('is_new', 'is_trending', 'is_featured', 'is_active', 'in_stock')}),
        ('Statistika', {'fields': ('views_count', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:50px;border-radius:8px;"/>', obj.image.url)
        return "-"
    image_preview.short_description = "Rasm"
    
    def price_display(self, obj):
        price_str = "{:,.0f}".format(float(obj.price))
        if obj.old_price:
            old_price_str = "{:,.0f}".format(float(obj.old_price))
            discount = obj.discount_percent or 0
            return format_html(
                '<del style="color:#999">{}</del><br><b style="color:#D4AF37">{}</b> <span style="color:#E53935">-{}%</span>',
                old_price_str, price_str, discount
            )
        return format_html('<b style="color:#D4AF37">{}</b>', price_str)
    price_display.short_description = "Narxi"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'watch', 'price_display', 'status_badge', 'telegram_badge', 'created_at']
    list_filter = ['status', 'telegram_sent', 'created_at']
    search_fields = ['order_number', 'full_name', 'phone', 'watch__name']
    readonly_fields = ['order_number', 'watch', 'full_name', 'phone', 'address', 'product_url', 'product_price', 'telegram_sent', 'telegram_message_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def price_display(self, obj):
        if obj.product_price:
            price_str = "{:,.0f}".format(float(obj.product_price))
            return format_html('<b style="color:#D4AF37">{}</b>', price_str)
        return "-"
    price_display.short_description = "Narxi"
    
    def status_badge(self, obj):
        colors = {
            'new': '#2196F3', 'confirmed': '#4CAF50', 'processing': '#FF9800',
            'shipped': '#9C27B0', 'delivered': '#00BCD4', 
            'completed': '#4CAF50', 'cancelled': '#F44336',
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background:{};color:#fff;padding:4px 10px;border-radius:10px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Holati"
    
    def telegram_badge(self, obj):
        if obj.telegram_sent:
            return format_html('<span style="color:#4CAF50">✅</span>')
        return format_html('<span style="color:#F44336">❌</span>')
    telegram_badge.short_description = "TG"
    
    def save_model(self, request, obj, form, change):
        if change:
            try:
                old_obj = Order.objects.get(pk=obj.pk)
                old_status = old_obj.status
                super().save_model(request, obj, form, change)
                if old_status != obj.status:
                    send_order_status_update(obj, old_status)
            except:
                super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'phone', 'telegram_username']
    
    fieldsets = (
        ('Sayt', {'fields': ('site_name', 'site_description')}),
        ('Kontakt', {'fields': ('phone', 'telegram_username', 'telegram_channel', 'instagram_username')}),
        ('Telegram Bot', {'fields': ('telegram_bot_token', 'telegram_chat_id')}),
        ('SEO', {'fields': ('meta_title', 'meta_description', 'meta_keywords'), 'classes': ('collapse',)}),
    )
    
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'watch', 'created_at']
    list_filter = ['created_at']


admin.site.site_header = "I.B.T Watches Admin"
admin.site.site_title = "I.B.T Watches"
admin.site.index_title = "Boshqaruv paneli"