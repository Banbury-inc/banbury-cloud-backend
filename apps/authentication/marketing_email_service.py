"""
Marketing email service for sending branded marketing emails from banbury@banbury.io
via Gmail SMTP using an App Password.
"""
import os
import html
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Optional

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
LOGO_CID = "banbury-logo"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "banbury_logo.png")
UNSUBSCRIBE_URL = "https://www.banbury.io/workspaces?openSettings=true&settingsTab=notifications"
COMPANY_ADDRESS = "New York, New York"


class MarketingEmailService:
    """Sends branded marketing emails via Gmail SMTP."""

    def __init__(self):
        self.from_email = os.getenv("GMAIL_MARKETING_EMAIL", "banbury@banbury.io")
        self.from_name = os.getenv("GMAIL_MARKETING_FROM_NAME", "Banbury")
        self.app_password = os.getenv("GMAIL_MARKETING_APP_PASSWORD")

        if not self.app_password:
            logger.warning(
                "GMAIL_MARKETING_APP_PASSWORD environment variable not set. "
                "Marketing email functionality will be disabled."
            )

    @property
    def is_configured(self) -> bool:
        return bool(self.app_password)

    def _load_logo_bytes(self) -> Optional[bytes]:
        try:
            with open(LOGO_PATH, "rb") as f:
                return f.read()
        except OSError:
            logger.warning("Banbury logo not found at %s; sending without inline logo.", LOGO_PATH)
            return None

    def _build_html(self, subject: str, body: str, include_logo: bool) -> str:
        """Render the branded HTML email template."""
        paragraphs = "".join(
            f'<p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: #333333;">{html.escape(line)}</p>'
            for line in body.split("\n")
            if line.strip()
        )

        logo_html = (
            f'<img src="cid:{LOGO_CID}" alt="Banbury" width="48" height="48" '
            'style="display: block; border: 0; border-radius: 10px;" />'
            if include_logo
            else '<span style="font-size: 24px; font-weight: 700; color: #111111;">Banbury</span>'
        )

        footer_logo_html = (
            f'<img src="cid:{LOGO_CID}" alt="Banbury" width="40" height="40" '
            'style="display: block; border: 0; opacity: 0.55;" />'
            if include_logo
            else '<span style="font-size: 16px; font-weight: 700; color: #8a8f98;">Banbury</span>'
        )

        footer_link_style = "color: #8a8f98; text-decoration: underline;"
        current_year = datetime.now().year

        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f5f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f5f7; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%;">
          <tr>
            <td style="padding: 0 8px 20px 8px;" align="center">
              {logo_html}
            </td>
          </tr>
          <tr>
            <td style="background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);">
              <h1 style="margin: 0 0 24px 0; font-size: 22px; line-height: 1.3; color: #111111; font-weight: 700;">{html.escape(subject)}</h1>
              {paragraphs}
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top: 28px;">
                <tr>
                  <td style="border-radius: 8px; background-color: #111111;">
                    <a href="https://www.banbury.io" style="display: inline-block; padding: 12px 24px; font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none;">Open Banbury</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding: 32px 8px 0 8px;" align="left">
              {footer_logo_html}
              <p style="margin: 20px 0 0 0; font-size: 14px; line-height: 1.6; color: #8a8f98;">
                <a href="https://www.banbury.io" style="{footer_link_style}">Home</a>
                &nbsp;&middot;&nbsp;
                <a href="https://banbury.io/docs" style="{footer_link_style}">Docs</a>
                &nbsp;&middot;&nbsp;
                <a href="https://www.banbury.io/workspaces" style="{footer_link_style}">Open Web App</a>
              </p>
              <p style="margin: 18px 0 0 0; font-size: 14px; line-height: 1.6; color: #8a8f98;">
                &copy; {current_year} Banbury<br />
                {COMPANY_ADDRESS}
              </p>
              <p style="margin: 18px 0 0 0; font-size: 14px; line-height: 1.6; color: #8a8f98;">
                <a href="{UNSUBSCRIBE_URL}" style="{footer_link_style}">Unsubscribe</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    def _build_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        logo_bytes: Optional[bytes],
    ) -> MIMEMultipart:
        message = MIMEMultipart("related")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email

        alternative = MIMEMultipart("alternative")
        message.attach(alternative)

        plain_text = (
            f"{body}\n\n"
            "---\n"
            "You're receiving this email because you have a Banbury account.\n"
            f"Banbury, {COMPANY_ADDRESS}\n"
            f"Unsubscribe: {UNSUBSCRIBE_URL}"
        )
        alternative.attach(MIMEText(plain_text, "plain", "utf-8"))
        alternative.attach(MIMEText(self._build_html(subject, body, include_logo=logo_bytes is not None), "html", "utf-8"))

        if logo_bytes:
            logo = MIMEImage(logo_bytes, _subtype="png")
            logo.add_header("Content-ID", f"<{LOGO_CID}>")
            logo.add_header("Content-Disposition", "inline", filename="banbury_logo.png")
            message.attach(logo)

        return message

    def send_bulk(self, recipients: list, subject: str, body: str) -> dict:
        """
        Send an individual marketing email to each recipient over a single SMTP connection.

        Args:
            recipients: list of dicts with "user_id" and "email" keys
            subject: email subject line
            body: plain-text message body (newlines become paragraphs)

        Returns:
            dict with "sent" (list of user_ids) and "failed" (list of {user_id, error}) keys
        """
        if not self.is_configured:
            return {
                "sent": [],
                "failed": [
                    {"user_id": r["user_id"], "error": "Email service not configured"}
                    for r in recipients
                ],
            }

        logo_bytes = self._load_logo_bytes()
        sent = []
        failed = []

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.from_email, self.app_password)

                for recipient in recipients:
                    try:
                        message = self._build_message(recipient["email"], subject, body, logo_bytes)
                        smtp.sendmail(self.from_email, [recipient["email"]], message.as_string())
                        sent.append(recipient["user_id"])
                    except smtplib.SMTPException as e:
                        logger.error("Failed to send marketing email to %s: %s", recipient["email"], e)
                        failed.append({"user_id": recipient["user_id"], "error": str(e)})
        except (smtplib.SMTPException, OSError) as e:
            logger.error("SMTP connection error while sending marketing emails: %s", e)
            already_processed = {r for r in sent} | {f["user_id"] for f in failed}
            for recipient in recipients:
                if recipient["user_id"] not in already_processed:
                    failed.append({"user_id": recipient["user_id"], "error": f"SMTP connection error: {e}"})

        return {"sent": sent, "failed": failed}


marketing_email_service = MarketingEmailService()
