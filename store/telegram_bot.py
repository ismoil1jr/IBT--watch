"""
Telegram Bot Integration
Buyurtmalarni admin telegramiga yuborish
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger('watches')


def get_telegram_settings():
    """Telegram sozlamalarini olish"""
    try:
        from .models import SiteSettings
        site_settings = SiteSettings.get_settings()
        return {
            'bot_token': site_settings.telegram_bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', ''),
            'chat_id': site_settings.telegram_chat_id or getattr(settings, 'TELEGRAM_CHAT_ID', ''),
        }
    except Exception as e:
        logger.error(f"Telegram sozlamalarini olishda xato: {e}")
        return {
            'bot_token': getattr(settings, 'TELEGRAM_BOT_TOKEN', ''),
            'chat_id': getattr(settings, 'TELEGRAM_CHAT_ID', ''),
        }


def send_telegram_message(message, parse_mode='HTML'):
    """
    Telegramga xabar yuborish
    
    Returns:
        tuple: (success: bool, message_id: str or None)
    """
    tg = get_telegram_settings()
    bot_token = tg['bot_token']
    chat_id = tg['chat_id']
    
    if not bot_token or not chat_id:
        logger.warning("Telegram bot token yoki chat_id sozlanmagan")
        return False, None
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': False,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('ok'):
            message_id = data.get('result', {}).get('message_id')
            logger.info(f"Telegram xabari yuborildi: {message_id}")
            return True, str(message_id)
        else:
            logger.error(f"Telegram xatosi: {data}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram so'rovida xato: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Telegram xabar yuborishda xato: {e}")
        return False, None


def send_order_to_telegram(order):
    """
    Yangi buyurtmani Telegramga yuborish
    """
    message = f"""
🛒 <b>YANGI BUYURTMA!</b>

📋 <b>Buyurtma:</b> #{order.order_number}

⌚ <b>Soat:</b> {order.watch.name}
💰 <b>Narxi:</b> {order.product_price:,.0f} so'm

👤 <b>Mijoz:</b>
├ <b>Ism:</b> {order.full_name}
├ <b>Tel:</b> {order.phone}
└ <b>Manzil:</b> {order.address}

🔗 <b>Havola:</b>
{order.product_url}

📅 <b>Sana:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}

━━━━━━━━━━━━━━━━
✅ Mijozga tez bog'laning!
"""
    
    success, message_id = send_telegram_message(message)
    
    if success and message_id:
        order.telegram_message_id = message_id
        order.telegram_sent = True
        order.save(update_fields=['telegram_message_id', 'telegram_sent'])
    
    return success


def send_order_status_update(order, old_status):
    """Buyurtma statusi o'zgarganda xabar yuborish"""
    status_emojis = {
        'new': '🆕', 'confirmed': '✅', 'processing': '⚙️',
        'shipped': '🚚', 'delivered': '📦', 'completed': '🎉', 'cancelled': '❌',
    }
    status_names = {
        'new': 'Yangi', 'confirmed': 'Tasdiqlangan', 'processing': 'Jarayonda',
        'shipped': "Jo'natildi", 'delivered': 'Yetkazildi', 
        'completed': 'Bajarildi', 'cancelled': 'Bekor qilindi',
    }
    
    emoji = status_emojis.get(order.status, '📝')
    new_status = status_names.get(order.status, order.status)
    old = status_names.get(old_status, old_status)
    
    message = f"""
{emoji} <b>STATUS O'ZGARDI</b>

📋 #{order.order_number}
⌚ {order.watch.name}
👤 {order.full_name}

📊 {old} ➡️ <b>{new_status}</b>
"""
    
    success, _ = send_telegram_message(message)
    return success


def test_telegram_connection():
    """Telegram ulanishini tekshirish"""
    tg = get_telegram_settings()
    
    if not tg['bot_token']:
        return {'success': False, 'message': 'Bot token sozlanmagan'}
    if not tg['chat_id']:
        return {'success': False, 'message': 'Chat ID sozlanmagan'}
    
    try:
        url = f"https://api.telegram.org/bot{tg['bot_token']}/getMe"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            bot_username = data.get('result', {}).get('username', 'Unknown')
            return {'success': True, 'message': f'Ulangan: @{bot_username}'}
        return {'success': False, 'message': data.get('description', 'Xatolik')}
    except Exception as e:
        return {'success': False, 'message': str(e)}