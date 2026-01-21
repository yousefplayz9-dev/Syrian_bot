# -*- coding: utf-8 -*-
"""back_to_products products_freefire
وحدة قاعدة البيانات لإدارة المستخدمين والمعاملات
"""
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name="wallet_bot.db"):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """تهيئة جداول قاعدة البيانات"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    balance REAL DEFAULT 0,
                    total_purchases INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول المعاملات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT, -- 'deposit' أو 'purchase'
                    amount REAL,
                    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول طلبات الإيداع
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deposit_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    method TEXT, -- 'sham' أو 'syriatel'
                    amount REAL,
                    transaction_code TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول طلبات الشراء
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS purchase_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    game TEXT,
                    product TEXT,
                    game_id TEXT,
                    price REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
            logger.info("تم تهيئة قاعدة البيانات بنجاح")
        except Exception as e:
            logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
        finally:
            conn.close()
    
    def get_or_create_user(self, user_id, username, full_name):
        """الحصول على مستخدم أو إنشاؤه إذا لم يكن موجودًا"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # البحث عن المستخدم
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # إنشاء مستخدم جديد
                cursor.execute('''
                    INSERT INTO users (user_id, username, full_name)
                    VALUES (?, ?, ?)
                ''', (user_id, username, full_name))
                conn.commit()
                logger.info(f"تم إنشاء مستخدم جديد: {user_id}")
                
                # الحصول على المستخدم المخلوق حديثًا
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
            
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"خطأ في get_or_create_user: {e}")
            return None
        finally:
            conn.close()
    
    def update_balance(self, user_id, amount):
        """تحديث رصيد المستخدم"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ? 
                WHERE user_id = ?
            ''', (amount, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطأ في update_balance: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_balance(self, user_id):
        """الحصول على رصيد المستخدم"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            return result['balance'] if result else 0
        except Exception as e:
            logger.error(f"خطأ في get_user_balance: {e}")
            return 0
        finally:
            conn.close()
    
    def create_deposit_request(self, user_id, method, amount, transaction_code):
        """إنشاء طلب إيداع"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO deposit_requests (user_id, method, amount, transaction_code)
                VALUES (?, ?, ?, ?)
            ''', (user_id, method, amount, transaction_code))
            
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"خطأ في create_deposit_request: {e}")
            return None
        finally:
            conn.close()
    
    def create_purchase_request(self, user_id, game, product, game_id, price):
        """إنشاء طلب شراء"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO purchase_requests (user_id, game, product, game_id, price)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, game, product, game_id, price))
            
            # تحديث عدد المشتريات
            cursor.execute('''
                UPDATE users 
                SET total_purchases = total_purchases + 1 
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"خطأ في create_purchase_request: {e}")
            return None
        finally:
            conn.close()
    
    def update_deposit_status(self, request_id, status):
        """تحديث حالة طلب الإيداع"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE deposit_requests 
                SET status = ? 
                WHERE id = ?
            ''', (status, request_id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطأ في update_deposit_status: {e}")
            return False
        finally:
            conn.close()
    
    def update_purchase_status(self, request_id, status):
        """تحديث حالة طلب الشراء"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE purchase_requests 
                SET status = ? 
                WHERE id = ?
            ''', (status, request_id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطأ في update_purchase_status: {e}")
            return False
        finally:
            conn.close()
    
    def get_deposit_request(self, request_id):
        """الحصول على طلب إيداع"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM deposit_requests WHERE id = ?', (request_id,))
            result = cursor.fetchone()
            
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"خطأ في get_deposit_request: {e}")
            return None
        finally:
            conn.close()
    
    def get_purchase_request(self, request_id):
        """الحصول على طلب شراء"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM purchase_requests WHERE id = ?', (request_id,))
            result = cursor.fetchone()
            
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"خطأ في get_purchase_request: {e}")
            return None
        finally:
            conn.close()