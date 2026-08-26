from __future__ import annotations

import logging

from app.core.config import Settings
from app.services.email_service import EmailDeliveryError, EmailService, OutboundEmail

logger = logging.getLogger(__name__)


class ShareNotificationService:
    """Tell someone a file has been shared with them.

    Until this existed there was no notification of any kind: a recipient learned about a
    share only by opening the file list and noticing something new, which for a file shared
    once and never mentioned means never.

    **The filename is deliberately not in the message.** The platform's own threat model
    accepts that the server holds filenames, but an email leaves that boundary entirely --
    it sits in a third-party mailbox, gets indexed, and is forwarded. Saying who shared
    something is enough for the recipient to know to go and look; saying what it was called
    would move metadata somewhere the design never accounted for.
    """

    def __init__(self, *, settings: Settings, email: EmailService | None = None) -> None:
        self.settings = settings
        self.email = email or EmailService(settings=settings)

    def notify_shared(self, *, recipient_email: str, recipient_username: str, sender_username: str) -> bool:
        """Best effort, by design.

        Called after the share has already committed. A share that succeeded must not be
        reported as failed because a mail server was unreachable, so delivery problems are
        logged and swallowed -- the file is shared either way, and the recipient will still
        find it in their list.
        """
        if not self.settings.SHARE_NOTIFICATION_EMAIL:
            return False

        try:
            self.email.send(self._compose(recipient_email, recipient_username, sender_username))
            return True
        except EmailDeliveryError:
            logger.warning("Share notification could not be delivered", exc_info=False)
            return False
        except Exception:  # pragma: no cover - defensive: never fail a committed share
            logger.exception("Unexpected failure sending a share notification")
            return False

    def _compose(self, email: str, recipient: str, sender: str) -> OutboundEmail:
        where = self.settings.APP_PUBLIC_URL.rstrip("/")
        link_line = f"\n\nOpen your files: {where}/files" if where else ""
        html_link = (
            f'<p><a href="{where}/files">Open your files</a></p>' if where else ""
        )

        text_body = (
            f"Hello {recipient},\n\n"
            f"{sender} has shared an encrypted file with you on SecureView.\n\n"
            "You will find it under \"Shared with me\" in your file list. Opening it uses "
            "your own encryption passphrase -- never the sender's."
            f"{link_line}\n\n"
            "If you were not expecting this, you can ignore it; nothing has been added to "
            "your account that you have to act on.\n"
        )
        html_body = (
            f"<p>Hello {recipient},</p>"
            f"<p><strong>{sender}</strong> has shared an encrypted file with you on "
            "SecureView.</p>"
            '<p>You will find it under &quot;Shared with me&quot; in your file list. Opening '
            "it uses your own encryption passphrase &mdash; never the sender&rsquo;s.</p>"
            f"{html_link}"
            "<p>If you were not expecting this, you can ignore it; nothing has been added to "
            "your account that you have to act on.</p>"
        )
        return OutboundEmail(
            to_address=email,
            subject=f"{sender} shared a file with you",
            text_body=text_body,
            html_body=html_body,
        )
