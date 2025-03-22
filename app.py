from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import requests
from datetime import datetime, timezone
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "otelmesajlasmasistemi2024"

# Directus API ayarları
DIRECTUS_URL = "https://directus-production-091d.up.railway.app/items/Messages"
DIRECTUS_USERS_URL = "https://directus-production-091d.up.railway.app/items/accountid"
DIRECTUS_TOKEN = "Bearer 7jAStr5AFo02IKTFicsLX_AIPIa37kHK"

# WhatsApp API Bilgileri
ACCESS_TOKEN = "EAAURqWXNsSEBOwLKwLJQLZAfneCVpeslGlJby5ukdUlqoqN17GsP1BwEEdFKSEoZBlhUbZBgzke7glcn3IqYcmFSRLNdV6tyA43CH8XbXuX09P4LwLtAvvos6BbZBPeQkLKHFJzNx2T5ZBxRg8bkPgZBMLJDYCHdn64KYSyWZAOAlXA9ObjZBpvAM2EY334G88dy4QZDZD"
PHONE_NUMBER_ID = "577431015454085"
WHATSAPP_API_URL = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

# Ana sayfa - giriş sayfasına yönlendir
@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# Kayıt (Register) endpoint'i
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name", "")
        role = request.form.get("role", "personel")

        account_id = str(uuid.uuid4())

        headers = {
            "Authorization":f"Bearer{DIRECTUS_TOKEN}" ,# Bearer kelimesi eklenmeyecek, token doğrudan veriliyor
            "Content-Type": "application/json"
        }

        data = {
            "email": email,
            "password": password,
            "accountid": account_id,
            "name": name,
            "role": role
        }

        response = requests.post(DIRECTUS_USERS_URL, json=data, headers=headers)

        if response.ok:
            flash("✅ Kayıt başarılı! Giriş yapabilirsiniz.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"❌ Kayıt başarısız! Hata: {response.text}", "danger")

    return render_template("register.html")

# Giriş (Login) endpoint'i
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        headers = {
           "Authorization":f"Bearer{DIRECTUS_TOKEN}" ,# Bearer kelimesi eklenmeyecek, token doğrudan veriliyor
            "Content-Type": "application/json"
        }

        # Directus üzerinden, girilen e-posta ile kullanıcı sorgulaması
        params = {
            "filter[email][_eq]": email
        }
        response = requests.get(DIRECTUS_USERS_URL, headers=headers, params=params)

        if response.ok:
            data = response.json()
            users = data.get("data", [])
            if users:
                user = users[0]
                # Şifreler düz metin olarak saklandığı için doğrudan karşılaştırma yapıyoruz
                if user.get("password") == password:
                    session["user"] = user  # Oturuma kullanıcı bilgisini kaydediyoruz
                    flash("✅ Giriş başarılı!", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("❌ Şifre yanlış.", "danger")
            else:
                flash("❌ Kullanıcı bulunamadı.", "danger")
        else:
            flash(f"❌ Giriş sırasında hata oluştu: {response.text}", "danger")
    
    return render_template("login.html")

# Kullanıcı paneli (Dashboard)
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("❌ Lütfen önce giriş yapınız.", "danger")
        return redirect(url_for("login"))
    
    user = session["user"]
    headers = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}
    
    try:
        response = requests.get(DIRECTUS_URL, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            flash("Directus'tan veri alınamadı veya veri boş.", "warning")
    except requests.exceptions.RequestException as e:
        flash(f"Directus bağlantısı başarısız! Hata Detayı: {str(e)}", "danger")
        return render_template("index.html", messages={}, phone_list=[], user=user)

    # Kullanıcıya atanmış mesajları filtrele
    filtered_data = [msg for msg in data if msg.get("assigned_to") == user["accountid"]]
    
    unique_phones = list(set(msg.get("phone", "Bilinmeyen") for msg in filtered_data))
    
    grouped_messages = {}
    
    for record in filtered_data:
        phone = record.get("phone", "Bilinmeyen")
        if phone not in grouped_messages:
            grouped_messages[phone] = []
            
        guest_text = record.get("message_guest") or ""
        agent_text = record.get("message_agent") or ""
        ai_text = record.get("message_ai") or ""
        
        if guest_text.strip():
            grouped_messages[phone].append({
                "date_created": record.get("date_created"),
                "message_guest": guest_text.strip(),
                "message_agent": None,
                "message_ai": None
            })
        if agent_text.strip():
            grouped_messages[phone].append({
                "date_created": record.get("date_created"),
                "message_guest": None,
                "message_agent": agent_text.strip(),
                "message_ai": None
            })
        if ai_text.strip():
            grouped_messages[phone].append({
                "date_created": record.get("date_created"),
                "message_guest": None,
                "message_agent": None,
                "message_ai": ai_text.strip()
            })
            
    for phone in grouped_messages:
        grouped_messages[phone].sort(key=lambda x: x["date_created"] or "")
        
    return render_template("index.html", 
                          messages=grouped_messages, 
                          phone_list=unique_phones,
                          user=user)

# Mesaj gönderme API'si
@app.route("/send", methods=["POST"])
def send_message():
    """Mesajı Directus'a kaydet ve WhatsApp'a gönder"""
    if "user" not in session:
        return jsonify({"error": "Oturum açmanız gerekiyor!"}), 401
        
    phone = request.json.get("phone")
    message = request.json.get("message")
    
    if not phone or not message:
        return jsonify({"error": "Telefon numarası ve mesaj boş olamaz!"}), 400
        
    user = session["user"]
    
    headers = {
        "Authorization": f"Bearer {DIRECTUS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "sender": "agent",
        "date_created": datetime.now(timezone.utc).isoformat(),
        "status": "draft",
        "phone": phone,
        "message_agent": message,
        "agent_id": user.get("accountid"),  # Mesajı gönderen kullanıcının ID'si
        "agent_name": user.get("name", "Personel")  # Mesajı gönderen kullanıcının adı
    }
    
    directus_response = requests.post(DIRECTUS_URL, json=data, headers=headers)
    
    if not directus_response.ok:
        return jsonify({"error": "Directus'a mesaj kaydedilemedi!", "detail": directus_response.text}), 500
        
    # WhatsApp Mesaj Gönderme
    whatsapp_headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    whatsapp_data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }
    
    wa_response = requests.post(WHATSAPP_API_URL, json=whatsapp_data, headers=whatsapp_headers)
    
    if not wa_response.ok:
        return jsonify({"error": "WhatsApp mesajı gönderilemedi!", "detail": wa_response.text}), 500
        
    return jsonify({"status": "success", "message": "Mesaj başarıyla gönderildi!"})

# Mesajları JSON olarak döndüren API
@app.route("/getMessages")
def get_messages():
    if "user" not in session:
        return jsonify({"error": "Oturum açmanız gerekiyor!"}), 401

    headers = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}
    response = requests.get(DIRECTUS_URL, headers=headers)

    if response.ok:
        all_data = response.json().get("data", [])
        phone_param = request.args.get("phone", default=None)

        if phone_param:
            all_data = [m for m in all_data if m.get("phone") == phone_param]

        all_data = sorted(all_data, key=lambda x: x["date_created"])

        result = []
        for msg in all_data:
            result.append({
                "date_created": msg.get("date_created"),
                "message_guest": msg.get("message_guest"),
                "message_ai": msg.get("message_ai"),
                "message_agent": msg.get("message_agent"),
                "phone": msg.get("phone"),
            })

        return jsonify(result)
    else:
        return jsonify({"error": "Directus bağlantısı başarısız!", "detail": response.text}), 500

# Çıkış yapma
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("✅ Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for("login"))

@app.route("/all-messages")
def all_messages():
    headers = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}
    
    response = requests.get(DIRECTUS_URL, headers=headers)

    if response.ok:
        data = response.json().get("data", [])
        
        # Tüm mesajları ve telefon numaralarını al
        messages = []
        for record in data:
            messages.append({
                "phone": record.get("phone", "Bilinmeyen"),
                "message_guest": record.get("message_guest"),
                "message_agent": record.get("message_agent"),
                "message_ai": record.get("message_ai"),
                "assigned_to": record.get("assigned_to")
            })
        
        return jsonify(messages)
    
    return f"Directus bağlantısı başarısız! Hata Detayı: {response.text}", 500

if __name__ == "__main__":
    app.run(debug=True)
