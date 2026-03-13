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

    # Đường dẫn file credentials OAuth2 tải từ Google Cloud Console
    CREDENTIALS_FILE: str = os.getenv("CREDENTIALS_FILE", "credentials.json")
    TOKEN_FILE: str = "token.pickle"

    # ─────────────────────────────────────────────
    # 🏷️ CẤU HÌNH LABEL GMAIL
    # ─────────────────────────────────────────────
    REJECTED_LABEL: str = "rejected"   # Label bot sẽ quét
    REPLIED_LABEL: str = "replied"     # Label đánh dấu đã xử lý

    # ─────────────────────────────────────────────
    # ⚙️ CẤU HÌNH GỬI EMAIL
    # ─────────────────────────────────────────────
    REPLY_SUBJECT_PREFIX: str = "Re: "
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
    EMAIL_BODY_PLAIN: str = """Kính gửi {name},

Cảm ơn bạn đã quan tâm và ứng tuyển vào vị trí tại {company}.

Sau khi xem xét hồ sơ của bạn, chúng tôi rất tiếc phải thông báo rằng hồ sơ của bạn chưa phù hợp với yêu cầu của vị trí tuyển dụng hiện tại.

Chúng tôi trân trọng sự quan tâm của bạn và mong rằng bạn sẽ tiếp tục theo dõi các cơ hội việc làm khác từ {company} trong tương lai.

Chúc bạn thành công trong sự nghiệp!

Trân trọng,
{sender_name}
{company}
"""

    # Nội dung HTML (được render đẹp hơn trong Gmail)
    EMAIL_BODY_HTML: str = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Kính gửi <strong>{name}</strong>,</p>

  <p>Cảm ơn bạn đã quan tâm và ứng tuyển vào vị trí tại <strong>{company}</strong>.</p>

  <p>Sau khi xem xét hồ sơ của bạn, chúng tôi rất tiếc phải thông báo rằng hồ sơ của bạn <strong>chưa phù hợp</strong> với yêu cầu của vị trí tuyển dụng hiện tại.</p>

  <p>Chúng tôi trân trọng sự quan tâm của bạn và mong rằng bạn sẽ tiếp tục theo dõi các cơ hội việc làm khác từ <strong>{company}</strong> trong tương lai.</p>

  <p>Chúc bạn thành công trong sự nghiệp!</p>

  <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
  <p style="color: #666; font-size: 14px;">
    Trân trọng,<br>
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
