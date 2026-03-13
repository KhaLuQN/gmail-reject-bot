# 🤖 Gmail Reject Auto-Reply Bot

Bot Telegram tự động quét email bị nhãn **rejected** trên Gmail và gửi email từ chối hàng loạt.

---

## 📋 Luồng hoạt động

```
Telegram /scan
    ↓
Quét Gmail (label: rejected, chưa có: replied)
    ↓
Báo danh sách → Hỏi xác nhận
    ↓ (bấm ✅ Xác nhận)
Gửi từng email (delay 1.5s/email)
    ↓
Cập nhật label: xoá "rejected", thêm "replied"
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

### Bước 3: Cấu hình Google Cloud & Gmail API

1. Vào [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới (hoặc chọn project có sẵn)
3. Vào **APIs & Services** → **Enable APIs**
4. Tìm và bật **Gmail API**
5. Vào **OAuth consent screen** → Chọn **External** → Điền thông tin
6. Vào **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
7. Chọn **Desktop app** → Tải file JSON → Đổi tên thành `credentials.json`
8. Đặt `credentials.json` vào thư mục này

### Bước 4: Cấu hình .env

```bash
cp .env.example .env
```

Mở file `.env` và điền:

```env
TELEGRAM_BOT_TOKEN=123456:ABCdef...      # Token từ BotFather
ALLOWED_USER_IDS=987654321               # User ID của bạn
SENDER_NAME=Phòng Nhân Sự
SENDER_COMPANY=Công ty ABC
```

### Bước 5: Tạo label Gmail

Trong Gmail:
- Tạo label tên **`rejected`** (bot sẽ quét label này)
- Gắn label này vào các email cần reply từ chối
- Bot sẽ tự tạo label **`replied`** sau khi gửi

### Bước 6: Chỉnh template email từ chối

Mở file `config.py`, chỉnh phần:

```python
EMAIL_BODY_PLAIN = """..."""
EMAIL_BODY_HTML  = """..."""
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

Lần đầu chạy, trình duyệt sẽ mở để xác thực Google → Đăng nhập Gmail → Cho phép quyền.
Token sẽ được lưu vào `token.pickle` để dùng lại.

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
| `REJECTED_LABEL` | `rejected` | Tên label cần quét |
| `REPLIED_LABEL` | `replied` | Tên label sau khi gửi |

---

## 🛡️ Bảo mật

- **Không commit** file `.env` và `credentials.json` lên git
- Thêm vào `.gitignore`:
  ```
  .env
  credentials.json
  token.pickle
  *.log
  ```
- Chỉ những User ID trong `ALLOWED_USER_IDS` mới dùng được bot

---

## 📊 Giới hạn Gmail API

| Loại tài khoản | Giới hạn gửi/ngày |
|---------------|------------------|
| Gmail cá nhân | ~500 email |
| Google Workspace | ~2,000 email |

Bot đã có delay 1.5s/email để tránh bị rate limit.

---

## 🐛 Lỗi thường gặp

**`credentials.json not found`**
→ Chưa đặt file credentials.json vào thư mục

**`Label 'rejected' không tìm thấy`**
→ Chưa tạo label trong Gmail hoặc tên label sai

**`Unauthorized`** trong Telegram
→ User ID của bạn chưa có trong `ALLOWED_USER_IDS`
