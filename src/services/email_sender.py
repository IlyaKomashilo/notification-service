from email.message import EmailMessage

import aiosmtplib


class EmailSender:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self.host = host
        self.port = port
        self.sender = sender

    async def send(self, recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=self.host,
            port=self.port,
            timeout=10,
            use_tls=False,
            start_tls=False,
        )
