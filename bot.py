# -*- coding: utf-8 -*- #handle_callback_query  handle_game_id handle_callback_query
"""main
البوت الرئيسي للمحفظة الإلكترونية
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import config
from database import Database
from admin_commands import AdminCommands
from datetime import datetime

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
db = Database(config.DB_NAME)
admin_handler = AdminCommands()

# متغيرات عالمية لتخزين الحالة المؤقتة
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت وعرض القائمة الرئيسية"""
    user = update.effective_user
    user_data = db.get_or_create_user(user.id, user.username, user.full_name)
    
    if user_data and user_data['is_banned']:
        await update.message.reply_text("⚠️ حسابك محظور. يرجى التواصل مع الأدمن.")
        return
    
    # إنشاء لوحة المفاتيح الرئيسية
    keyboard = [
        [KeyboardButton("💰 إيداع رصيد"), KeyboardButton("👤 معلومات الحساب")],
        [KeyboardButton("🛍️ المنتجات"), KeyboardButton("👨‍💼 التحدث مع الأدمن")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = f"مرحباً {user.full_name}!\n{config.MESSAGES['welcome']}"
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user = update.effective_user
    text = update.message.text
    
    # التحقق من حالة الحظر
    user_data = db.get_or_create_user(user.id, user.username, user.full_name)
    if user_data and user_data['is_banned']:
        await update.message.reply_text("⚠️ حسابك محظور. يرجى التواصل مع الأدمن.")
        return
    
    # التحقق من حالة المستخدم
    user_id = user.id
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['action'] == 'waiting_deposit_code':
            # معالجة رمز الإيداع
            await handle_deposit_code(update, context, state['method'])
            return
        elif state['action'] == 'waiting_game_id':
            # معالجة معرف اللعبة
            await handle_game_id(update, context, state['game'], state['product'])
            return
    
    # معالجة الأزرار الرئيسية
    if text == "💰 إيداع رصيد":
        await show_deposit_methods(update, context)
    elif text == "👤 معلومات الحساب":
        await show_account_info(update, context)
    elif text == "🛍️ المنتجات":
        await show_products_menu(update, context)
    elif text == "👨‍💼 التحدث مع الأدمن":
        await contact_admin(update, context)

async def show_deposit_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طرق الإيداع"""
    keyboard = [
        [
            InlineKeyboardButton("شام كاش", callback_data="deposit_sham"),
            InlineKeyboardButton("سيرياتيل كاش", callback_data="deposit_syriatel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 اختر طريقة الإيداع:",
        reply_markup=reply_markup
    )

async def show_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات الحساب"""
    user = update.effective_user
    user_data = db.get_or_create_user(user.id, user.username, user.full_name)
    
    if user_data:
        info = f"""
👤 **معلومات الحساب**

📛 الاسم: {user_data['full_name']}
🆔 المعرف: `{user_data['user_id']}`
💰 الرصيد: {user_data['balance']} ليرة سورية
🛒 عدد المشتريات: {user_data['total_purchases']}
📅 تاريخ الإنشاء: {user_data['created_at']}
        """
        await update.message.reply_text(info, parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ لم يتم العثور على حسابك.")

async def show_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المنتجات"""
    keyboard = [
        [
            InlineKeyboardButton("🎮 PUBG UC", callback_data="products_pubg"),
            InlineKeyboardButton("🔥 Free Fire", callback_data="products_freefire")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛍️ اختر نوع المنتجات:",
        reply_markup=reply_markup
    )

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التواصل مع الأدمن"""
    await update.message.reply_text(
        f"👨‍💼 للتواصل مع الأدمن:\n{config.ADMIN_USERNAME}"
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استعلامات الزر الداخلي"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    if data.startswith("admin_approve_purchase_"):
        request_id = int(data.split("_")[3])
        await admin_handle_purchase(query, context, request_id, "approved")
    
    elif data.startswith("admin_reject_purchase_"):
        request_id = int(data.split("_")[3])
        await admin_handle_purchase(query, context, request_id, "rejected")
    # التحقق من حالة الحظر
    user_data = db.get_or_create_user(user.id, user.username, user.full_name)
    if user_data and user_data['is_banned']:
        await query.edit_message_text("⚠️ حسابك محظور. يرجى التواصل مع الأدمن.")
        return
    
    if data.startswith("deposit_"):
        # طرق الإيداع
        method = data.split("_")[1]
        await handle_deposit_method(query, context, method)
    
    elif data.startswith("products_"):
        # قائمة المنتجات
        game = data.split("_")[1]
        await show_game_products(query, context, game)
    
    elif data.startswith("buy_"):
        # شراء منتج
        _, game, product = data.split("_")
        await start_purchase_process(query, context, game, product)
    
    elif data.startswith("admin_approve_deposit_"):
        # موافقة الأدمن على الإيداع
        request_id = int(data.split("_")[3])
        await admin_handle_deposit(query, context, request_id, "approved")
    
    elif data.startswith("admin_reject_deposit_"):
        # رفض الأدمن للإيداع
        request_id = int(data.split("_")[3])
        await admin_handle_deposit(query, context, request_id, "rejected")
    
    elif data.startswith("admin_approve_purchase_"):
        # موافقة الأدمن على الشراء
        request_id = int(data.split("_")[3])
        await admin_handle_purchase(query, context, request_id, "approved")
    
    elif data.startswith("admin_reject_purchase_"):
        # رفض الأدمن للشراء
        request_id = int(data.split("_")[3])
        await admin_handle_purchase(query, context, request_id, "rejected")

    elif data.startswith("copy_game_id_"):
        # نسخ Game ID
        game_id = data.replace("copy_game_id_", "")
        
        # إرسال Game ID كرسالة منفصلة يسهل نسخها
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🎮 **Game ID للنسخ:**\n\n`{game_id}`\n\n"
                 f"✅ **للنسخ:** اضغط على النص أعلاه واختر 'نسخ'",
            parse_mode='Markdown'
        )
        
        await query.answer("📋 تم إرسال Game ID للنسخ", show_alert=True)
    
    elif data.startswith("copy_user_id_"):
        # نسخ معرف المستخدم
        user_id = data.replace("copy_user_id_", "")
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"👤 **معرف اللاعب للنسخ:**\n\n`{user_id}`\n\n"
                 f"✅ **للنسخ:** اضغط على النص أعلاه واختر 'نسخ'",
            parse_mode='Markdown'
        )
        
        await query.answer("📋 تم إرسال معرف اللاعب للنسخ", show_alert=True)
    
    elif data.startswith("broadcast_confirm_"):
        # تأكيد البث الشامل
        await handle_broadcast_confirmation(query, context)
    
    elif data == "broadcast_cancel":
        # إلغاء البث الشامل
        await query.edit_message_text("❌ تم إلغاء البث الشامل.")

async def handle_broadcast_confirmation(query, context):
    """معالجة تأكيد البث الشامل"""
    try:
        # استخراج الرسالة من callback_data
        # الصيغة: broadcast_confirm_HASH
        data = query.data
        hash_value = data.replace("broadcast_confirm_", "")
        
        # الحصول على الرسالة الأصلية
        original_text = query.message.text
        # استخراج الرسالة من النص
        lines = original_text.split('\n')
        message_text = ""
        
        # البحث عن سطر "الرسالة:" واستخراج ما بعده
        for i, line in enumerate(lines):
            if "الرسالة:" in line:
                # أخذ جميع الأسطر من هذا السطر فما بعد
                message_text = "\n".join(lines[i+1:])
                # إزالة الأسطر الأخيرة غير المرغوبة
                if "سيتم إرسال هذه الرسالة" in message_text:
                    message_text = message_text.split("سيتم إرسال هذه الرسالة")[0].strip()
                break
        
        if not message_text:
            message_text = "رسالة من الأدمن"
        
        await query.edit_message_text("📤 جاري إرسال الرسالة للجميع...")
        
        # جلب جميع المستخدمين النشطين
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
        users = cursor.fetchall()
        conn.close()
        
        total_users = len(users)
        successful_sends = 0
        failed_sends = 0
        
        # إرسال الرسالة لكل مستخدم
        broadcast_message = f"📢 **إشعار من الأدمن**\n\n{message_text}"
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=broadcast_message,
                    parse_mode='Markdown'
                )
                successful_sends += 1
                
                # تأخير بسيط لتجنب flood
                import asyncio
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_sends += 1
                logger.error(f"فشل إرسال إلى {user['user_id']}: {e}")
        
        # إرسال تقرير النتائج
        result_message = f"""
✅ **تم الانتهاء من البث الشامل**

📊 **النتائج:**
• 👥 إجمالي المستخدمين: {total_users}
• ✅ تم الإرسال بنجاح: {successful_sends}
• ❌ فشل الإرسال: {failed_sends}
• 📈 نسبة النجاح: {(successful_sends/total_users*100 if total_users > 0 else 0):.1f}%

📝 **الرسالة المرسلة:**
{message_text[:200]}...
        """
        
        await query.edit_message_text(result_message, parse_mode='Markdown')
        
        # تسجيل البث في السجلات
        logger.info(f"تم البث الشامل: {successful_sends}/{total_users} مستخدم")
        
    except Exception as e:
        logger.error(f"خطأ في handle_broadcast_confirmation: {e}")
        await query.edit_message_text(f"❌ حدث خطأ في البث الشامل: {e}")

async def handle_deposit_method(query, context, method):
    """معالجة طريقة الإيداع المختارة"""
    user = query.from_user
    
    if method == "sham":
        code = config.SHAM_CASH_CODE
        instructions = config.MESSAGES['deposit_instructions_sham']
    else:
        code = config.SYRIATEL_CASH_CODE
        instructions = config.MESSAGES['deposit_instructions_syriatel']
    
    message = f"💳 **طريقة الدفع: {'شام كاش' if method == 'sham' else 'سيرياتيل كاش'}**\n\n"
    message += f"🔢 الرمز: `{code}`\n\n"
    message += instructions
    
    # حفظ حالة المستخدم
    user_states[user.id] = {
        'action': 'waiting_deposit_code',
        'method': method
    }
    
    await query.edit_message_text(message, parse_mode='Markdown')

async def handle_deposit_code(update, context, method):
    """معالجة رمز الإيداع المرسل"""
    user = update.effective_user
    text = update.message.text.strip()
    
    try:
        # فصل رمز التحويل والمبلغ
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("⚠️ صيغة غير صحيحة. يجب أن تكون: [رمز التحويل] [المبلغ]")
            return
        
        transaction_code, amount_str = parts
        amount = float(amount_str)
        
        if amount <= 0:
            await update.message.reply_text("⚠️ المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        # إنشاء طلب الإيداع
        request_id = db.create_deposit_request(user.id, method, amount, transaction_code)
        
        if request_id:
            # إرسال إشعار للأدمن
            method_name = "شام كاش" if method == "sham" else "سيرياتيل كاش"
            notification = config.MESSAGES['admin_deposit_notification'].format(
                user=user.full_name,
                user_id=user.id,
                method=method_name,
                amount=amount,
                code=transaction_code
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ الموافقة", callback_data=f"admin_approve_deposit_{request_id}"),
                    InlineKeyboardButton("❌ الرفض", callback_data=f"admin_reject_deposit_{request_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=notification,
                reply_markup=reply_markup
            )
            
            await update.message.reply_text(config.MESSAGES['deposit_success'])
        else:
            await update.message.reply_text("⚠️ حدث خطأ في معالجة طلبك. يرجى المحاولة لاحقًا.")
    
    except ValueError:
        await update.message.reply_text("⚠️ المبلغ غير صالح. يرجى إدخال رقم صحيح.")
    except Exception as e:
        logger.error(f"خطأ في handle_deposit_code: {e}")
        await update.message.reply_text("⚠️ حدث خطأ في معالجة طلبك.")
    
    # تنظيف حالة المستخدم
    if user.id in user_states:
        del user_states[user.id]

async def show_game_products(query, context, game):
    """عرض منتجات اللعبة المختارة"""
    if game == "pubg":
        products = config.PRODUCTS["pubg"]
        game_name = "PUBG UC"
    else:
        products = config.PRODUCTS["freefire"]
        game_name = "Free Fire"
    
    message = f"🛍️ **{game_name} - المنتجات**\n\n"
    
    # إنشاء أزرار المنتجات (2-2)
    keyboard = []
    row = []
    
    for i, (product, price) in enumerate(products.items()):
        button_text = f"{product} - {price} ل.س"
        callback_data = f"buy_{game}_{product}"
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        # إضافة صف جديد كل زرين
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # إضافة الصف الأخير إذا كان يحتوي على عناصر
    if row:
        keyboard.append(row)
    
    # زر الرجوع
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="show_products_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    for product, price in products.items():
        message += f"• {product}: {price} ليرة سورية\n"
    
    await query.edit_message_text(message, reply_markup=reply_markup)

async def start_purchase_process(query, context, game, product):
    """بدء عملية الشراء"""
    user = query.from_user
    
    # التحقق من الرصيد
    user_balance = db.get_user_balance(user.id)
    product_price = config.PRODUCTS[game][product]
    
    if user_balance < product_price:
        await query.answer(config.MESSAGES['insufficient_balance'], show_alert=True)
        return
    
    # حفظ حالة المستخدم
    user_states[user.id] = {
        'action': 'waiting_game_id',
        'game': game,
        'product': product
    }
    
    game_name = "PUBG" if game == "pubg" else "Free Fire"
    await query.edit_message_text(
        f"🎮 **{game_name} - {product}**\n\n"
        f"💰 السعر: {product_price} ليرة سورية\n"
        f"💵 رصيدك الحالي: {user_balance} ليرة سورية\n\n"
        "📝 يرجى إرسال معرفك في اللعبة (Game ID):"
    )

async def handle_game_id(update, context, game, product):
    """معالجة معرف اللعبة"""
    user = update.effective_user
    game_id = update.message.text.strip()
    
    # تسجيل للتصحيح
    print(f"🔍 DEBUG: handle_game_id called - User: {user.id}, Game: {game}, Product: {product}")
    print(f"🔍 DEBUG: Game ID: {game_id}")
    
    # التحقق من الرصيد
    user_balance = db.get_user_balance(user.id)
    product_price = config.PRODUCTS[game][product]
    
    print(f"🔍 DEBUG: Balance: {user_balance}, Price: {product_price}")
    
    if user_balance < product_price:
        await update.message.reply_text(config.MESSAGES['insufficient_balance'])
        if user.id in user_states:
            del user_states[user.id]
        return
    
    # إنشاء طلب الشراء
    request_id = db.create_purchase_request(user.id, game, product, game_id, product_price)
    print(f"🔍 DEBUG: Request ID: {request_id}")
    
    if request_id:
        # خصم المبلغ
        db.update_balance(user.id, -product_price)
        
        # إعداد الرسالة
        game_name = "PUBG" if game == "pubg" else "Free Fire"
        notification = f"""🛒 طلب شراء جديد

👤 المستخدم: {user.full_name}
🆔 المعرف: {user.id}

🎮 اللعبة: {game_name}
📦 المنتج: {product}
🎮 Game ID: `{game_id}`
💰 السعر: {product_price} ل.س"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ الموافقة", callback_data=f"admin_approve_purchase_{request_id}"),
                InlineKeyboardButton("❌ الرفض", callback_data=f"admin_reject_purchase_{request_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        print(f"🔍 DEBUG: محاولة إرسال إلى ADMIN_ID: {config.ADMIN_ID}")
        
        try:
            # محاولة الإرسال
            await context.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=notification,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            print(f"✅ DEBUG: تم الإرسال بنجاح إلى {config.ADMIN_ID}")
            await update.message.reply_text("✅ تم إرسال طلبك بنجاح! سيتم مراجعته قريباً.")
            
        except Exception as e:
            print(f"❌ DEBUG: فشل الإرسال إلى {config.ADMIN_ID}: {e}")
            
            # محاولة بديلة: إرسال إلى الأدمن عبر اليوزر
            try:
                await context.bot.send_message(
                    chat_id=config.ADMIN_USERNAME,  # @Yousef_T1899
                    text=notification,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                print(f"✅ DEBUG: تم الإرسال إلى اليوزر {config.ADMIN_USERNAME}")
                await update.message.reply_text("✅ تم إرسال طلبك بنجاح!")
            except Exception as e2:
                print(f"❌ DEBUG: فشل الإرسال إلى اليوزر أيضاً: {e2}")
                await update.message.reply_text("⚠️ حدث خطأ في إرسال طلبك. يرجى التواصل مع الأدمن مباشرة.")
        
    else:
        await update.message.reply_text("⚠️ حدث خطأ في معالجة طلبك.")
    
    # تنظيف الحالة
    if user.id in user_states:
        del user_states[user.id]

async def admin_handle_deposit(query, context, request_id, action):
    """معالجة رد الأدمن على طلب الإيداع"""
    if query.from_user.id != config.ADMIN_ID:
        await query.answer("❌ ليس لديك صلاحية للقيام بهذا الإجراء.", show_alert=True)
        return
    
    # الحصول على طلب الإيداع
    deposit_request = db.get_deposit_request(request_id)
    if not deposit_request:
        await query.edit_message_text("⚠️ لم يتم العثور على طلب الإيداع.")
        return
    
    # تحديث حالة الطلب
    db.update_deposit_status(request_id, action)
    
    if action == "approved":
        # إضافة الرصيد للمستخدم
        db.update_balance(deposit_request['user_id'], deposit_request['amount'])
        
        # إرسال إشعار للمستخدم
        try:
            await context.bot.send_message(
                chat_id=deposit_request['user_id'],
                text=config.MESSAGES['deposit_approved'].format(amount=deposit_request['amount'])
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار للمستخدم: {e}")
    
    else:  # rejected
        # إرسال إشعار للمستخدم
        try:
            await context.bot.send_message(
                chat_id=deposit_request['user_id'],
                text=config.MESSAGES['deposit_rejected']
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار للمستخدم: {e}")
    
    await query.edit_message_text(f"✅ تم {action} طلب الإيداع.")

async def admin_handle_purchase(query, context, request_id, action):
    """معالجة رد الأدمن على طلب الشراء"""
    if query.from_user.id != config.ADMIN_ID:
        await query.answer("❌ ليس لديك صلاحية للقيام بهذا الإجراء.", show_alert=True)
        return
    
    # الحصول على طلب الشراء
    purchase_request = db.get_purchase_request(request_id)
    if not purchase_request:
        await query.edit_message_text("⚠️ لم يتم العثور على طلب الشراء.")
        return
    
    user_id = purchase_request['user_id']
    price = purchase_request['price']
    
    # التحقق من حالة الطلب أولاً
    if purchase_request['status'] != 'pending':
        await query.edit_message_text(f"⚠️ هذا الطلب تم معالجته مسبقاً ({purchase_request['status']}).")
        return
    
    # تحديث حالة الطلب أولاً
    db.update_purchase_status(request_id, action)
    
    if action == "approved":
        # الموافقة: لا تغيير في الرصيد (تم الخصم مسبقاً)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=config.MESSAGES['purchase_approved']
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار للمستخدم: {e}")
    
    else:  # rejected
        # الرفض: إعادة الرصيد فقط إذا تم خصمه
        # التحقق: هل الرصيد الحالي أقل من السعر الأصلي؟
        current_balance = db.get_user_balance(user_id)
        
        # إذا كان الرصيد الحالي أقل من المتوقع (تم الخصم)
        # نضيف السعر مرة أخرى
        db.update_balance(user_id, price)
        
        # إرسال إشعار للمستخدم
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=config.MESSAGES['purchase_rejected']
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار للمستخدم: {e}")
    
    await query.edit_message_text(f"✅ تم {action} طلب الشراء.")

# أوامر الأدمن
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أوامر الأدمن"""
    user = update.effective_user
    
    if user.id != config.ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الأوامر.")
        return
    
    command = update.message.text.split()[0]
    
    if command == "/balance":
        # عرض رصيد مستخدم
        if len(context.args) < 1:
            await update.message.reply_text("❌ استخدام خاطئ: /balance [user_id]")
            return
        
        try:
            user_id = int(context.args[0])
            balance = db.get_user_balance(user_id)
            await update.message.reply_text(f"💰 رصيد المستخدم {user_id}: {balance} ل.س")
        except ValueError:
            await update.message.reply_text("❌ معرف مستخدم غير صالح.")
    
    elif command == "/addbalance":
        # إضافة رصيد لمستخدم
        if len(context.args) < 2:
            await update.message.reply_text("❌ استخدام خاطئ: /addbalance [user_id] [amount]")
            return
        
        try:
            user_id = int(context.args[0])
            amount = float(context.args[1])
            
            if db.update_balance(user_id, amount):
                await update.message.reply_text(f"✅ تم إضافة {amount} ل.س إلى رصيد المستخدم {user_id}")
                
                # إرسال إشعار للمستخدم
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"💰 تمت إضافة {amount} ليرة سورية إلى رصيدك من قبل الأدمن."
                    )
                except Exception as e:
                    logger.error(f"خطأ في إرسال إشعار للمستخدم: {e}")
            else:
                await update.message.reply_text("❌ فشلت العملية.")
        except ValueError:
            await update.message.reply_text("❌ قيم غير صالحة.")
    
    elif command == "/ban":
        # حظر مستخدم
        if len(context.args) < 1:
            await update.message.reply_text("❌ استخدام خاطئ: /ban [user_id] [reason]")
            return
        
        try:
            user_id = int(context.args[0])
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون سبب"
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"✅ تم حظر المستخدم {user_id}\nالسبب: {reason}")
        except ValueError:
            await update.message.reply_text("❌ معرف مستخدم غير صالح.")
    
    elif command == "/unban":
        # فك حظر مستخدم
        if len(context.args) < 1:
            await update.message.reply_text("❌ استخدام خاطئ: /unban [user_id]")
            return
        
        try:
            user_id = int(context.args[0])
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"✅ تم فك حظر المستخدم {user_id}")
        except ValueError:
            await update.message.reply_text("❌ معرف مستخدم غير صالح.")
    
    elif command == "/message":
        # إرسال رسالة لمستخدم
        if len(context.args) < 2:
            await update.message.reply_text("❌ استخدام خاطئ: /message [user_id] [message]")
            return
        
        try:
            user_id = int(context.args[0])
            message = " ".join(context.args[1:])
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📨 رسالة من الأدمن:\n\n{message}"
            )
            
            await update.message.reply_text(f"✅ تم إرسال الرسالة إلى المستخدم {user_id}")
        except ValueError:
            await update.message.reply_text("❌ معرف مستخدم غير صالح.")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل إرسال الرسالة: {e}")
    
    elif command == "/stats":
        # إحصائيات البوت
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute('SELECT COUNT(*) as active_users FROM users WHERE is_banned = 0')
        active_users = cursor.fetchone()['active_users']
        
        cursor.execute('SELECT COUNT(*) as banned_users FROM users WHERE is_banned = 1')
        banned_users = cursor.fetchone()['banned_users']
        
        cursor.execute('SELECT SUM(balance) as total_balance FROM users')
        total_balance = cursor.fetchone()['total_balance'] or 0
        
        cursor.execute('SELECT SUM(amount) as total_deposits FROM deposit_requests WHERE status = "approved"')
        total_deposits = cursor.fetchone()['total_deposits'] or 0
        
        cursor.execute('SELECT SUM(price) as total_sales FROM purchase_requests WHERE status = "approved"')
        total_sales = cursor.fetchone()['total_sales'] or 0
        
        conn.close()
        
        stats_message = f"""
📊 **إحصائيات البوت**

👥 إجمالي المستخدمين: {total_users}
👤 المستخدمين النشطين: {active_users}
🚫 المستخدمين المحظورين: {banned_users}

💰 إجمالي الأرصدة: {total_balance} ل.س
💳 إجمالي الإيداعات: {total_deposits} ل.س
🛒 إجمالي المبيعات: {total_sales} ل.س
📈 صافي الأرباح: {total_deposits - total_sales} ل.س
        """
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')

