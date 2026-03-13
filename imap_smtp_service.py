"""
IMAP/SMTP Service - Xử lý email qua IMAP và SMTP
Thay thế Gmail API với App Password
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import logging
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.imap_client = None
        self.smtp_client = None
        self._connect_imap()
        self._connect_smtp()

    def _connect_imap(self):
        """Kết nối IMAP"""
        try:
            self.imap_client = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT)
            self.imap_client.login(Config.IMAP_USERNAME, Config.IMAP_PASSWORD)
            self.imap_client.select("INBOX")
            logger.info("✅ Connected to IMAP")
        except Exception as e:
            logger.error(f"❌ IMAP connection failed: {e}")
            raise

    def _connect_smtp(self):
        """Kết nối SMTP"""
        try:
            self.smtp_client = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT)
            self.smtp_client.starttls()
            self.smtp_client.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            logger.info("✅ Connected to SMTP")
        except Exception as e:
            logger.error(f"❌ SMTP connection failed: {e}")
            raise

    def _ensure_labels_exist(self):
        """
        Đảm bảo các label cần thiết tồn tại
        Gmail sử dụng IMAP folders như labels
        """
        try:
            # Lấy danh sách folders
            status, folders = self.imap_client.list()

            existing_folders = []
            for folder in folders:
                # Parse folder name
                parts = folder.decode().split('"')
                if len(parts) >= 4:
                    folder_name = parts[3]
                    existing_folders.append(folder_name)

            logger.info(f"Existing folders: {existing_folders}")

            # Tạo folder nếu chưa tồn tại
            for label_name in [Config.REJECTED_LABEL, Config.REPLIED_LABEL]:
                if label_name not in existing_folders:
                    try:
                        self.imap_client.create(label_name)
                        logger.info(f"✅ Created folder: {label_name}")
                    except Exception as e:
                        # Folder có thể đã tồn tại
                        logger.warning(f"⚠️ Folder {label_name} may already exist: {e}")

        except Exception as e:
            logger.error(f"❌ Error checking folders: {e}")

    def get_rejected_emails(self) -> List[Dict]:
        """
        Quét email có label 'rejected' nhưng chưa có label 'replied'
        Returns: list of email dicts
        """
        try:
            # Kết nối lại nếu cần
            if not self.imap_client:
                self._connect_imap()

            # Tìm email trong folder rejected
            self.imap_client.select(Config.REJECTED_LABEL)

            # Tìm tất cả email
            status, messages = self.imap_client.search(None, "ALL")

            if status != "OK":
                logger.error(f"❌ Search failed: {status}")
                return []

            email_ids = messages[0].split()
            emails = []

            for email_id in email_ids[:Config.MAX_EMAILS_PER_SCAN]:
                try:
                    email_data = self._parse_email(email_id)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"❌ Error parsing email {email_id}: {e}")

            logger.info(f"✅ Found {len(emails)} emails to process")
            return emails

        except Exception as e:
            logger.error(f"❌ Error getting rejected emails: {e}")
            # Nếu folder không tồn tại, trả về empty list
            return []

    def _parse_email(self, email_id: bytes) -> Optional[Dict]:
        """Parse thông tin email từ email ID"""
        try:
            # Fetch email
            status, msg_data = self.imap_client.fetch(email_id, "(RFC822)")

            if status != "OK":
                return None

            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract headers
            from_raw = email_message.get("From", "")
            from_email = self._extract_email(from_raw)
            from_name = self._extract_name(from_raw)

            if not from_email:
                return None

            return {
                "message_id": email_id.decode(),
                "from_email": from_email,
                "from_name": from_name,
                "from_raw": from_raw,
                "subject": email_message.get("Subject", "(Không có tiêu đề)"),
                "original_message_id": email_message.get("Message-ID", ""),
                "date": email_message.get("Date", ""),
            }

        except Exception as e:
            logger.error(f"❌ Error parsing email: {e}")
            return None

    def _extract_email(self, from_header: str) -> str:
        """Trích xuất địa chỉ email từ header From"""
        import re
        match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", from_header)
        return match.group(0) if match else ""

    def _extract_name(self, from_header: str) -> str:
        """Trích xuất tên người gửi từ header From"""
        if "<" in from_header:
            name_part = from_header.split("<")[0].strip().strip('"')
            if name_part:
                # Decode encoded header nếu có
                try:
                    decoded = decode_header(name_part)
                    name = ""
                    for part, encoding in decoded:
                        if isinstance(part, bytes):
                            name += part.decode(encoding or "utf-8")
                        else:
                            name += part
                    return name.strip()
                except Exception:
                    return name_part

        # Nếu không có tên, lấy username từ email (phần trước @)
        email = self._extract_email(from_header)
        if email and "@" in email:
            return email.split("@")[0]

        return ""

    def send_rejection_reply(self, email: Dict):
        """
        Gửi email từ chối reply đến người gửi
        Sau đó cập nhật folder: chuyển từ rejected sang replied
        """
        try:
            # Tạo nội dung email
            body = Config.build_rejection_body(
                recipient_name=email.get("from_name", ""),
                recipient_email=email["from_email"],
                original_subject=email["subject"]
            )

            # Tạo MIME message
            message = MIMEMultipart("alternative")
            message["To"] = email["from_raw"] or email["from_email"]
            message["Subject"] = Config.REPLY_SUBJECT_PREFIX + email["subject"]
            message["In-Reply-To"] = email.get("original_message_id", "")
            message["References"] = email.get("original_message_id", "")

            # Thêm nội dung plain text và HTML
            part_text = MIMEText(body["plain"], "plain", "utf-8")
            part_html = MIMEText(body["html"], "html", "utf-8")
            message.attach(part_text)
            message.attach(part_html)

            # Gửi qua SMTP
            self.smtp_client.send_message(message)
            logger.info(f"✅ Sent email to {email['from_email']}")

            # Cập nhật folder: chuyển từ rejected sang replied
            self._update_folder_after_reply(email["message_id"])

        except Exception as e:
            logger.error(f"❌ Error sending email to {email['from_email']}: {e}")
            raise

    def _update_folder_after_reply(self, message_id: str):
        """Chuyển email từ folder rejected sang replied"""
        try:
            # Copy sang folder replied
            self.imap_client.copy(message_id, Config.REPLIED_LABEL)

            # Xóa khỏi folder rejected
            self.imap_client.store(message_id, "+FLAGS", "\\Deleted")
            self.imap_client.expunge()

            logger.info(f"✅ Moved email {message_id} from {Config.REJECTED_LABEL} to {Config.REPLIED_LABEL}")

        except Exception as e:
            logger.error(f"❌ Error moving email: {e}")

    def close(self):
        """Đóng kết nối"""
        try:
            if self.imap_client:
                self.imap_client.close()
                self.imap_client.logout()
        except Exception as e:
            logger.error(f"❌ Error closing IMAP: {e}")

        try:
            if self.smtp_client:
                self.smtp_client.quit()
        except Exception as e:
            logger.error(f"❌ Error closing SMTP: {e}")