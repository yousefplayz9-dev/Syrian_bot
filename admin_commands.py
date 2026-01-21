# -*- coding: utf-8 -*-  show_stats broadcast handle_callback_query
        
"""
وحدة أوامر الأدمن الكاملة
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from database import Database

logger = logging.getLogger(__name__)
db = Database(config.DB_NAME)

class AdminCommands:
    def __init__(self):
        self.admin_id = config.ADMIN_ID
    
    def is_admin(self, user_id):
        """التحقق من صلاحية الأدمن"""
        return user_id == self.admin_id
    
    async def handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة جميع أوامر الأدمن"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ ليس لديك صلاحية الأدمن.")
            return
        
        command = update.message.text.split()[0]
        
        # توجيه الأوامر للدوال المناسبة
        command_handlers = {
            '/ban': self.ban_user,
            '/unban': self.unban_user,
            '/users': self.list_users,
            '/balance': self.get_user_balance,
            '/addbalance': self.add_balance,
            '/deduct': self.deduct_balance,
            '/deposits': self.list_deposits,
            '/purchases': self.list_purchases,
            '/stats': self.show_stats,
            '/message': self.send_message,
            '/broadcast': self.broadcast,
            '/transactions': self.user_transactions,
            '/top': self.top_users,
            '/backup': self.create_backup,
            '/logs': self.show_logs,
            '/help_admin': self.admin_help
        }
        
        handler = command_handlers.get(command)
        if handler:
            await handler(update, context)
        else:
            await update.message.reply_text("❌ أمر غير معروف. استخدم /help_admin")
    
    async def admin_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض مساعدة الأدمن"""
        help_text = """
🎮 **أوامر الأدمن الكاملة:**

👥 **إدارة المستخدمين:**
• `/ban [id] [reason]` - حظر مستخدم
• `/unban [id]` - فك حظر
• `/users [page]` - عرض المستخدمين
• `/search [query]` - بحث عن مستخدم

💰 **إدارة الرصيد:**
• `/balance [id]` - عرض رصيد
• `/addbalance [id] [amount]` - إضافة رصيد
• `/setbalance [id] [amount]` - تعيين رصيد
• `/deduct [id] [amount] [reason]` - خصم رصيد

📋 **إدارة الطلبات:**
• `/deposits [status]` - طلبات الإيداع
• `/deposit_approve [id]` - قبول إيداع
• `/deposit_reject [id] [reason]` - رفض إيداع
• `/purchases [status]` - طلبات الشراء
• `/purchase_approve [id]` - قبول شراء
• `/purchase_reject [id] [reason]` - رفض شراء

📊 **الإحصائيات:**
• `/stats` - إحصائيات البوت
• `/report [period]` - تقرير مفصل
• `/transactions [id]` - معاملات مستخدم
• `/top [type]` - أعلى المستخدمين

📨 **التواصل:**
• `/message [id] [text]` - إرسال رسالة
• `/broadcast [text]` - إرسال للجميع
• `/reply [text]` - رد على آخر رسالة

⚙️ **النظام:**
• `/backup` - نسخة احتياطية
• `/restart` - إعادة التشغيل
• `/logs [lines]` - عرض السجلات
• `/settings` - الإعدادات
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """حظر مستخدم"""
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ استخدام: /ban [user_id] [reason]")
                return
            
            user_id = int(context.args[0])
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون سبب"
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"✅ تم حظر المستخدم {user_id}\nالسبب: {reason}")
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚫 تم حظر حسابك\nالسبب: {reason}\nللتواصل: {config.ADMIN_USERNAME}"
                )
            except:
                pass
                
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فك حظر مستخدم"""
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ استخدام: /unban [user_id]")
                return
            
            user_id = int(context.args[0])
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"✅ تم فك حظر المستخدم {user_id}")
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ تم فك حظر حسابك\nمرحباً بعودتك!"
                )
            except:
                pass
                
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة المستخدمين"""
        try:
            page = int(context.args[0]) if context.args else 1
            limit = 10
            offset = (page - 1) * limit
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # جلب المستخدمين
            cursor.execute('''
                SELECT * FROM users 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            users = cursor.fetchall()
            
            # عدد المستخدمين الإجمالي
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            conn.close()
            
            if not users:
                await update.message.reply_text("📭 لا يوجد مستخدمين في هذه الصفحة.")
                return
            
            message = f"👥 **المستخدمين (الصفحة {page})**\n\n"
            for user in users:
                status = "🚫 محظور" if user['is_banned'] else "✅ نشط"
                message += (
                    f"🆔 **{user['user_id']}**\n"
                    f"👤 {user['full_name']}\n"
                    f"💰 {user['balance']} ل.س | 🛒 {user['total_purchases']}\n"
                    f"📅 {user['created_at'][:10]} | {status}\n"
                    f"━━━━━━━━━━━━━━\n"
                )
            
            total_pages = (total_users + limit - 1) // limit
            
            # أزرار التنقل
            keyboard = []
            if page > 1:
                keyboard.append(InlineKeyboardButton("◀️ السابق", callback_data=f"users_{page-1}"))
            if page < total_pages:
                keyboard.append(InlineKeyboardButton("التالي ▶️", callback_data=f"users_{page+1}"))
            
            if keyboard:
                reply_markup = InlineKeyboardMarkup([keyboard])
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(message, parse_mode='Markdown')
                
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def get_user_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض رصيد مستخدم"""
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ استخدام: /balance [user_id]")
                return
            
            user_id = int(context.args[0])
            balance = db.get_user_balance(user_id)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                message = (
                    f"👤 **معلومات المستخدم**\n\n"
                    f"🆔 **المعرف:** {user['user_id']}\n"
                    f"📛 **الاسم:** {user['full_name']}\n"
                    f"📧 **اليوزر:** @{user['username'] if user['username'] else 'غير متوفر'}\n"
                    f"💰 **الرصيد:** {balance} ليرة سورية\n"
                    f"🛒 **المشتريات:** {user['total_purchases']}\n"
                    f"📅 **تاريخ التسجيل:** {user['created_at'][:10]}\n"
                    f"🚫 **الحالة:** {'محظور' if user['is_banned'] else 'نشط'}"
                )
            else:
                message = f"❌ لم يتم العثور على المستخدم {user_id}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def add_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إضافة رصيد لمستخدم"""
        try:
            if len(context.args) < 2:
                await update.message.reply_text("❌ استخدام: /addbalance [user_id] [amount]")
                return
            
            user_id = int(context.args[0])
            amount = float(context.args[1])
            
            if amount <= 0:
                await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر.")
                return
            
            # التحقق من وجود المستخدم
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                await update.message.reply_text(f"❌ لم يتم العثور على المستخدم {user_id}")
                return
            
            # إضافة الرصيد
            success = db.update_balance(user_id, amount)
            conn.close()
            
            if success:
                # تسجيل المعاملة
                new_conn = db.get_connection()
                new_cursor = new_conn.cursor()
                new_cursor.execute('''
                    INSERT INTO transactions (user_id, type, amount, status, details)
                    VALUES (?, 'admin_add', ?, 'approved', ?)
                ''', (user_id, amount, f"إضافة رصيد من الأدمن"))
                new_conn.commit()
                new_conn.close()
                
                await update.message.reply_text(f"✅ تم إضافة {amount} ل.س إلى رصيد المستخدم {user_id}")
                
                # إرسال إشعار للمستخدم
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"💰 **تمت إضافة رصيد**\n\nتم إضافة {amount} ليرة سورية إلى رصيدك من قبل الأدمن.\nرصيدك الجديد: {user['balance'] + amount} ل.س"
                    )
                except Exception as e:
                    logger.error(f"فشل إرسال إشعار للمستخدم: {e}")
            else:
                await update.message.reply_text("❌ فشلت العملية.")
                
        except ValueError:
            await update.message.reply_text("❌ القيم المدخلة غير صالحة.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def list_deposits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض طلبات الإيداع"""
        try:
            status = context.args[0] if context.args else 'pending'
            valid_statuses = ['pending', 'approved', 'rejected', 'all']
            
            if status not in valid_statuses:
                await update.message.reply_text(f"❌ الحالة يجب أن تكون: {', '.join(valid_statuses)}")
                return
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            if status == 'all':
                cursor.execute('''
                    SELECT d.*, u.full_name, u.username 
                    FROM deposit_requests d 
                    JOIN users u ON d.user_id = u.user_id 
                    ORDER BY d.created_at DESC 
                    LIMIT 20
                ''')
            else:
                cursor.execute('''
                    SELECT d.*, u.full_name, u.username 
                    FROM deposit_requests d 
                    JOIN users u ON d.user_id = u.user_id 
                    WHERE d.status = ? 
                    ORDER BY d.created_at DESC 
                    LIMIT 20
                ''', (status,))
            
            deposits = cursor.fetchall()
            conn.close()
            
            if not deposits:
                await update.message.reply_text(f"📭 لا توجد طلبات إيداع بحالة '{status}'")
                return
            
            message = f"💰 **طلبات الإيداع ({status})**\n\n"
            
            for dep in deposits:
                method = "شام كاش" if dep['method'] == 'sham' else "سيرياتيل كاش"
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'rejected': '❌'
                }.get(dep['status'], '📄')
                
                message += (
                    f"🆔 **طلب #{dep['id']}** {status_emoji}\n"
                    f"👤 {dep['full_name']} (@{dep['username']})\n"
                    f"💳 {method} | 💰 {dep['amount']} ل.س\n"
                    f"🔢 الكود: {dep['transaction_code']}\n"
                    f"📅 {dep['created_at'][:16]}\n"
                    f"━━━━━━━━━━━━━━\n"
                )
            
            # أزرار الإجراءات
            keyboard = []
            if status == 'pending':
                keyboard.append([
                    InlineKeyboardButton("✅ جميع المعاملات", callback_data="deposits_all"),
                    InlineKeyboardButton("⏳ المعلقة فقط", callback_data="deposits_pending")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def list_purchases(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض طلبات الشراء"""
        try:
            status = context.args[0] if context.args else 'pending'
            valid_statuses = ['pending', 'approved', 'rejected', 'all']
            
            if status not in valid_statuses:
                await update.message.reply_text(f"❌ الحالة يجب أن تكون: {', '.join(valid_statuses)}")
                return
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            if status == 'all':
                cursor.execute('''
                    SELECT p.*, u.full_name, u.username 
                    FROM purchase_requests p 
                    JOIN users u ON p.user_id = u.user_id 
                    ORDER BY p.created_at DESC 
                    LIMIT 20
                ''')
            else:
                cursor.execute('''
                    SELECT p.*, u.full_name, u.username 
                    FROM purchase_requests p 
                    JOIN users u ON p.user_id = u.user_id 
                    WHERE p.status = ? 
                    ORDER BY p.created_at DESC 
                    LIMIT 20
                ''', (status,))
            
            purchases = cursor.fetchall()
            conn.close()
            
            if not purchases:
                await update.message.reply_text(f"📭 لا توجد طلبات شراء بحالة '{status}'")
                return
            
            message = f"🛒 **طلبات الشراء ({status})**\n\n"
            
            for pur in purchases:
                game = "PUBG" if pur['game'] == 'pubg' else "Free Fire"
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'rejected': '❌'
                }.get(pur['status'], '📄')
                
                message += (
                    f"🆔 **طلب #{pur['id']}** {status_emoji}\n"
                    f"👤 {pur['full_name']} (@{pur['username']})\n"
                    f"🎮 {game} | 📦 {pur['product']}\n"
                    f"🎮 ID: {pur['game_id']} | 💰 {pur['price']} ل.س\n"
                    f"📅 {pur['created_at'][:16]}\n"
                    f"━━━━━━━━━━━━━━\n"
                )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def deduct_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قص رصيد من مستخدم"""
        try:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ استخدام: /deduct [user_id] [amount] [reason]\n\n"
                    "📝 مثال:\n"
                    "• /deduct 123456789 1000\n"
                    "• /deduct 123456789 5000 مخالفة القواعد\n"
                    "• /deduct 123456789 all (قص كل الرصيد)"
                )
                return
            
            user_id = int(context.args[0])
            amount_str = context.args[1].lower()
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else "بدون سبب"
            
            # التحقق من وجود المستخدم
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                await update.message.reply_text(f"❌ لم يتم العثور على المستخدم {user_id}")
                return
            
            current_balance = user['balance']
            
            # تحديد المبلغ المطلوب قصه
            if amount_str == "all":
                amount = current_balance
                if amount == 0:
                    conn.close()
                    await update.message.reply_text(f"❌ رصيد المستخدم {user_id} صفر!")
                    return
            else:
                amount = float(amount_str)
                if amount <= 0:
                    conn.close()
                    await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر.")
                    return
                
                if amount > current_balance:
                    conn.close()
                    await update.message.reply_text(
                        f"❌ المبلغ المطلوب قصه ({amount} ل.س) أكبر من الرصيد الحالي ({current_balance} ل.س)"
                    )
                    return
            
            # قص الرصيد
            new_balance = current_balance - amount
            cursor.execute('''
                UPDATE users 
                SET balance = balance - ? 
                WHERE user_id = ?
            ''', (amount, user_id))
            
            # تسجيل المعاملة
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, status, details)
                VALUES (?, 'admin_deduct', ?, 'completed', ?)
            ''', (user_id, -amount, f"قص رصيد من الأدمن - السبب: {reason}"))
            
            conn.commit()
            conn.close()
            
            # إرسال تأكيد للأدمن
            await update.message.reply_text(
                f"✅ تم قص {amount} ل.س من رصيد المستخدم {user_id}\n\n"
                f"👤 **المستخدم:** {user['full_name']}\n"
                f"💰 **الرصيد السابق:** {current_balance} ل.س\n"
                f"💵 **الرصيد الجديد:** {new_balance} ل.س\n"
                f"📝 **السبب:** {reason}"
            )
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠️ **تم خصم رصيد من حسابك**\n\n"
                         f"💰 **المبلغ:** {amount} ليرة سورية\n"
                         f"💵 **رصيدك الجديد:** {new_balance} ل.س\n"
                         f"📝 **السبب:** {reason}\n"
                         f"🔗 **للتواصل:** {config.ADMIN_USERNAME}"
                )
            except Exception as e:
                logger.error(f"فشل إرسال إشعار للمستخدم {user_id}: {e}")
                
        except ValueError:
            await update.message.reply_text("❌ القيم المدخلة غير صالحة. تأكد من صحة الأرقام.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات البوت"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # عدد المستخدمين
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 0')
            active_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
            banned_users = cursor.fetchone()[0]
            
            # الأرصدة
            cursor.execute('SELECT SUM(balance) FROM users')
            total_balance = cursor.fetchone()[0] or 0
            
            # الإيداعات
            cursor.execute('SELECT SUM(amount) FROM deposit_requests WHERE status = "approved"')
            total_deposits = cursor.fetchone()[0] or 0
            
            # المبيعات
            cursor.execute('SELECT SUM(price) FROM purchase_requests WHERE status = "approved"')
            total_sales = cursor.fetchone()[0] or 0
            
            # عدد المشتريات
            cursor.execute('SELECT COUNT(*) FROM purchase_requests WHERE status = "approved"')
            total_purchases = cursor.fetchone()[0] or 0  # <-- أضف هذا السطر

            # إجمالي المشتريات (كمية المنتجات)
            cursor.execute('SELECT SUM(total_purchases) FROM users')
            total_products = cursor.fetchone()[0] or 0   # ✅ متغير جديد

            # الطلبات اليومية
            cursor.execute('SELECT COUNT(*) FROM deposit_requests WHERE DATE(created_at) = DATE("now")')
            today_deposits = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM purchase_requests WHERE DATE(created_at) = DATE("now")')
            today_purchases = cursor.fetchone()[0]
            
            conn.close()
            
            # حساب المعدلات - ⬇️⬇️⬇️ تعريف المتغيرات قبل استخدامها ⬇️⬇️⬇️
            avg_balance = total_balance / active_users if active_users > 0 else 0
            avg_purchase_value = total_sales / total_purchases if total_purchases > 0 else 0
            avg_purchases_per_user = total_products / active_users if active_users > 0 else 0

            stats_message = f"""
📊 **إحصائيات البوت الشاملة**

👥 **المستخدمين:**
• إجمالي المستخدمين: {total_users}
• المستخدمين النشطين: {active_users}
• المستخدمين المحظورين: {banned_users}

💰 **الأموال:**
• إجمالي الأرصدة: {total_balance:,.0f} ل.س
• إجمالي الإيداعات: {total_deposits:,.0f} ل.س
• إجمالي المبيعات: {total_sales:,.0f} ل.س
• صافي الأرباح: {total_deposits - total_sales:,.0f} ل.س

🛒 **المشتريات:**
• عدد المعاملات: {total_purchases}
• منتجات مشتراة: {total_products}
• قيمة إجمالية: {total_sales:,.0f} ل.س

📈 **النشاط اليومي:**
• طلبات الإيداع: {today_deposits}
• طلبات الشراء: {today_purchases}
• إجمالي الطلبات: {today_deposits + today_purchases}

💼 **المعدلات:**
• متوسط الرصيد: {avg_balance:,.0f} ل.س
• متوسط قيمة الشراء: {avg_purchase_value:,.0f} ل.س
• متوسط المشتريات/مستخدم: {avg_purchases_per_user:.1f}
            """
            
            await update.message.reply_text(stats_message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في الإحصائيات: {e}")
    
    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إرسال رسالة لمستخدم"""
        try:
            if len(context.args) < 2:
                await update.message.reply_text("❌ استخدام: /message [user_id] [text]")
                return
            
            user_id = int(context.args[0])
            message_text = " ".join(context.args[1:])
            
            # التحقق من وجود المستخدم
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                await update.message.reply_text(f"❌ لم يتم العثور على المستخدم {user_id}")
                return
            
            # إرسال الرسالة
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📨 **رسالة من الأدمن:**\n\n{message_text}\n\n🔗 للرد: {config.ADMIN_USERNAME}"
                )
                await update.message.reply_text(f"✅ تم إرسال الرسالة إلى المستخدم {user_id}")
                
                # تسجيل الرسالة
                log_conn = db.get_connection()
                log_cursor = log_conn.cursor()
                log_cursor.execute('''
                    INSERT INTO transactions (user_id, type, amount, status, details)
                    VALUES (?, 'admin_message', 0, 'sent', ?)
                ''', (user_id, f"رسالة أدمن: {message_text[:50]}..."))
                log_conn.commit()
                log_conn.close()
                
            except Exception as e:
                await update.message.reply_text(f"❌ فشل إرسال الرسالة: {e}")
                
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إرسال رسالة للجميع"""
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ استخدام: /broadcast [text]")
                return
            
            message_text = " ".join(context.args)
            
            # تأكيد البث
            keyboard = [
                [
                    InlineKeyboardButton("✅ نعم، أرسل للجميع", callback_data=f"broadcast_confirm_{hash(message_text)}"),
                    InlineKeyboardButton("❌ إلغاء", callback_data="broadcast_cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📢 **تأكيد البث الشامل**\n\n"
                f"الرسالة:\n{message_text}\n\n"
                f"سيتم إرسال هذه الرسالة لجميع المستخدمين النشطين.\n"
                f"هل تريد المتابعة؟",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def user_transactions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض معاملات مستخدم"""
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ استخدام: /transactions [user_id]")
                return
            
            user_id = int(context.args[0])
            limit = int(context.args[1]) if len(context.args) > 1 else 10
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # التحقق من وجود المستخدم
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                await update.message.reply_text(f"❌ لم يتم العثور على المستخدم {user_id}")
                return
            
            # جلب المعاملات
            cursor.execute('''
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            transactions = cursor.fetchall()
            conn.close()
            
            if not transactions:
                await update.message.reply_text(f"📭 لا توجد معاملات للمستخدم {user_id}")
                return
            
            message = f"📋 **معاملات المستخدم {user_id}**\n\n"
            
            for trans in transactions:
                type_emoji = {
                    'deposit': '💳',
                    'purchase': '🛒',
                    'admin_add': '➕',
                    'admin_message': '📨'
                }.get(trans['type'], '📄')
                
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'rejected': '❌',
                    'sent': '📤'
                }.get(trans['status'], '📄')
                
                message += (
                    f"{type_emoji} **{trans['type']}** {status_emoji}\n"
                    f"💰 {trans['amount']} ل.س\n"
                    f"📝 {trans['details'][:50]}...\n"
                    f"📅 {trans['created_at'][:16]}\n"
                    f"━━━━━━━━━━━━━━\n"
                )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def top_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض أعلى المستخدمين"""
        try:
            criteria = context.args[0] if context.args else 'balance'
            
            if criteria not in ['balance', 'purchases']:
                await update.message.reply_text("❌ المعيار يجب أن يكون: balance أو purchases")
                return
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            if criteria == 'balance':
                cursor.execute('''
                    SELECT user_id, full_name, balance, total_purchases 
                    FROM users 
                    WHERE is_banned = 0 
                    ORDER BY balance DESC 
                    LIMIT 10
                ''')
                title = "💰 **أعلى 10 أرصدة**"
            else:
                cursor.execute('''
                    SELECT user_id, full_name, balance, total_purchases 
                    FROM users 
                    WHERE is_banned = 0 
                    ORDER BY total_purchases DESC 
                    LIMIT 10
                ''')
                title = "🛒 **أعلى 10 مشتريات**"
            
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                await update.message.reply_text("📭 لا يوجد مستخدمين")
                return
            
            message = f"{title}\n\n"
            
            for i, user in enumerate(users, 1):
                emoji = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
                if criteria == 'balance':
                    value = f"💰 {user['balance']:,} ل.س"
                else:
                    value = f"🛒 {user['total_purchases']} عملية"
                
                message += (
                    f"{emoji} **{user['full_name']}**\n"
                    f"🆔 {user['user_id']} | {value}\n"
                    f"━━━━━━━━━━━━━━\n"
                )
            
            # أزرار التبديل
            keyboard = [
                [
                    InlineKeyboardButton("💰 الأرصدة", callback_data="top_balance"),
                    InlineKeyboardButton("🛒 المشتريات", callback_data="top_purchases")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
    
    async def create_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء نسخة احتياطية"""
        try:
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_{timestamp}.db"
            
            shutil.copy2(config.DB_NAME, backup_file)
            
            await update.message.reply_text(
                f"💾 **تم إنشاء نسخة احتياطية**\n\n"
                f"📁 الملف: `{backup_file}`\n"
                f"📅 التاريخ: {timestamp}\n"
                f"🔒 تم حفظها في مجلد البوت"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ فشل إنشاء النسخة الاحتياطية: {e}")
    
    async def show_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض سجلات البوت"""
        try:
            lines = int(context.args[0]) if context.args else 50
            
            import os
            if not os.path.exists('bot.log'):
                await update.message.reply_text("📭 لا يوجد ملف سجلات")
                return
            
            with open('bot.log', 'r', encoding='utf-8') as f:
                all_logs = f.readlines()
            
            if len(all_logs) > lines:
                logs = all_logs[-lines:]
            else:
                logs = all_logs
            
            if not logs:
                await update.message.reply_text("📭 لا توجد سجلات حديثة")
                return
            
            log_text = "📜 **آخر السجلات:**\n\n"
            for log in logs[-20:]:  # إرسال آخر 20 سطر فقط لتجنب تجاوز الحد
                log_text += f"`{log.strip()}`\n"
            
            await update.message.reply_text(log_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في عرض السجلات: {e}")