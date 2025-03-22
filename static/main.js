// main.js

// Fonksiyon: Seçilen telefon numarasına ait mesajları yükler.
function loadMessages(phone) {
    localStorage.setItem("selectedPhone", phone);
    document.getElementById("current-phone").innerText = "Mesajlar - " + phone;
    var chatMessages = document.getElementById("chat-messages");
    chatMessages.innerHTML = "";

    if (typeof allMessages !== "undefined" && allMessages[phone]) {
        allMessages[phone].forEach(function(msg) {
            var date = new Date(msg.date_created).toLocaleString();

            if (msg.message_guest && msg.message_guest.trim() !== "") {
                chatMessages.innerHTML += `
                    <div class="message left-message">
                        <div class="message-content">
                            <strong>(${date}):</strong> ${msg.message_guest}
                        </div>
                    </div>
                `;
            }
            if (msg.message_agent && msg.message_agent.trim() !== "") {
                chatMessages.innerHTML += `
                    <div class="message right-message">
                        <div class="message-content">
                            <strong>(${date}):</strong> ${msg.message_agent}
                        </div>
                    </div>
                `;
            }
            if (msg.message_ai && msg.message_ai.trim() !== "") {
                chatMessages.innerHTML += `
                    <div class="message right-message ai-message">
                        <div class="message-content">
                            <strong>(${date}):</strong> ${msg.message_ai}
                        </div>
                    </div>
                `;
            }
        });
    } else {
        chatMessages.innerHTML = "<div class='message'>Mesaj bulunamadı.</div>";
    }
    scrollToBottom();
}

// Fonksiyon: Mesaj gönderme işlemini yapar.
function sendMessage() {
    var phoneElement = document.getElementById("current-phone").innerText;
    var phone = phoneElement.split(" - ")[1] || "";
    var messageContent = document.getElementById("message").value;

    if (!phone || !messageContent) {
        alert("Telefon numarası veya mesaj boş olamaz!");
        return;
    }

    $.ajax({
        url: "/send",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ phone: phone, message: messageContent }),
        success: function(response) {
            alert("Mesaj başarıyla gönderildi!");
            document.getElementById("message").value = "";
            loadMessages(phone);
        },
        error: function(xhr) {
            alert("Mesaj gönderilemedi: " + xhr.responseText);
        }
    });
}

// Document hazır olduğunda çalışacak kodlar
$(document).ready(function() {
    // Toggle Switch: Sayfa yüklendiğinde toggle durumunu localStorage'dan alıp uygula
    var savedToggle = localStorage.getItem("n8nToggleState");
    if (savedToggle && savedToggle === "on") {
        $("#n8nToggle").prop("checked", true);
        $("#n8n-status-text").text("AI ON");
    } else {
        $("#n8nToggle").prop("checked", false);
        $("#n8n-status-text").text("AI OFF");
    }

    // Toggle Switch Event Listener
    $("#n8nToggle").change(function() {
        let isN8NActive = $(this).is(":checked") ? "on" : "off";
        localStorage.setItem("n8nToggleState", isN8NActive);
        $("#n8n-status-text").text(isN8NActive.toUpperCase());
        
        // Webhook'u çalıştır
        $.ajax({
            url: "https://mkara.app.n8n.cloud/webhook/733fd66c-ae02-478b-a2b1-d0112ac94101",
            type: "GET",
            data: { status: isN8NActive },
            success: function(response) {
                console.log("📌 N8N güncellendi:", response);
            },
            error: function() {
                console.log("❌ N8N değişikliği başarısız!");
            }
        });
    });

    // Kullanıcı yazıyor mu? (Textarea odakta)
    let isTyping = false;
    let messageBox = document.getElementById("message");
    messageBox.addEventListener("focus", function() { isTyping = true; });
    messageBox.addEventListener("blur", function() { isTyping = false; });

    // Eğer daha önce bir telefon seçildiyse, sayfa yüklendiğinde otomatik o numarayı yükle
    let savedPhone = localStorage.getItem("selectedPhone");
    if (savedPhone) {
        loadMessages(savedPhone);
    }

    // Otomatik yenileme (polling): Her 10 saniyede bir, eğer kullanıcı yazmıyorsa tam sayfa reload
    setInterval(function() {
        if (!isTyping) {
            window.location.reload();
        }
    }, 10000);
});

// Scroll'u en alta çeken fonksiyon
function scrollToBottom() {
    let chatMessages = document.getElementById("chat-messages");
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
  