"""
Gmail Service - Xử lý Gmail API
Quét email nhãn rejected, gửi reply, cập nhật nhãn
"""

import base64
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

from config import Config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


class GmailService:
    def __init__(self):
        self.service = self._authenticate()
        self._ensure_labels_exist()

    def _authenticate(self):
        """Xác thực OAuth2 với Gmail"""
        creds = None

        # Load token đã lưu
        if os.path.exists(Config.TOKEN_FILE):
            with open(Config.TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        # Refresh hoặc login mới
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Lưu token
            with open(Config.TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

        return build("gmail", "v1", credentials=creds)

    def _ensure_labels_exist(self):
        """Đảm bảo các label cần thiết tồn tại"""
        existing = self._get_all_labels()
        existing_names = {l["name"] for l in existing}

        for label_name in [Config.REJECTED_LABEL, Config.REPLIED_LABEL]:
            if label_name not in existing_names:
                self._create_label(label_name)
                logger.info(f"Đã tạo label: {label_name}")

    def _get_all_labels(self) -> list:
        """Lấy tất cả labels"""
        result = self.service.users().labels().list(userId="me").execute()
        return result.get("labels", [])

    def _create_label(self, name: str) -> dict:
        """Tạo label mới"""
        label_body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        return self.service.users().labels().create(
            userId="me", body=label_body
        ).execute()

    def _get_label_id(self, name: str) -> str | None:
        """Lấy ID của label theo tên"""
        labels = self._get_all_labels()
        for label in labels:
            if label["name"] == name:
                return label["id"]
        return None

    def get_rejected_emails(self) -> list[dict]:
        """
        Quét tất cả email có label 'rejected' nhưng chưa có label 'replied'
        Returns: list of email dicts
        """
        rejected_id = self._get_label_id(Config.REJECTED_LABEL)
        replied_id = self._get_label_id(Config.REPLIED_LABEL)

        if not rejected_id:
            raise ValueError(f"Không tìm thấy label '{Config.REJECTED_LABEL}' trong Gmail")

        # Query: có label rejected, KHÔNG có label replied
        query = f"label:{Config.REJECTED_LABEL}"
        if replied_id:
            query += f" -label:{Config.REPLIED_LABEL}"

        results = self.service.users().messages().list(
            userId="me",
            q=query,
            maxResults=Config.MAX_EMAILS_PER_SCAN
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg_ref in messages:
            try:
                email_data = self._parse_email(msg_ref["id"])
                if email_data:
                    emails.append(email_data)
            except Exception as e:
                logger.error(f"Lỗi parse email {msg_ref['id']}: {e}")

        logger.info(f"Tìm thấy {len(emails)} email cần xử lý")
        return emails

    def _parse_email(self, message_id: str) -> dict | None:
        """Parse thông tin email từ message ID"""
        msg = self.service.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "To", "Message-ID", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

        from_raw = headers.get("From", "")
        from_email = self._extract_email(from_raw)
        from_name = self._extract_name(from_raw)

        if not from_email:
            return None

        return {
            "message_id": message_id,
            "thread_id": msg.get("threadId"),
            "from_email": from_email,
            "from_name": from_name,
            "from_raw": from_raw,
            "subject": headers.get("Subject", "(Không có tiêu đề)"),
            "original_message_id": headers.get("Message-ID", ""),
            "date": headers.get("Date", ""),
            "label_ids": msg.get("labelIds", []),
        }

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
        return ""

    def send_rejection_reply(self, email: dict):
        """
        Gửi email từ chối reply đến người gửi
        Sau đó cập nhật nhãn: xoá rejected, thêm replied
        """
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

        # Encode và gửi
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_body = {
            "raw": raw,
            "threadId": email.get("thread_id")
        }

        self.service.users().messages().send(
            userId="me", body=send_body
        ).execute()

        # Cập nhật label
        self._update_labels_after_reply(email["message_id"])
        logger.info(f"✅ Đã gửi + cập nhật label cho: {email['from_email']}")

    def _update_labels_after_reply(self, message_id: str):
        """Xoá label rejected, thêm label replied"""
        rejected_id = self._get_label_id(Config.REJECTED_LABEL)
        replied_id = self._get_label_id(Config.REPLIED_LABEL)

        modify_body = {}
        if replied_id:
            modify_body["addLabelIds"] = [replied_id]
        if rejected_id:
            modify_body["removeLabelIds"] = [rejected_id]

        if modify_body:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body=modify_body
            ).execute()
