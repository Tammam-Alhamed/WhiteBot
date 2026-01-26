import requests
import json
import config

def get_products():
    # الرابط حسب التوثيق: /products
    url = f"{config.API_BASE_URL}/products"
    
    # السر كله هنا: التوكن يوضع في الهيدر باسم 'api-token'
    headers = {
        "api-token": config.API_TOKEN,
        "Content-Type": "application/json"
    }
    
    print(f"📡 جاري الاتصال بـ: {url}")
    print(f"🔑 الهيدر المرسل: {headers}")

    try:
        response = requests.get(url, headers=headers)
        
        print(f"📥 كود الحالة: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # حفظ المنتجات في ملف
            with open("products_list.txt", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            print("\n✅ تم جلب المنتجات بنجاح!")
            print("💾 تم الحفظ في ملف 'products_list.txt'")
            
            # عرض أول منتج كمثال
            if isinstance(data, list) and len(data) > 0:
                print("\nمثال على أول منتج:")
                print(json.dumps(data[0], indent=4, ensure_ascii=False))
        else:
            print("❌ فشل الاتصال.")
            print("الرد:", response.text)

    except Exception as e:
        print(f"خطأ برمجي: {e}")

if __name__ == "__main__":
    get_products()