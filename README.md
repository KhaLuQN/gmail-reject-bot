# 🤖 Gmail Reject Auto-Reply Bot

Bot Telegram tự động quét email bị nhãn **rejected** trên Gmail và gửi email từ chối hàng loạt.

**Phiên bản mới:** Sử dụng **App Password + IMAP/SMTP** thay vì OAuth2 để dễ dàng cài đặt hơn!

---

## 📋 Luồng hoạt động

```
Telegram /scan
 ↓
Quét Gmail (folder: rejected, chưa có: replied)
 ↓
Báo danh sách → Hỏi xác nhận
 ↓ (bấm ✅ Xác nhận)
Gửi từng email (delay 1.5s/email)
 ↓
Cập nhật folder: chuyển từ rejected sang replied
 ↓
Báo kết quả về Telegram
```

---

## 🚀 Cài đặt

### Bước 1: Cài Python dependencies

```bash
pip install -r requirements.txt
```

### Bước 2: Tạo Telegram Bot

1. Nhắn tin `@BotFather` trên Telegram
2. Gõ `/newbot` → Đặt tên → Lấy **Token**
3. Nhắn `@userinfobot` để lấy **User ID** của bạn

### Bước 3: Tạo Gmail App Password

1. Vào [Google Account Security](https://myaccount.google.com/security)
2. Bật **2-Step Verification** (nếu chưa bật)
3. Tìm **App passwords**
4. Tạo mới:
   - App: Mail
   - Device: Custom name (ví dụ: "Gmail Reject Bot")
5. Copy password (ví dụ: `abcd efgh ijkl mnop`)

### Bước 4: Cấu hình .env

```bash
cp .env.example .env
```

Mở file `.env` và điền:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABCdef...      # Token từ BotFather
ALLOWED_USER_IDS=987654321               # User ID của bạn

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop        # App Password

# IMAP Configuration
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=abcd efgh ijkl mnop        # App Password

# Sender Info
SENDER_NAME=Phòng Nhân Sự
SENDER_COMPANY=Công ty ABC
```

### Bước 5: Tạo folder Gmail

Trong Gmail:
- Tạo folder tên **`rejected`** (bot sẽ quét folder này)
- Di chuyển email cần reply từ chối vào folder này
- Bot sẽ tự tạo folder **`replied`** sau khi gửi

### Bước 6: Chỉnh template email từ chối

Mở file `config.py`, chỉnh phần:

```python
EMAIL_BODY_PLAIN = """..."""
EMAIL_BODY_HTML = """..."""
```

Các biến có thể dùng trong template:
| Biến | Ý nghĩa |
|------|---------|
| `{name}` | Tên người nhận (auto-detect từ email) |
| `{email}` | Địa chỉ email người nhận |
| `{subject}` | Tiêu đề email gốc |
| `{company}` | Tên công ty (từ .env) |
| `{sender_name}` | Tên người gửi (từ .env) |

### Bước 7: Chạy bot

```bash
python bot.py
```

Hoặc dùng virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
```

---

## 📱 Sử dụng

| Lệnh | Chức năng |
|------|-----------|
| `/start` | Xem hướng dẫn |
| `/scan` | Quét email rejected và hỏi xác nhận |
| `/status` | Xem có job nào đang pending không |
| `/help` | Hướng dẫn chi tiết |

---

## ⚙️ Cấu hình nâng cao

| Tham số | Mặc định | Ý nghĩa |
|---------|---------|---------|
| `MAX_EMAILS_PER_SCAN` | 200 | Số email tối đa mỗi lần quét |
| `SEND_DELAY_SECONDS` | 1.5 | Delay giữa 2 email (giây) |
| `REJECTED_LABEL` | `rejected` | Tên folder cần quét |
| `REPLIED_LABEL` | `replied` | Tên folder sau khi gửi |

---

## 🛡️ Bảo mật

- **Không commit** file `.env` lên git
- Thêm vào `.gitignore`:
  ```
  .env
  *.log
  __pycache__/
  .venv/
  venv/
  ```
- Chỉ những User ID trong `ALLOWED_USER_IDS` mới dùng được bot

---

## 📊 Giới hạn Gmail

| Loại tài khoản | Giới hạn gửi/ngày |
|---------------|------------------|
| Gmail cá nhân | ~500 email |
| Google Workspace | ~2,000 email |

Bot đã có delay 1.5s/email để tránh bị rate limit.

---

## 🐛 Lỗi thường gặp

**`Authentication failed`**
→ Kiểm tra App Password, đảm bảo 2-Step Verification đã bật

**`Folder 'rejected' không tìm thấy`**
→ Chưa tạo folder trong Gmail hoặc tên folder sai

**`Unauthorized`** trong Telegram
→ User ID của bạn chưa có trong `ALLOWED_USER_IDS`

---

## 🚀 Chạy bot với systemd (Linux)

Tạo file `/etc/systemd/system/gmail-reject-bot.service`:

```ini
[Unit]
Description=Gmail Reject Auto-Reply Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/gmail-reject-bot
Environment=PATH=/home/ubuntu/gmail-reject-bot/venv/bin
ExecStart=/home/ubuntu/gmail-reject-bot/venv/bin/python3 /home/ubuntu/gmail-reject-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Kích hoạt và chạy:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gmail-reject-bot.service
sudo systemctl start gmail-reject-bot.service
```

Kiểm tra trạng thái:

```bash
sudo systemctl status gmail-reject-bot.service
```

Xem logs:

```bash
sudo journalctl -u gmail-reject-bot.service -f
```