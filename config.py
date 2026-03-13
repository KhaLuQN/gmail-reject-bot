"""
Cấu hình Bot - Chỉnh sửa file này theo nhu cầu của bạn
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ─────────────────────────────────────────────
    # 🔑 THÔNG TIN XÁC THỰC (đặt trong file .env)
    # ─────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Danh sách Telegram User ID được phép dùng bot
    # Lấy ID của bạn bằng cách nhắn @userinfobot trên Telegram
    ALLOWED_USER_IDS: list[int] = [
        int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()
    ]

    # ─────────────────────────────────────────────
    # 📧 SMTP/IMAP CONFIGURATION (App Password)
    # ─────────────────────────────────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USERNAME: str = os.getenv("IMAP_USERNAME", "")
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "")

    # ─────────────────────────────────────────────
    # 🏷️ CẤU HÌNH LABEL GMAIL
    # ─────────────────────────────────────────────
    REJECTED_LABEL: str = "rejected"   # Label bot sẽ quét
    REPLIED_LABEL: str = "replied"     # Label đánh dấu đã xử lý

    # ─────────────────────────────────────────────
    # ⚙️ CẤU HÌNH GỬI EMAIL
    # ─────────────────────────────────────────────
    REPLY_SUBJECT_PREFIX: str = "Application Update – Leadsmax Group"
    MAX_EMAILS_PER_SCAN: int = 200     # Tối đa email quét mỗi lần
    SEND_DELAY_SECONDS: float = 1.5    # Delay giữa các email (tránh rate limit)

    # ─────────────────────────────────────────────
    # 📧 TEMPLATE EMAIL TỪ CHỐI
    # Chỉnh nội dung tại đây theo nhu cầu của bạn
    # Có thể dùng các biến:
    #   {name}    - Tên người nhận (nếu có)
    #   {email}   - Địa chỉ email người nhận
    #   {subject} - Tiêu đề email gốc
    # ─────────────────────────────────────────────

    SENDER_NAME: str = os.getenv("SENDER_NAME", "Phòng Nhân Sự")
    SENDER_COMPANY: str = os.getenv("SENDER_COMPANY", "Công ty ABC")

    # Nội dung Plain Text
    EMAIL_BODY_PLAIN: str = """Dear {name},

Thank you for your interest in the position at {company} and for taking the time to submit your application.

After reviewing your CV, we regret to inform you that we will not be moving forward with your application at this time, as we have decided to proceed with other candidates whose qualifications more closely match our current requirements.

We truly appreciate your interest in joining our team and wish you every success in your future career.

Best regards,
{sender_name}
{company}
"""

    # Nội dung HTML (được render đẹp hơn trong Gmail)
    EMAIL_BODY_HTML: str = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Dear <strong>{name}</strong>,</p>

  <p>Thank you for your interest in the position at <strong>{company}</strong> and for taking the time to submit your application.</p>

  <p>After reviewing your CV, we regret to inform you that we will not be moving forward with your application at this time, as we have decided to proceed with other candidates whose qualifications more closely match our current requirements.</p>

  <p>We truly appreciate your interest in joining our team and wish you every success in your future career.</p>

  <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
  <p style="color: #666; font-size: 14px;">
    Best regards,<br>
    <strong>{sender_name}</strong><br>
    {company}
  </p>
</body>
</html>"""

    @classmethod
    def build_rejection_body(
        cls,
        recipient_name: str,
        recipient_email: str,
        original_subject: str
    ) -> dict:
        """
        Build nội dung email từ chối với các biến được thay thế
        Returns: {"plain": str, "html": str}
        """
        # Dùng tên nếu có, không thì dùng email
        display_name = recipient_name if recipient_name else recipient_email

        vars_map = {
            "name": display_name,
            "email": recipient_email,
            "subject": original_subject,
            "company": cls.SENDER_COMPANY,
            "sender_name": cls.SENDER_NAME,
        }

        return {
            "plain": cls.EMAIL_BODY_PLAIN.format(**vars_map),
            "html": cls.EMAIL_BODY_HTML.format(**vars_map),
        }