# ===== الدوال الناقصة التي يجب إضافتها =====

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help للمستخدمين"""
    help_text = """
❓ **أوامر البوت:**

🔹 **أوامر عامة:**
/start - بدء البوت
/help - عرض هذه الرسالة
/balance - عرض رصيدك
/deposit - إيداع رصيد (استخدم الأزرار)
/products - عرض المنتجات (استخدم الأزرار)
/admin - معلومات الأدمن

🔹 **الأزرار المتاحة:**
💰 إيداع رصيد - للإيداع عبر شام كاش أو سيرياتيل كاش
👤 معلومات الحساب - لعرض بيانات حسابك
🛍️ المنتجات - لشراء UC للببجي أو جواهر للفري فاير
👨‍💼 التحدث مع الأدمن - للتواصل مع الدعم

📱 **استخدم الأزرار في الأسفل للتنقل السريع!**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def user_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /balance للمستخدمين العاديين"""
    user = update.effective_user
    user_data = db.get_or_create_user(user.id, user.username, user.full_name)
    
    if user_data:
        balance = user_data['balance']
        await update.message.reply_text(
            f"💰 **رصيدك الحالي:** {balance} ليرة سورية\n\n"
            f"💳 للإيداع: استخدم زر '💰 إيداع رصيد'\n"
            f"🛍️ للشراء: استخدم زر '🛍️ المنتجات'",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("⚠️ لم يتم العثور على حسابك.")

async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توجيه أوامر الأدمن إلى admin_handler"""
    await admin_handler.handle_admin_command(update, context)

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    print("=" * 50)
    print("🚀 بدء تشغيل Syrian store ⚡🇸🇾")
    print("=" * 50)
    
    try:
        # إنشاء التطبيق
        application = Application.builder().token(config.BOT_TOKEN).build()
        
        # ===== إضافة المعالجات =====
        
        # 1. أوامر المستخدمين الأساسية
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("balance", user_balance_command))
        
        # 2. معالج الاستعلامات (Inline Buttons)
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # 3. معالج الرسائل النصية
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # 4. أوامر الأدمن
        application.add_handler(CommandHandler("stats", handle_admin_command))
        application.add_handler(CommandHandler("ban", handle_admin_command))
        application.add_handler(CommandHandler("unban", handle_admin_command))
        application.add_handler(CommandHandler("addbalance", handle_admin_command))
        application.add_handler(CommandHandler("deduct", handle_admin_command))
        application.add_handler(CommandHandler("message", handle_admin_command))
        application.add_handler(CommandHandler("users", handle_admin_command))
        application.add_handler(CommandHandler("deposits", handle_admin_command))
        application.add_handler(CommandHandler("purchases", handle_admin_command))
        application.add_handler(CommandHandler("top", handle_admin_command))
        application.add_handler(CommandHandler("transactions", handle_admin_command))
        application.add_handler(CommandHandler("broadcast", handle_admin_command))
        application.add_handler(CommandHandler("backup", handle_admin_command))
        application.add_handler(CommandHandler("logs", handle_admin_command))
        application.add_handler(CommandHandler("help_admin", handle_admin_command))
        
        print("✅ تم تهيئة جميع المعالجات")
        print(f"🔑 البوت: Syrian store ⚡🇸🇾")
        print(f"🔗 الرابط: t.me/Syrian_store_1_bot")
        print(f"👑 الأدمن: {config.ADMIN_ID}")
        print("\n📱 البوت جاهز للاستخدام!")
        print("🎯 اكتب /start في Telegram")
        print("=" * 50)
        
        # تشغيل البوت
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 البوت توقف بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ في تشغيل البوت: {type(e).__name__}")
        print(f"📝 التفاصيل: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()