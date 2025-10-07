from flask import Flask, request, jsonify, send_file
from database import GoodsEntryDB
import json
import io
from datetime import datetime
import base64

app = Flask(__name__)
db = GoodsEntryDB()

# فعال کردن CORS برای توسعه
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/entries', methods=['POST', 'OPTIONS'])
def create_entry():
    """ایجاد یک فرم جدید"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        data = request.get_json()
        print("📥 دریافت داده‌های فرم:")
        print(f"   شماره ورود: {data.get('entry_number', 'تولید خودکار')}")
        print(f"   نام: {data.get('full_name')}")
        print(f"   تعداد آیتم‌ها: {len(data.get('items', []))}")
        print(f"   تعداد اسناد: {len(data.get('documents', []))}")
        
        # اعتبارسنجی داده‌های ضروری
        required_fields = ['entry_date', 'entry_time', 'full_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'فیلد {field} ضروری است'}), 400
        
        form_data = {
            'entry_number': data.get('entry_number'),  # اختیاری - اگر نبود خودکار تولید می‌شود
            'entry_date': data['entry_date'],
            'entry_time': data['entry_time'],
            'full_name': data['full_name'],
            'vehicle_number': data.get('vehicle_number', ''),
            'roadway_bill': data.get('roadway_bill', ''),
            'internal_bill': data.get('internal_bill', ''),
            'controller': data.get('controller', ''),
            'description': data.get('description', '')
        }
        
        items_data = data.get('items', [])
        documents_data = data.get('documents', [])
        
        # تبدیل base64 به باینری برای اسناد
        processed_documents = []
        for doc in documents_data:
            processed_documents.append({
                'filename': doc['fileName'],
                'file_data': doc['fileData'],  # داده base64
                'type': doc.get('type', 'scanned'),
                'mime_type': doc.get('mimeType', 'image/jpeg')
            })
        
        entry_id, final_entry_number = db.create_entry(form_data, items_data, processed_documents)
        
        return jsonify({
            'success': True,
            'message': 'فرم با موفقیت ثبت شد',
            'entry_id': entry_id,
            'entry_number': final_entry_number
        })
        
    except Exception as e:
        print(f"❌ خطا در ایجاد فرم: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<entry_number>', methods=['GET'])
def get_entry(entry_number):
    """دریافت اطلاعات یک فرم"""
    try:
        entry = db.get_entry_by_number(entry_number)
        if not entry:
            return jsonify({'error': 'فرم یافت نشد'}), 404
        
        return jsonify(entry)
        
    except Exception as e:
        print(f"❌ خطا در دریافت فرم: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries', methods=['GET'])
def get_all_entries():
    """دریافت لیست تمام فرم‌ها"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        entries = db.get_all_entries(limit, offset)
        return jsonify(entries)
        
    except Exception as e:
        print(f"❌ خطا در دریافت لیست فرم‌ها: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<entry_number>/<document_name>', methods=['GET'])
def get_document(entry_number, document_name):
    """دریافت فایل سند"""
    try:
        file_data, mime_type = db.get_document_file(entry_number, document_name)
        if not file_data:
            return jsonify({'error': 'سند یافت نشد'}), 404
        
        return send_file(
            io.BytesIO(file_data),
            mimetype=mime_type,
            as_attachment=True,
            download_name=document_name
        )
        
    except Exception as e:
        print(f"❌ خطا در دریافت سند: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """دریافت آمار پایگاه داده"""
    try:
        stats = db.get_statistics()
        return jsonify(stats)
    except Exception as e:
        print(f"❌ خطا در دریافت آمار: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<entry_number>', methods=['DELETE'])
def delete_entry(entry_number):
    """حذف یک فرم"""
    try:
        success = db.delete_entry(entry_number)
        if not success:
            return jsonify({'error': 'فرم یافت نشد'}), 404
        
        return jsonify({'success': True, 'message': 'فرم با موفقیت حذف شد'})
        
    except Exception as e:
        print(f"❌ خطا در حذف فرم: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """بررسی سلامت سرور"""
    return jsonify({'status': 'ok', 'message': 'سرور فعال است'})

@app.route('/api/generate-entry-number', methods=['GET'])
def generate_entry_number():
    """تولید شماره ورود منحصر به فرد"""
    try:
        unique_number = db.generate_unique_entry_number()
        return jsonify({'entry_number': unique_number})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 سرور API در حال راه‌اندازی...")
    print("📝 آدرس‌های در دسترس:")
    print("   POST /api/entries - ایجاد فرم جدید")
    print("   GET /api/entries - دریافت لیست فرم‌ها")
    print("   GET /api/entries/<شماره> - دریافت اطلاعات فرم")
    print("   GET /api/documents/<شماره>/<نام فایل> - دریافت سند")
    print("   GET /api/statistics - دریافت آمار")
    print("   DELETE /api/entries/<شماره> - حذف فرم")
    print("   GET /api/health - بررسی سلامت سرور")
    print("   GET /api/generate-entry-number - تولید شماره ورود")
    print("\n🌐 سرور در آدرس: http://localhost:5000")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی سرور: {e}")
        print("💡 ممکن است پورت 5000 در حال استفاده باشد. پورت دیگری امتحان کنید:")
        print("   app.run(debug=True, host='0.0.0.0', port=5001)")