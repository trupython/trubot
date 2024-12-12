import sqlite3
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os
import random
import string
from datetime import datetime


# إعدادات البوت
TOKEN = "8085198613:AAHrKzvH4k5ByEzr-ATmWDxj4flQr21TtEg"
ADMIN_CHAT_ID = 1825720878
bot = telebot.TeleBot(TOKEN)

# إنشاء قاعدة البيانات
def create_database():
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            publisher TEXT NOT NULL,
            telegram_account TEXT NOT NULL,
            image_path TEXT NOT NULL,
            order_status TEXT DEFAULT 'قيد المعالجة'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            publisher TEXT NOT NULL,
            media_path TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            user_id INTEGER,
            rating INTEGER,
            comment TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        subscription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        referral TEXT,
        interests TEXT,
        telegram_account TEXT,
        avatar_path TEXT,
        points INTEGER DEFAULT 0,
        purchases INTEGER DEFAULT 0,
        sales INTEGER DEFAULT 0,
        ads INTEGER DEFAULT 0,
        products INTEGER DEFAULT 0
    )
''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        balance REAL DEFAULT 0
    )
''')


    conn.commit()
    conn.close()

    # إنشاء الفئات
    categories = [
        "قسم الكتب📚",
        "قسم الاكسسوارات💍",
        "قسم الملابس👗",
        "قسم التحف والهدايا🎁",
        "قسم أدوات التجميل💄",
        "قسم الأدوات المستعملة🛠️",
        "قسم الاجهزة الكهربائية⚡",
        "قسم الاجهزة الالكترونية💻"
    ]
    
    if not os.path.exists("الفئات"):
        os.makedirs("الفئات")
        for category in categories:
            os.makedirs(f"الفئات/{category}")

    if not os.path.exists("إعلانات"):
        os.makedirs("إعلانات")

create_database()

# دالة لإنشاء معرف فريد
def generate_unique_id(prefix):
    while True:
        unique_id = f"{prefix}{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
        if not check_id_exists(unique_id):
            return unique_id

# دالة للتحقق من وجود المعرف في قاعدة البيانات
def check_id_exists(unique_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM products WHERE id=?", (unique_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def send_notification_to_admin(message_type, content):
    try:
        # حفظ الإشعار في قاعدة البيانات
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notifications (type, content)
            VALUES (?, ?)
        """, (message_type, content))
        conn.commit()
        conn.close()

        # إرسال الإشعار للمشرف
        notification_text = f"""
🔔 إشعار جديد!
النوع: {message_type}
المحتوى: {content}
الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        bot.send_message(ADMIN_CHAT_ID, notification_text)
    except Exception as e:
        print(f"Error sending admin notification: {str(e)}")

def notify_subscribers(content):
    try:
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM subscribers WHERE is_active=1")
        subscribers = cursor.fetchall()
        conn.close()

        for subscriber in subscribers:
            try:
                bot.send_message(subscriber[0], content)
            except Exception as e:
                print(f"Error sending notification to user {subscriber[0]}: {str(e)}")
    except Exception as e:
        print(f"Error in notify_subscribers: {str(e)}")

@bot.message_handler(commands=[ 'menu'])
def show_menu(message):
    # إنشاء لوحة المفاتيح
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    delete_button = KeyboardButton("حذف بياناتي ❌")
    update_button = KeyboardButton("تحديث بياناتي 🔄")
    profile_button = KeyboardButton("الملف الشخصي👤")
    
    # إضافة الأزرار إلى لوحة المفاتيح
    keyboard.add(delete_button, update_button, profile_button)
    
    # إرسال الرسالة مع لوحة المفاتيح
    bot.send_message(message.chat.id, "اختر الإجراء الذي ترغب في تنفيذه:", reply_markup=keyboard)
    
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_product_"))
def delete_product(call):
    product_id = call.data.split("_")[-1]
    
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # حذف المنتج من قاعدة البيانات
    cursor.execute("SELECT image_path FROM products WHERE id=?", (product_id,))
    result = cursor.fetchone()
    
    if result:
        image_path = result[0]
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        
        # حذف الصورة من المجلد
        if os.path.exists(image_path):
            os.remove(image_path)
        
        bot.answer_callback_query(call.id, text="✅ تم حذف المنتج بنجاح.")
    else:
        bot.answer_callback_query(call.id, text="❌ لم يتم العثور على المنتج.")
    
    conn.close()    

# دالة حذف الإعلان
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_ad_'))
def handle_delete_ad(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "⛔ عذراً، هذه الخاصية متاحة فقط للمسؤول.")
        return
        
    try:
        ad_id = call.data.split('_')[2]  # استخراج معرف الإعلان
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        
        # الحصول على مسار الملف قبل الحذف
        cursor.execute("SELECT media_path FROM ads WHERE id=?", (ad_id,))
        result = cursor.fetchone()
        
        if result:
            media_path = result[0]
            cursor.execute("DELETE FROM ads WHERE id=?", (ad_id,))
            conn.commit()
            
            # حذف الوسائط من المجلد
            if os.path.exists(media_path):
                os.remove(media_path)

            bot.answer_callback_query(call.id, text="✅ تم حذف الإعلان بنجاح.")
        else:
            bot.answer_callback_query(call.id, text="❌ لم يتم العثور على الإعلان.")
        
        conn.close()
    except Exception as e:
        bot.answer_callback_query(call.id, text=f"❌ حدث خطأ أثناء حذف الإعلان: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
def handle_rating(call):
    product_id = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton(
            f"{i}⭐", 
            callback_data=f"star_{product_id}_{i}"
        ))
    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('star_'))
def handle_star_rating(call):
    _, product_id, rating = call.data.split('_')
    
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO ratings (product_id, user_id, rating)
            VALUES (?, ?, ?)
        """, (product_id, call.from_user.id, rating))
        conn.commit()
        
        msg = bot.send_message(
            call.message.chat.id, 
            "هل تريد إضافة تعليق؟ (نعم/لا)"
        )
        bot.register_next_step_handler(msg, process_comment, product_id)
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"حدث خطأ: {str(e)}")
    finally:
        conn.close()

def process_comment(message, product_id):
    if message.text.lower() == 'نعم':
        msg = bot.send_message(message.chat.id, "اكتب تعليقك:")
        bot.register_next_step_handler(msg, save_comment, product_id)
    else:
        bot.send_message(message.chat.id, "✅ تم حفظ تقييمك بنجاح!")

def save_comment(message, product_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    try:
        # نحصل على آخر تقييم للمستخدم لهذا المنتج
        cursor.execute("""
            SELECT id FROM ratings 
            WHERE product_id = ? AND user_id = ? 
            ORDER BY date DESC LIMIT 1
        """, (product_id, message.from_user.id))
        
        rating_id = cursor.fetchone()
        
        if rating_id:
            # تحديث التعليق
            cursor.execute("""
                UPDATE ratings 
                SET comment = ? 
                WHERE id = ?
            """, (message.text, rating_id[0]))
            
            conn.commit()
            bot.send_message(message.chat.id, "✅ تم حفظ تقييمك وتعليقك بنجاح!")
        else:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على تقييمك السابق")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"حدث خطأ: {str(e)}")
    finally:
        conn.close() 
        
# دوال عرض المنتجات
@bot.message_handler(func=lambda message: message.text in ["عرض المنتجات", "المنتجات"])
def show_products(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        bot.send_message(message.chat.id, "لا توجد منتجات حالياً.")
        return

    for product in products:
        try:
            with open(product[7], 'rb') as photo:
                # تقليص الوصف إذا كان أطول من 3 كلمات
                full_description = product[3]
                words = full_description.split()
                if len(words) > 3:
                    short_description = " ".join(words[:3]) + " ..."
                else:
                    short_description = full_description
                caption = f"""
🏷️ اسم المنتج: {product[1]}
💰 السعر: {product[2]:.2f} دولار
📝 الوصف: {short_description}
👤 الناشر: {product[5]}
📱 حساب التلغرام: {product[6]}
🆔 معرف المنتج: {product[0]}
                """
                markup = types.InlineKeyboardMarkup()
                # زر "لمزيد من التفاصيل" لعرض الوصف الكامل
                details_button = types.InlineKeyboardButton(
                    "لمزيد من التفاصيل", 
                    callback_data=f"details_{product[0]}"  # تمرير معرف المنتج
                )
                markup.add(details_button)
                
                # أزرار التحكم
                if message.chat.id == ADMIN_CHAT_ID:
                    delete_button = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_product_{product[0]}")
                    edit_button = types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_product_{product[0]}")
                    markup.add(delete_button, edit_button)
                
                buy_button = types.InlineKeyboardButton("🛒 شراء", url="https://www.paypal.com/ncp/payment/EKL79JPH9S58A")
                contact_button = types.InlineKeyboardButton("🔗 رابط المنتج", callback_data=f"product_link_{product[0]}")
                rate_button = types.InlineKeyboardButton("⭐ تقييم المنتج", callback_data=f"rate_{product[0]}")
                markup.add(buy_button, contact_button)
                markup.add(rate_button)

                bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"حدث خطأ في عرض المنتج: {str(e)}")
            
# معالجة الضغط على زر "لمزيد من التفاصيل"
@bot.callback_query_handler(func=lambda call: call.data.startswith("details_"))
def show_full_details(call):
    # استخراج معرف المنتج من callback_data
    product_id = call.data.split("_")[1]

    # جلب تفاصيل المنتج من قاعدة البيانات
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product:
        # إرسال الوصف الكامل
        full_description = product[3]
        bot.send_message(call.message.chat.id, f"📝 الوصف الكامل:\n{full_description}")
    else:
        bot.send_message(call.message.chat.id, "❌ لم يتم العثور على المنتج.")
        
@bot.message_handler(func=lambda message: message.text == "المشتركين" and message.chat.id == ADMIN_CHAT_ID)
def show_subscribers(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, points FROM subscribers")
    subscribers = cursor.fetchall()
    conn.close()

    if not subscribers:
        bot.send_message(message.chat.id, "لا توجد مشتركين حالياً.")
        return

    for subscriber in subscribers:
        subscriber_info = f"""
👤 **المشترك:**
اسم المستخدم: @{subscriber[1]}
الاسم: {subscriber[2]}
🔢 رصيد النقاط: {subscriber[3]}
"""
        markup = types.InlineKeyboardMarkup()
        edit_button = types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_subscriber_{subscriber[0]}")
        delete_button = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_subscriber_{subscriber[0]}")
        markup.add(edit_button, delete_button)

        bot.send_message(message.chat.id, subscriber_info, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_subscriber_"))
def edit_subscriber(call):
    user_id = call.data.split("_")[-1]
    msg = bot.send_message(call.message.chat.id, "أدخل النقاط الجديدة للمشترك:")
    bot.register_next_step_handler(msg, update_subscriber_points, user_id)

def update_subscriber_points(message, user_id):
    try:
        new_points = int(message.text)
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE subscribers SET points = ? WHERE user_id = ?", (new_points, user_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ تم تحديث النقاط بنجاح.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح للنقاط.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_subscriber_"))
def delete_subscriber(call):
    user_id = call.data.split("_")[-1]
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(call.message.chat.id, "✅ تم حذف المشترك بنجاح.")
    
@bot.callback_query_handler(func=lambda call: call.data.startswith("product_link_"))
def show_product_link(call):
    product_id = call.data.split("_")[-1]
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT product_link FROM products WHERE id=?", (product_id,))
    product_link = cursor.fetchone()
    conn.close()

    if product_link:
        bot.send_message(call.message.chat.id, f"🔗 رابط المنتج: {product_link[0]}")
    else:
        bot.send_message(call.message.chat.id, "❌ لم يتم العثور على رابط المنتج.")
        
def add_product_link_column():
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    try:
        # التحقق مما إذا كان العمود موجودًا بالفعل
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'product_link' not in columns:
            # إضافة العمود الجديد إلى الجدول
            cursor.execute("ALTER TABLE products ADD COLUMN product_link TEXT")
            conn.commit()
            print("تم إضافة العمود product_link بنجاح.")
        else:
            print("العمود product_link موجود بالفعل.")
    except Exception as e:
        print(f"حدث خطأ أثناء إضافة العمود: {str(e)}")
    finally:
        conn.close()

add_product_link_column()


@bot.message_handler(func=lambda message: message.text == "بحث بحسب الفئة 🔍")
def search_by_category(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    categories = [
        "قسم الكتب📚",
        "قسم الاكسسوارات💍",
        "قسم الملابس👗",
        "قسم التحف والهدايا🎁",
        "قسم أدوات التجميل💄",
        "قسم الأدوات المستعملة🛠️",
        "قسم الاجهزة الكهربائية⚡",
        "قسم الاجهزة الالكترونية💻"
    ]
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add(types.KeyboardButton("الواجهة الرئيسية"))
    
    bot.send_message(message.chat.id, "اختر الفئة التي تريد عرض منتجاتها:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    "قسم الكتب📚", "قسم الاكسسوارات💍", "قسم الملابس👗",
    "قسم التحف والهدايا🎁", "قسم أدوات التجميل💄",
    "قسم الأدوات المستعملة🛠️", "قسم الاجهزة الكهربائية⚡",
    "قسم الاجهزة الالكترونية💻"
])
def show_category_products(message):
    category = message.text
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = ?", (category,))
    products = cursor.fetchall()
    conn.close()

    if not products:
        bot.send_message(message.chat.id, f"لا توجد منتجات في {category} حالياً.")
        return

    for product in products:
        try:
            with open(product[7], 'rb') as photo:
                caption = f"""
🏷️ اسم المنتج: {product[1]}
💰 السعر: {product[2]:.2f} دولار
📝 الوصف: {product[3][:100]}...
👤 الناشر: {product[5]}
📱 حساب التلغرام: {product[6]}
🆔 معرف المنتج: {product[0]}
                """
                markup = types.InlineKeyboardMarkup()
                details_button = types.InlineKeyboardButton(
                    "لمزيد من التفاصيل", 
                    callback_data=f"details_{product[0]}"
                )
                buy_button = types.InlineKeyboardButton(
                    "🛒 شراء", 
                    url="https://www.paypal.com/ncp/payment/EKL79JPH9S58A"
                )
                contact_button = types.InlineKeyboardButton("🔗 رابط المنتج", callback_data=f"product_link_{product[0]}")
                markup.add(details_button)
                markup.add(buy_button, contact_button)

                bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"حدث خطأ في عرض المنتج: {str(e)}")

  
                        
# بداية البوت
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "للاشتراك في المتجر",
        "الدخول للمتجر",
        "أضف إعلان 📢",
        "عرض الإعلانات 📜",
        "❓ المساعدة",
        "الواجهة الرئيسية"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])

    with open('patrin.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo)

    bot.send_message(message.chat.id, 
                     "🤗 أهلا وسهلا بكم 🤗\nقد سررنا بزيارتكم الكريمة لمتجر الزعبوط الالكتروني.\n\n(اشترك الآن لتتمكن من عرض منتجاتك ولمتابعة كل جديد في عالم التسوق)",
                     reply_markup=markup)

        
    
# قائمة المساعدة
@bot.message_handler(func=lambda message: message.text == "❓ المساعدة")
def help_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📖 دليل المستخدم", callback_data="user_guide"),
        types.InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq"),
        types.InlineKeyboardButton("🚚 معلومات الشحن", callback_data="shipping"),
        types.InlineKeyboardButton("💳 طرق الدفع", callback_data="payment"),
        types.InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")
    ]
    markup.add(*buttons)
    help_text = "🔰 مركز المساعدة\n\nاختر أحد الأقسام التالية للحصول على المساعدة:"
    bot.send_message(message.chat.id, help_text, reply_markup=markup)

# معالجة الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    back_button = types.InlineKeyboardMarkup()
    back_button.add(types.InlineKeyboardButton("🔙 رجوع للمساعدة", callback_data="back_to_help"))

    if call.data == "user_guide":
        guide_text = """
📖 دليل المستخدم:

1️⃣ تصفح المنتجات:
• اضغط على "المنتجات"
• اختر الفئة المناسبة
• اضغط على المنتج للتفاصيل

2️⃣ الشراء:
•  للشراء المباشر من خلال المتجر إضغط على زر شراء, حيث ان هذا الزر مخصص
للذين يرغبون شراء منتجاتهم من خلال الدفع المباشر لحساب المتجر 
لتقوم إدارة المتجر بشراء المنتج نيابة عن المستخدم وايصاله اليه بحسب عنوانه
لذلك من الضروري الاشتراك فى المتجر ليتمتع المستخدم بهذه الميزة.
• للشراء الخاص إضغط على زر رابط المنتج سينبثق رابط يتم من خلاله نقل المستخدم
الى صفحة المنتج الاساسية ليتمكن من استعراض كافة تفاصيل المنتج ومن ثم شرائه ان رغب بذلك
• لكلا الزرين السابقين خطوات عليك إستيفائها

3️⃣ المتابعة:
• ستصلك رسالة تأكيد
• يمكنك تتبع طلبك
4️⃣ إضافة منتج جديد:
بعد الضغط على إضافة منتج سيتم جمع بيانات المنتج من المستخدم
لذلك على المستخدم ان يضع معلومات صحيحة عن المنتج وعناوين تواصل صالحة وفعالة
5️⃣ إضافة إعلان جديد :
ميزة جديدة تتيح للمستخدمين إضافة اعلانات تجارية لمنتجاتهم
مع مراعاة تعبئة بيانات الاعلان المطلوبة
6️⃣ خصائص المادة الاعلانية :
مقطع فيديو , الامتداد Mp4 على ان لا يتجاوز 35 ثانية
أو صورة متحركة الامتداد Gif

✌️يُرجى الالتزام بمتطلبات إضافة المنتجات و الإعلانات✌️
"""
        bot.edit_message_text(guide_text, call.message.chat.id, call.message.message_id, reply_markup=back_button)

    elif call.data == "faq":
        faq_text = """
❓ الأسئلة الشائعة:

س: كيف أشتري من المتجر؟
ج: اختر المنتج، إضغط على زر شراء ان رغبت بالشراء من خلال بوابة الدفع الالكتروني.
او يمكنك الضغط على زر رابط المنتج للانطلاق للصفحة الخاصة بالمنتج. .

س: ما هي طرق الدفع المتاحة؟
ج: نقبل الدفع عبر PayPal والبطاقات الائتمانية.

س: كم تستغرق عملية الشحن؟
ج: 3-7 أيام عمل داخل البلاد.
"""
        bot.edit_message_text(faq_text, call.message.chat.id, call.message.message_id, reply_markup=back_button)

    elif call.data == "shipping":
        shipping_text = """
🚚 معلومات الشحن:
• الشحن المحلي: 3-7 أيام
• الشحن الدولي: 7-14 يوم
• تتبع الشحنة متاح
"""
        bot.edit_message_text(shipping_text, call.message.chat.id, call.message.message_id, reply_markup=back_button)

    elif call.data == "payment":
        payment_text = """
💳 طرق الدفع المتاحة:

• PayPal
• البطاقات الائتمانية
• التحويل البنكي
•  الدفع عند الاستلام بحال كان البيع والشراء وجاهيا
"""
        bot.edit_message_text(payment_text, call.message.chat.id, call.message.message_id, reply_markup=back_button)

    elif call.data == "contact":
        contact_text = """
📞 اتصل بنا:

• المشرف: @Azoris11
• Trunology77@gmail.com
• واتساب: +9725955-08421
• أوقات العمل: 10 ص - 10 م

🚨 للحالات العاجلة:
https://t.me/azoris11
"""
        bot.edit_message_text(contact_text, call.message.chat.id, call.message.message_id, reply_markup=back_button)

    elif call.data == "back_to_help":
        help_menu(call.message)


@bot.message_handler(func=lambda message: message.text == "الواجهة الرئيسية")
def return_to_main_menu(message):
    start(message)

@bot.message_handler(func=lambda message: message.text == "للاشتراك في المتجر")
def subscribe(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscribers WHERE user_id = ?", (message.chat.id,))
    user_exists = cursor.fetchone()
    conn.close()

    if user_exists:
        bot.send_message(message.chat.id, "✅ أنت مسجل بالفعل في المتجر. يمكنك عرض ملفك الشخصي باستخدام زر 'الملف الشخصي👤'.")
    else:
        msg = bot.send_message(message.chat.id, "👤 أدخل اسمك الكامل:")
        bot.register_next_step_handler(msg, process_name_subscription)

def process_name_subscription(message):
    user_data = {'name': message.text}
    msg = bot.send_message(message.chat.id, "❓ كيف وصلت إلى هنا؟ اختر واحدة:\n1️⃣ من خلال صديق\n2️⃣ من خلال مجموعة")
    bot.register_next_step_handler(msg, process_referral_subscription, user_data)

def process_referral_subscription(message, user_data):
    user_data['referral'] = message.text
    msg = bot.send_message(message.chat.id, "🎯 ما هي اهتماماتك؟ اختر واحدة:\n1️⃣ تسوق\n2️⃣ بائع منتجات\n3️⃣ مروج إعلانات")
    bot.register_next_step_handler(msg, process_interest_subscription, user_data)

def process_interest_subscription(message, user_data):
    user_data['interests'] = message.text
    msg = bot.send_message(message.chat.id, "📱 ضع حسابك على تيليجرام:")
    bot.register_next_step_handler(msg, process_telegram_subscription, user_data)

def process_telegram_subscription(message, user_data):
    user_data['telegram_account'] = message.text
    msg = bot.send_message(message.chat.id, "🖼️ قم بتحميل صورة رمزية:")
    bot.register_next_step_handler(msg, process_avatar_subscription, user_data)
       

def process_avatar_subscription(message, user_data):
    try:
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            avatar_folder = "avatars"
            if not os.path.exists(avatar_folder):
                os.makedirs(avatar_folder)
            avatar_path = f"{avatar_folder}/{message.chat.id}.jpg"
            downloaded_file = bot.download_file(file_info.file_path)
            with open(avatar_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            user_data['avatar_path'] = avatar_path

            # حفظ البيانات في قاعدة البيانات
            conn = sqlite3.connect('store.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO subscribers (user_id, username, first_name, referral, interests, telegram_account, avatar_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message.chat.id, message.chat.username, user_data['name'], user_data['referral'], user_data['interests'], user_data['telegram_account'], avatar_path))
            conn.commit()
            conn.close()

            # إرسال إشعار للمشرف
            admin_notification = f"""
👤 مشترك جديد:
الاسم: {user_data['name']}
المعرف: @{message.chat.username}
الآيدي: {message.chat.id}
"""
            send_notification_to_admin("new_subscriber", admin_notification)

            # رسالة تأكيد للمستخدم
            bot.send_message(message.chat.id, f"✅ شكراً لاشتراكك في متجر الزعبوط الإلكتروني.\n🆔 الرجاء الاحتفاظ بالمعرف الخاص بك: {message.chat.id}")
        else:
            bot.send_message(message.chat.id, "❌ الرجاء إرسال صورة صحيحة!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء الاشتراك: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "تحديث بياناتي 🔄")
def update_profile(message):
    msg = bot.send_message(message.chat.id, "ما الذي تريد تحديثه؟ اختر:\n1️⃣ الاسم\n2️⃣ الاهتمامات\n3️⃣ حساب التلغرام")
    bot.register_next_step_handler(msg, process_update_choice)

# معالجة اختيار المستخدم للتحديث
def process_update_choice(message):
    choice = message.text
    if choice == "1":
        msg = bot.send_message(message.chat.id, "أدخل اسمك الجديد:")
        bot.register_next_step_handler(msg, update_name)
    elif choice == "2":
        msg = bot.send_message(message.chat.id, "أدخل اهتماماتك الجديدة:")
        bot.register_next_step_handler(msg, update_interests)
    elif choice == "3":
        msg = bot.send_message(message.chat.id, "أدخل حساب التلغرام الجديد:")
        bot.register_next_step_handler(msg, update_telegram_account)
    else:
        bot.send_message(message.chat.id, "❌ خيار غير صحيح. حاول مرة أخرى.")

# دالة تحديث الاسم
def update_name(message):
    new_name = message.text
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE subscribers SET first_name = ? WHERE user_id = ?", (new_name, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ تم تحديث اسمك بنجاح.")

# دالة تحديث الاهتمامات
def update_interests(message):
    new_interests = message.text
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE subscribers SET interests = ? WHERE user_id = ?", (new_interests, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ تم تحديث اهتماماتك بنجاح.")

# دالة تحديث حساب التلغرام
def update_telegram_account(message):
    new_account = message.text
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE subscribers SET telegram_account = ? WHERE user_id = ?", (new_account, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ تم تحديث حساب التلغرام بنجاح.")

@bot.message_handler(func=lambda message: message.text == "الملف الشخصي👤")
def show_profile(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, first_name, subscription_date, referral, interests, telegram_account, points, purchases, sales, ads, products, avatar_path
        FROM subscribers
        WHERE user_id = ?
    """, (message.chat.id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        # صياغة نص الملف الشخصي
        profile_text = f"""
👤 **الملف الشخصي:**
اسم المستخدم: @{user_data[0]}
الاسم: {user_data[1]}
📅 تاريخ الاشتراك: {user_data[2]}
🔗 الإحالة: {user_data[3]}
🎯 الاهتمامات: {user_data[4]}
📱 حساب التلغرام: {user_data[5]}
🔢 رصيد النقاط: {user_data[6]}
🛒 عدد المشتريات: {user_data[7]}
🛍️ عدد المبيعات: {user_data[8]}
📢 عدد الإعلانات: {user_data[9]}
📦 عدد المنتجات: {user_data[10]}
        """

        # التحقق من وجود الصورة الرمزية في مجلد avatars
        avatar_path = user_data[11]  # مسار الصورة المخزن في قاعدة البيانات
        if avatar_path and os.path.exists(avatar_path):  # التحقق من وجود الصورة
            with open(avatar_path, 'rb') as avatar:
                bot.send_photo(message.chat.id, avatar, caption=profile_text)
        else:
            # في حال عدم وجود الصورة، يتم إرسال النصوص فقط
            bot.send_message(message.chat.id, profile_text)
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على بياناتك. الرجاء التسجيل أولاً.")

@bot.message_handler(func=lambda message: message.text == "حذف بياناتي ❌")
def confirm_delete(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    yes_button = KeyboardButton("نعم، احذف بياناتي")
    no_button = KeyboardButton("لا، تراجع")
    markup.add(yes_button, no_button)

    bot.send_message(message.chat.id, "⚠️ هل أنت متأكد أنك تريد حذف بياناتك؟", reply_markup=markup)

# إذا أكد المستخدم الحذف
@bot.message_handler(func=lambda message: message.text == "نعم، احذف بياناتي")
def delete_user_data(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (message.chat.id,))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "✅ تم حذف بياناتك بنجاح.")

# إذا تراجع المستخدم
@bot.message_handler(func=lambda message: message.text == "لا، تراجع")
def cancel_delete(message):
    bot.send_message(message.chat.id, "❌ تم إلغاء عملية الحذف.")



@bot.message_handler(func=lambda message: message.text == "الدخول للمتجر")
def login(message):
    if message.chat.id == ADMIN_CHAT_ID:
        admin_menu(message)
    else:
        user_menu(message)

def admin_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "المشتركين",  # إضافة زر المشتركين
        "إضافة منتج جديد",
        "عرض المنتجات",
        "بحث بحسب الفئة 🔍",  # إضافة الزر الجديد
        "الواجهة الرئيسية"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    bot.send_message(message.chat.id, "🎩 مرحبا بك مدير البوت!", reply_markup=markup)

def user_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "الملف الشخصي👤",  # إضافة زر الملف الشخصي
        "إضافة منتج جديد",  # إضافة زر جديد
        "عرض المنتجات",     # إضافة زر جديد
        "بحث بحسب الفئة 🔍",  # إضافة الزر الجديد
        "❓ المساعدة",
        "الواجهة الرئيسية"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    bot.send_message(message.chat.id, "👤 مرحبا بك!", reply_markup=markup)


# دوال إدارة المنتجات
@bot.message_handler(func=lambda message: message.text == "إضافة منتج جديد")
def add_product(message):
   
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    categories = [
        "قسم الكتب📚",
        "قسم الاكسسوارات💍",
        "قسم الملابس👗",
        "قسم التحف والهدايا🎁",
        "قسم أدوات التجميل💄",
        "قسم الأدوات المستعملة🛠️",
        "قسم الاجهزة الكهربائية⚡",
        "قسم الاجهزة الالكترونية💻"
    ]
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add(types.KeyboardButton("الواجهة الرئيسية"))
    
    msg = bot.send_message(message.chat.id, "اختر الفئة المناسبة للمنتج:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_category)

def process_category(message):
    if message.text == "الواجهة الرئيسية":
        start(message)
        return
        
    product_data = {'category': message.text}
    msg = bot.send_message(message.chat.id, "أدخل اسم المنتج:")
    bot.register_next_step_handler(msg, process_name, product_data)

def process_name(message, product_data):
    product_data['name'] = message.text
    msg = bot.send_message(message.chat.id, "أدخل سعر المنتج:")
    bot.register_next_step_handler(msg, process_price, product_data)

def process_price(message, product_data):
    try:
        base_price = float(message.text)  # تحويل السعر المدخل إلى رقم
        final_price = base_price + 5  # إضافة 5 دولارات
        product_data['price'] = final_price
        # توزيع النقاط والعمولات
        distribute_commissions_and_points(base_price)
        msg = bot.send_message(message.chat.id, "أدخل وصف المنتج:")
        bot.register_next_step_handler(msg, process_description, product_data)
    except ValueError:
        msg = bot.send_message(message.chat.id, "الرجاء إدخال سعر صحيح!")
        bot.register_next_step_handler(msg, process_price, product_data)

def distribute_commissions_and_points(base_price):
    # حساب النقاط
    points_to_distribute = (3 / base_price) * 20  # كل 1 دولار = 20 نقطة

    # تحديث نقاط المشتركين
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM subscribers WHERE is_active=1")
    subscribers = cursor.fetchall()

    for subscriber in subscribers:
        cursor.execute("""
            UPDATE subscribers
            SET points = points + ?
            WHERE user_id = ?
        """, (points_to_distribute, subscriber[0]))

    # تحديث عمولة المشرف
    cursor.execute("""
        UPDATE admin
        SET balance = balance + 2
    """)
    conn.commit()
    conn.close()

def process_description(message, product_data):
    product_data['description'] = message.text
    msg = bot.send_message(message.chat.id, "أدخل اسم الناشر:")
    bot.register_next_step_handler(msg, process_publisher, product_data)

def process_publisher(message, product_data):
    product_data['publisher'] = message.text
    msg = bot.send_message(message.chat.id, "أدخل حساب التلغرام الخاص بك:")
    bot.register_next_step_handler(msg, process_telegram, product_data)

def process_telegram(message, product_data):
    product_data['telegram_account'] = message.text
    msg = bot.send_message(message.chat.id, "أدخل رابط المنتج:")
    bot.register_next_step_handler(msg, process_product_link, product_data)
    
def process_product_link(message, product_data):
    product_data['product_link'] = message.text
    msg = bot.send_message(message.chat.id, "قم بإرسال صورة المنتج:")
    bot.register_next_step_handler(msg, process_image, product_data)    

def process_image(message, product_data):
    try:
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            product_id = generate_unique_id("PRD")
            image_path = f"الفئات/{product_data['category']}/{product_id}.jpg"
            
            downloaded_file = bot.download_file(file_info.file_path)
            with open(image_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            conn = sqlite3.connect('store.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (id, name, price, description, category, publisher, telegram_account, image_path, product_link)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (product_id, product_data['name'], product_data['price'], product_data['description'],
      product_data['category'], product_data['publisher'], product_data['telegram_account'], image_path, product_data['product_link']))
            cursor.execute("""
        UPDATE subscribers
        SET products = products + 1
        WHERE user_id = ?
    """, (message.chat.id,))
            conn.commit()
            conn.close()
                       # إضافة إشعار للمشرف
            admin_notification = f"""
🆕 منتج جديد:
الاسم: {product_data['name']}
السعر: {product_data['price']}
الناشر: {product_data['publisher']}
"""
            send_notification_to_admin("new_product", admin_notification)

            # إشعار المشتركين
            subscriber_notification = f"""
🆕 منتج جديد في المتجر!
{product_data['name']}
السعر: {product_data['price']} دولار
الوصف: {product_data['description']}
"""
            notify_subscribers(subscriber_notification) 
            
            bot.send_message(message.chat.id, "✅ تم إضافة المنتج بنجاح!")
        else:
            bot.send_message(message.chat.id, "❌ الرجاء إرسال صورة صحيحة!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء معالجة الصورة: {str(e)}")
 
@bot.message_handler(func=lambda message: message.text == "الملف الشخصي")
def show_profile(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, first_name, points, purchases, sales, ads, products
        FROM subscribers
        WHERE user_id = ?
    """, (message.chat.id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        profile_text = f"""
👤 الملف الشخصي:
اسم المستخدم: {user_data[0]}
الاسم: {user_data[1]}
🔢 رصيد النقاط: {user_data[2]}
🛒 عدد المشتريات: {user_data[3]}
🛍️ عدد المبيعات: {user_data[4]}
📢 عدد الإعلانات: {user_data[5]}
📦 عدد المنتجات: {user_data[6]}
        """
        bot.send_message(message.chat.id, profile_text)
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على بياناتك.")
          
# دالة لمعالجة التواصل مع البائع
@bot.callback_query_handler(func=lambda call: call.data.startswith("contact_seller_"))
def contact_seller(call):
    product_id = call.data.split("_")[-1]
    msg = bot.send_message(call.message.chat.id, "من فضلك، أدخل اسمك:")
    bot.register_next_step_handler(msg, process_contact_name, product_id)

def process_contact_name(message, product_id):
    name = message.text
    msg = bot.send_message(message.chat.id, "الرجاء إدخال عنوانك:")
    bot.register_next_step_handler(msg, process_contact_address, product_id, name)

def process_contact_address(message, product_id, name):
    address = message.text
    msg = bot.send_message(message.chat.id, "الرجاء إدخال رقم هاتفك:")
    bot.register_next_step_handler(msg, process_contact_phone, product_id, name, address)

def process_contact_phone(message, product_id, name, address):
    phone = message.text
    bot.send_message(message.chat.id, f"شكرا لك {name} قد تم تسجيل طلبك بنجاح, الرجاء الانتظار لحين معالجة طلبك.\n(مع تحيات بائع المنتج)")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_product_"))
def delete_product(call):
    product_id = call.data.split("_")[-1]
    
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # حذف المنتج من قاعدة البيانات
    cursor.execute("SELECT image_path FROM products WHERE id=?", (product_id,))
    result = cursor.fetchone()
    
    if result:
        image_path = result[0]
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        
        # حذف الصورة من المجلد
        if os.path.exists(image_path):
            os.remove(image_path)
        
        bot.answer_callback_query(call.id, text="✅ تم حذف المنتج بنجاح.")
    else:
        bot.answer_callback_query(call.id, text="❌ لم يتم العثور على المنتج.")
    
    conn.close()

# دوال الإعلانات
@bot.message_handler(func=lambda message: message.text == "أضف إعلان 📢")
def add_advertisement(message):
    msg = bot.send_message(message.chat.id, "أدخل عنوان الإعلان:")
    bot.register_next_step_handler(msg, process_ad_name)

def process_ad_name(message):
    ad_data = {'name': message.text}
    msg = bot.send_message(message.chat.id, "أدخل وصف الإعلان:")
    bot.register_next_step_handler(msg, process_ad_description, ad_data)

def process_ad_description(message, ad_data):
    ad_data['description'] = message.text
    msg = bot.send_message(message.chat.id, "أدخل اسم الناشر:")
    bot.register_next_step_handler(msg, process_ad_publisher, ad_data)

def process_ad_publisher(message, ad_data):
    ad_data['publisher'] = message.text
    msg = bot.send_message(message.chat.id, "قم بإرسال صورة أو فيديو للإعلان:")
    bot.register_next_step_handler(msg, process_ad_media, ad_data)

def process_ad_media(message, ad_data):
    try:
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
            file_ext = '.jpg'
        elif message.video:
            file_id = message.video.file_id
            file_ext = '.mp4'
        else:
            bot.send_message(message.chat.id, "الرجاء إرسال صورة أو فيديو!")
            return

        ad_id = generate_unique_id("AD")
        media_path = f"إعلانات/{ad_id}{file_ext}"
        
        downloaded_file = bot.download_file(bot.get_file(file_id).file_path)
        with open(media_path, 'wb') as new_file:
            new_file.write(downloaded_file)
                        
        
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ads (id, name, description, publisher, media_path)
            VALUES (?, ?, ?, ?, ?)
        """, (ad_id, ad_data['name'], ad_data['description'], ad_data['publisher'], media_path))
        
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, "✅ تم إضافة الإعلان بنجاح!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء معالجة الوسائط: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "عرض الإعلانات 📜")
def show_advertisements(message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ads")
    ads = cursor.fetchall()
    conn.close()
    
    if not ads:
        bot.send_message(message.chat.id, "لا توجد إعلانات حالياً.")
        return

    for ad in ads:
        try:
            media_path = ad[4]
            caption = f"""
📢 عنوان الإعلان: {ad[1]}
📝 الوصف: {ad[2]}
👤 الناشر: {ad[3]}
🆔 معرف الإعلان: {ad[0]}
            """
            
            # إنشاء أزرار التحكم للمشرف
            markup = None
            if message.chat.id == ADMIN_CHAT_ID:
                markup = types.InlineKeyboardMarkup()
                delete_button = types.InlineKeyboardButton("🗑️ حذف الإعلان", callback_data=f"delete_ad_{ad[0]}")
                markup.add(delete_button)
            
            # إرسال الإعلان مع أزرار التحكم
            if media_path.endswith('.jpg'):
                with open(media_path, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)
            elif media_path.endswith('.mp4'):
                with open(media_path, 'rb') as video:
                    bot.send_video(message.chat.id, video, caption=caption, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء عرض الإعلان: {str(e)}")



def run_bot():
    while True:
        try:
            print("Starting bot...")
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Bot stopped. Restarting...\nError: {str(e)}")
            # إرسال إشعار للمشرف عن الخطأ
            try:
                error_notification = f"""
⚠️ تنبيه: توقف البوت
الخطأ: {str(e)}
الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
جاري إعادة التشغيل...
"""
                bot.send_message(ADMIN_CHAT_ID, error_notification)
            except:
                pass
            
            # انتظار 10 ثواني قبل إعادة المحاولة
            time.sleep(10)
            continue

if __name__ == "__main__":
    # إضافة استيراد وحدة time
    import time
    
    # تشغيل البوت مع المعالجة المستمرة
    run_bot()
