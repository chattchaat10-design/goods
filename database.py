import sqlite3
import json
from datetime import datetime
import os
from pathlib import Path
import random

class GoodsEntryDB:
    def __init__(self, db_path="goods_entry.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """ایجاد جداول پایگاه داده"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول اصلی فرم
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_number TEXT UNIQUE NOT NULL,
                entry_date TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                full_name TEXT NOT NULL,
                vehicle_number TEXT,
                roadway_bill TEXT,
                internal_bill TEXT,
                controller TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول آیتم‌های کالا
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                row_number INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                serial_number TEXT,
                invoice_number TEXT,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES entry_forms (id) ON DELETE CASCADE
            )
        ''')
        
        # جدول اسناد اسکن شده
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanned_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                document_name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entry_forms (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ پایگاه داده با موفقیت ایجاد شد")
    
    def generate_unique_entry_number(self):
        """تولید شماره ورود منحصر به فرد"""
        current_persian_year = 1404
        timestamp = datetime.now().strftime("%H%M%S")
        random_num = random.randint(1000, 9999)
        unique_number = f"{current_persian_year}{timestamp}{random_num}"
        
        # بررسی منحصر به فرد بودن
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM entry_forms WHERE entry_number = ?', (unique_number,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            # اگر بازهم تکراری بود، یک شماره دیگر تولید کن
            return self.generate_unique_entry_number()
        
        return unique_number
    
    def create_uploads_directory(self):
        """ایجاد پوشه آپلود برای ذخیره عکس‌ها"""
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        return upload_dir
    
    def save_document_file(self, file_data, filename, entry_number):
        """ذخیره فایل عکس در پوشه آپلود"""
        try:
            upload_dir = self.create_uploads_directory()
            
            # ایجاد پوشه مخصوص این ورودی
            entry_dir = upload_dir / f"entry_{entry_number}"
            entry_dir.mkdir(exist_ok=True)
            
            # تولید نام فایل منحصر به فرد
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = Path(filename).suffix
            new_filename = f"{timestamp}_{filename}"
            file_path = entry_dir / new_filename
            
            # ذخیره فایل
            if isinstance(file_data, bytes):
                # اگر داده باینری است
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            else:
                # اگر داده base64 است
                import base64
                if isinstance(file_data, str) and ',' in file_data:
                    file_data = file_data.split(',')[1]
                file_bytes = base64.b64decode(file_data)
                with open(file_path, 'wb') as f:
                    f.write(file_bytes)
            
            file_size = file_path.stat().st_size
            print(f"✅ فایل {filename} ذخیره شد (حجم: {file_size} بایت)")
            return str(file_path), file_size
            
        except Exception as e:
            print(f"❌ خطا در ذخیره فایل: {e}")
            raise e
    
    def create_entry(self, form_data, items_data, documents_data=None):
        """ایجاد یک رکورد جدید در پایگاه داده"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # بررسی وجود شماره ورود تکراری
            if 'entry_number' in form_data:
                cursor.execute('SELECT id FROM entry_forms WHERE entry_number = ?', (form_data['entry_number'],))
                existing_entry = cursor.fetchone()
                
                if existing_entry:
                    # اگر شماره تکراری است، شماره جدید تولید کن
                    new_entry_number = self.generate_unique_entry_number()
                    print(f"⚠️ شماره ورود تکراری! شماره جدید تولید شد: {new_entry_number}")
                    form_data['entry_number'] = new_entry_number
            else:
                # اگر شماره ورود وجود ندارد، تولید کن
                form_data['entry_number'] = self.generate_unique_entry_number()
            
            # درج داده‌های اصلی فرم
            cursor.execute('''
                INSERT INTO entry_forms (
                    entry_number, entry_date, entry_time, full_name, 
                    vehicle_number, roadway_bill, internal_bill, 
                    controller, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                form_data['entry_number'],
                form_data['entry_date'],
                form_data['entry_time'],
                form_data['full_name'],
                form_data.get('vehicle_number', ''),
                form_data.get('roadway_bill', ''),
                form_data.get('internal_bill', ''),
                form_data.get('controller', ''),
                form_data.get('description', '')
            ))
            
            entry_id = cursor.lastrowid
            print(f"✅ فرم اصلی با ID {entry_id} ایجاد شد")
            
            # درج آیتم‌های کالا
            for item in items_data:
                cursor.execute('''
                    INSERT INTO entry_items (
                        entry_id, row_number, item_name, serial_number,
                        invoice_number, quantity, unit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry_id,
                    item['row'],
                    item['name'],
                    item.get('serial', ''),
                    item.get('invoice', ''),
                    float(item['quantity']),
                    item['unit']
                ))
            print(f"✅ {len(items_data)} آیتم اضافه شد")
            
            # درج اسناد اسکن شده
            if documents_data:
                for doc in documents_data:
                    file_path, file_size = self.save_document_file(
                        doc['file_data'],
                        doc['filename'],
                        form_data['entry_number']
                    )
                    
                    cursor.execute('''
                        INSERT INTO scanned_documents (
                            entry_id, document_name, document_type,
                            file_path, file_size, mime_type
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        entry_id,
                        doc['filename'],
                        doc.get('type', 'scanned'),
                        file_path,
                        file_size,
                        doc.get('mime_type', 'image/jpeg')
                    ))
                print(f"✅ {len(documents_data)} سند اضافه شد")
            
            conn.commit()
            print(f"✅ تمام تغییرات ثبت شد")
            return entry_id, form_data['entry_number']
            
        except Exception as e:
            conn.rollback()
            print(f"❌ خطا در ایجاد فرم: {e}")
            raise e
        finally:
            conn.close()
    
    def get_entry_by_number(self, entry_number):
        """دریافت اطلاعات یک فرم بر اساس شماره ورود"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # اطلاعات اصلی فرم
            cursor.execute('''
                SELECT * FROM entry_forms WHERE entry_number = ?
            ''', (entry_number,))
            form_data = cursor.fetchone()
            
            if not form_data:
                return None
            
            # آیتم‌های کالا
            cursor.execute('''
                SELECT row_number, item_name, serial_number, invoice_number, quantity, unit
                FROM entry_items WHERE entry_id = ? ORDER BY row_number
            ''', (form_data[0],))
            items = cursor.fetchall()
            
            # اسناد اسکن شده
            cursor.execute('''
                SELECT document_name, document_type, file_path, file_size, scan_timestamp
                FROM scanned_documents WHERE entry_id = ? ORDER BY scan_timestamp
            ''', (form_data[0],))
            documents = cursor.fetchall()
            
            # تبدیل به دیکشنری
            result = {
                'id': form_data[0],
                'entry_number': form_data[1],
                'entry_date': form_data[2],
                'entry_time': form_data[3],
                'full_name': form_data[4],
                'vehicle_number': form_data[5],
                'roadway_bill': form_data[6],
                'internal_bill': form_data[7],
                'controller': form_data[8],
                'description': form_data[9],
                'created_at': form_data[10],
                'items': [],
                'documents': []
            }
            
            for item in items:
                result['items'].append({
                    'row': item[0],
                    'name': item[1],
                    'serial': item[2],
                    'invoice': item[3],
                    'quantity': item[4],
                    'unit': item[5]
                })
            
            for doc in documents:
                result['documents'].append({
                    'name': doc[0],
                    'type': doc[1],
                    'file_path': doc[2],
                    'file_size': doc[3],
                    'timestamp': doc[4]
                })
            
            return result
            
        except Exception as e:
            print(f"❌ خطا در دریافت فرم: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_entries(self, limit=100, offset=0):
        """دریافت تمام فرم‌ها با قابلیت صفحه‌بندی"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, entry_number, entry_date, full_name, vehicle_number, created_at
                FROM entry_forms 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            entries = cursor.fetchall()
            
            result = []
            for entry in entries:
                result.append({
                    'id': entry[0],
                    'entry_number': entry[1],
                    'entry_date': entry[2],
                    'full_name': entry[3],
                    'vehicle_number': entry[4],
                    'created_at': entry[5]
                })
            
            return result
            
        except Exception as e:
            print(f"❌ خطا در دریافت لیست فرم‌ها: {e}")
            return []
        finally:
            conn.close()
    
    def get_document_file(self, entry_number, document_name):
        """دریافت فایل سند"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT sd.file_path, sd.mime_type
                FROM scanned_documents sd
                JOIN entry_forms ef ON sd.entry_id = ef.id
                WHERE ef.entry_number = ? AND sd.document_name = ?
            ''', (entry_number, document_name))
            
            document = cursor.fetchone()
            
            if document and os.path.exists(document[0]):
                with open(document[0], 'rb') as f:
                    file_data = f.read()
                return file_data, document[1]
            
            return None, None
            
        except Exception as e:
            print(f"❌ خطا در دریافت سند: {e}")
            return None, None
        finally:
            conn.close()
    
    def delete_entry(self, entry_number):
        """حذف یک فرم و تمام داده‌های مرتبط"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # پیدا کردن entry_id
            cursor.execute('SELECT id FROM entry_forms WHERE entry_number = ?', (entry_number,))
            entry = cursor.fetchone()
            
            if not entry:
                return False
            
            entry_id = entry[0]
            
            # حذف اسناد از سیستم فایل
            cursor.execute('SELECT file_path FROM scanned_documents WHERE entry_id = ?', (entry_id,))
            documents = cursor.fetchall()
            
            for doc in documents:
                if os.path.exists(doc[0]):
                    try:
                        os.remove(doc[0])
                        print(f"✅ فایل {doc[0]} حذف شد")
                    except Exception as e:
                        print(f"⚠️ خطا در حذف فایل {doc[0]}: {e}")
            
            # حذف داده‌ها از پایگاه داده
            cursor.execute('DELETE FROM scanned_documents WHERE entry_id = ?', (entry_id,))
            cursor.execute('DELETE FROM entry_items WHERE entry_id = ?', (entry_id,))
            cursor.execute('DELETE FROM entry_forms WHERE id = ?', (entry_id,))
            
            conn.commit()
            print(f"✅ فرم {entry_number} با موفقیت حذف شد")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ خطا در حذف فرم: {e}")
            return False
        finally:
            conn.close()
    
    def get_statistics(self):
        """دریافت آمار پایگاه داده"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM entry_forms')
            total_entries = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM entry_items')
            total_items = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM scanned_documents')
            total_documents = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(file_size) FROM scanned_documents')
            total_storage = cursor.fetchone()[0] or 0
            
            return {
                'total_entries': total_entries,
                'total_items': total_items,
                'total_documents': total_documents,
                'total_storage_mb': round(total_storage / (1024 * 1024), 2)
            }
            
        except Exception as e:
            print(f"❌ خطا در دریافت آمار: {e}")
            return {}
        finally:
            conn.close()

# تست پایگاه داده
def test_database():
    """تابع تست پایگاه داده"""
    print("🧪 شروع تست پایگاه داده...")
    
    # ایجاد نمونه پایگاه داده
    db = GoodsEntryDB()
    
    # ایجاد 3 فرم تستی
    for i in range(3):
        form_data = {
            'entry_date': '1403/07/15',
            'entry_time': '14:30:25',
            'full_name': f'کاربر تستی {i+1}',
            'vehicle_number': f'55ب{10000 + i}',
            'roadway_bill': f'RW140300{i+1}',
            'internal_bill': f'INT140300{i+1}',
            'controller': 'احمدی',
            'description': f'ورود تستی شماره {i+1}'
        }
        
        items_data = [
            {
                'row': 1,
                'name': f'کالای تستی {i+1}',
                'serial': f'SN00{i+1}',
                'invoice': f'INV00{i+1}',
                'quantity': i + 1,
                'unit': 'عدد'
            }
        ]
        
        try:
            # ایجاد یک تصویر نمونه ساده (بدون نیاز به فایل خارجی)
            sample_image_data = b'fake_image_data_for_testing_' + str(i).encode()
            
            sample_documents = [
                {
                    'filename': f'بارنامه_test_{i+1}.jpg',
                    'file_data': sample_image_data,
                    'type': 'roadway_bill',
                    'mime_type': 'image/jpeg'
                }
            ]
            
            # درج داده‌های نمونه
            entry_id, entry_number = db.create_entry(form_data, items_data, sample_documents)
            print(f"✅ فرم {i+1} با شماره {entry_number} ایجاد شد (ID: {entry_id})")
            
        except Exception as e:
            print(f"⚠️ ایجاد فرم {i+1} با خطا مواجه شد: {e}")
            try:
                # اگر خطا داشت، بدون عکس ایجاد کن
                entry_id, entry_number = db.create_entry(form_data, items_data)
                print(f"✅ فرم {i+1} با شماره {entry_number} با موفقیت ایجاد شد (بدون عکس)")
            except Exception as e2:
                print(f"❌ ایجاد فرم بدون عکس هم با خطا مواجه شد: {e2}")
    
    # نمایش آمار
    stats = db.get_statistics()
    print("\n📊 آمار پایگاه داده:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # دریافت لیست تمام فرم‌ها
    entries = db.get_all_entries()
    print(f"\n📋 لیست فرم‌های موجود ({len(entries)} فرم):")
    for entry in entries:
        print(f"   - {entry['entry_number']}: {entry['full_name']}")

if __name__ == "__main__":
    test_database()