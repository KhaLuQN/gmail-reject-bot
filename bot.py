"""
Gmail Reject Auto-Reply Bot
Telegram Bot + IMAP/SMTP integration
"""

import logging
import asyncio
import gc  # Garbage collection để giảm memory
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from imap_smtp_service import EmailService
from config import Config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,  # Giảm log level để tiết kiệm memory
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Lưu trạng thái pending confirm per user
pending_jobs: dict = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start"""
    text = (
        "🤖 *Gmail Reject Auto-Reply Bot*\n\n"
        "Các lệnh có sẵn:\n"
        "• /scan — Quét email bị nhãn `rejected`\n"
        "• /status — Xem trạng thái hiện tại\n"
        "• /help — Hướng dẫn sử dụng\n\n"
        "Bắt đầu bằng lệnh /scan nhé!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /help"""
    text = (
        "📖 *Hướng dẫn sử dụng*\n\n"
        "1️⃣ Đảm bảo Gmail đã có label `rejected`\n"
        "2️⃣ Gõ /scan để bot quét các email cần reply\n"
        "3️⃣ Bot sẽ liệt kê danh sách và hỏi xác nhận\n"
        "4️⃣ Bấm *✅ Xác nhận gửi* để gửi hàng loạt\n"
        "5️⃣ Bot báo kết quả sau khi hoàn tất\n\n"
        "⚙️ *Cấu hình template:* Chỉnh file `config.py`\n"
        "🏷️ *Label Gmail:* `rejected` → sau khi gửi → `replied`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /scan - quét email bị label rejected"""
    user_id = update.effective_user.id

    # Kiểm tra quyền
    if user_id not in Config.ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng bot này.")
        return

    msg = await update.message.reply_text("🔍 Đang quét Gmail... vui lòng đợi")

    try:
        email_service = EmailService()
        emails = email_service.get_rejected_emails()

        if not emails:
            await msg.edit_text(
                "✅ Không tìm thấy email nào có label `rejected`.\n"
                "Tất cả đã được xử lý rồi!",
                parse_mode="Markdown"
            )
            return

        # Lưu job vào pending
        pending_jobs[user_id] = {
            "emails": emails,
            "email_service": email_service
        }

        # Hiển thị preview
        preview_lines = []
        for i, email in enumerate(emails[:10], 1):  # Hiện tối đa 10
            preview_lines.append(
                f"{i}. 📧 `{email['from_email']}`\n"
                f"   📌 {email['subject'][:50]}{'...' if len(email['subject']) > 50 else ''}"
            )

        more_text = f"\n_...và {len(emails) - 10} email khác_" if len(emails) > 10 else ""

        text = (
            f"📊 *Tìm thấy {len(emails)} email cần reply*\n\n"
            + "\n".join(preview_lines)
            + more_text
            + "\n\n"
            "Bạn có muốn gửi email từ chối đến tất cả không?"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Xác nhận gửi", callback_data=f"confirm_send_{user_id}"),
                InlineKeyboardButton("❌ Huỷ", callback_data=f"cancel_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)

        # Giải phóng memory sau khi scan xong
        gc.collect()

    except Exception as e:
        logger.error(f"Scan error: {e}")
        await msg.edit_text(f"❌ Lỗi khi quét Gmail:\n`{str(e)}`", parse_mode="Markdown")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý nút bấm inline keyboard"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data == f"cancel_{user_id}":
        pending_jobs.pop(user_id, None)
        await query.edit_message_text("❌ Đã huỷ. Không có email nào được gửi.")
        return

    if data == f"confirm_send_{user_id}":
        job = pending_jobs.get(user_id)
        if not job:
            await query.edit_message_text("⚠️ Phiên đã hết hạn. Vui lòng /scan lại.")
            return

        emails = job["emails"]
        email_service = job["email_service"]
        total = len(emails)

        await query.edit_message_text(
            f"📤 Đang gửi {total} email... vui lòng đợi\n"
            f"(Có thể mất vài phút)"
        )

        # Gửi email và thu thập kết quả
        success_list = []
        failed_list = []

        for i, email in enumerate(emails, 1):
            try:
                # Cập nhật tiến độ mỗi 5 email
                if i % 5 == 0 or i == 1:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"⏳ Đang xử lý: {i}/{total}..."
                    )

                email_service.send_rejection_reply(email)
                success_list.append(email["from_email"])
                logger.info(f"✅ Sent to {email['from_email']}")

                # Delay để tránh rate limit
                await asyncio.sleep(Config.SEND_DELAY_SECONDS)

            except Exception as e:
                failed_list.append({
                    "email": email["from_email"],
                    "error": str(e)
                })
                logger.error(f"❌ Failed {email['from_email']}: {e}")

        # Xoá pending job
        pending_jobs.pop(user_id, None)

        # Giải phóng memory
        gc.collect()

        # Tạo báo cáo kết quả
        report = _build_report(total, success_list, failed_list)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=report,
            parse_mode="Markdown"
        )


def _build_report(total: int, success_list: list, failed_list: list) -> str:
    """Tạo báo cáo tổng kết"""
    lines = [
        "📋 *BÁO CÁO KẾT QUẢ*\n",
        f"📊 Tổng: {total} email",
        f"✅ Thành công: {len(success_list)}",
        f"❌ Thất bại: {len(failed_list)}\n",
    ]

    if failed_list:
        lines.append("⚠️ *Các email gửi lỗi:*")
        for item in failed_list[:20]:  # Tối đa 20 dòng
            lines.append(f"• `{item['email']}`\n  _{item['error'][:80]}_")

    if len(success_list) == total:
        lines.append("\n🎉 Tất cả email đã được gửi thành công!")
    elif len(success_list) == 0:
        lines.append("\n💔 Không có email nào được gửi thành công.")
    else:
        lines.append(f"\n✅ Đã gửi thành công {len(success_list)}/{total} email.")

    return "\n".join(lines)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /status"""
    user_id = update.effective_user.id
    job = pending_jobs.get(user_id)

    if job:
        count = len(job["emails"])
        await update.message.reply_text(
            f"⏳ Đang có job pending với {count} email chờ xác nhận.\n"
            "Dùng /scan để xem lại hoặc xác nhận gửi."
        )
    else:
        await update.message.reply_text("✅ Không có job nào đang chờ xử lý.")


def main():
    """Khởi chạy bot"""
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot đang chạy...")
    # Chỉ nhận các update cần thiết để giảm memory
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
