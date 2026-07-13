"""Render the brief as a styled HTML email and send it via SMTP.

All config comes from environment variables, so nothing sensitive is ever
stored in the code or the repo:

    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD   -- your email provider
    EMAIL_TO                                          -- where the brief goes (you)
    EMAIL_FROM                                        -- optional; defaults to SMTP_USER

If SMTP_HOST or EMAIL_TO is missing, delivery is skipped with a message — so a
plain `python run.py` on your laptop still works without sending anything.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

import markdown as md

# Email-safe styling. Kept in a <style> block plus sensible defaults; renders
# cleanly in Gmail, Apple Mail, and Outlook web.
_HEAD = """\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { margin: 0; background: #f4f5f7; }
  .wrap { max-width: 640px; margin: 0 auto; padding: 24px 16px; }
  .card { background: #ffffff; border-radius: 12px; overflow: hidden;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          color: #1a1a1a; line-height: 1.55; }
  .bar { background: #14213d; color: #ffffff; padding: 20px 28px; }
  .bar .kicker { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
                 color: #9fb3d1; margin: 0 0 4px; }
  .bar h1 { font-size: 20px; margin: 0; font-weight: 600; }
  .body { padding: 8px 28px 28px; }
  .body h1 { display: none; }            /* the markdown H1 duplicates the bar title */
  .body h2 { font-size: 16px; margin: 26px 0 8px; padding-bottom: 6px;
             border-bottom: 1px solid #ececec; color: #14213d; }
  .body h3 { font-size: 14px; margin: 16px 0 6px; color: #333; }
  .body p, .body li { font-size: 14px; }
  .body ul { padding-left: 20px; margin: 8px 0; }
  .body li { margin: 6px 0; }
  .body a { color: #1d4ed8; text-decoration: none; }
  .body a:hover { text-decoration: underline; }
  .body strong { color: #14213d; }
  .footer { padding: 16px 28px; font-size: 12px; color: #8a8a8a;
            border-top: 1px solid #ececec; }
</style>
</head>
<body>
<div class="wrap"><div class="card">
"""

_FOOTER = """\
<div class="footer">Generated automatically by the Adtech Market Intelligence Agent.</div>
</div></div>
</body>
</html>
"""


def _render_html(brief_md: str, date_str: str) -> str:
    body_html = md.markdown(brief_md, extensions=["extra", "sane_lists"])
    bar = (
        '<div class="bar"><p class="kicker">Adtech Market Intelligence</p>'
        f'<h1>Weekly Brief &middot; {date_str}</h1></div>'
    )
    # f-string assembly is safe: the CSS braces live in _HEAD (never .format-ed),
    # and body_html is interpolated as a value, not re-parsed.
    return f'{_HEAD}{bar}<div class="body">{body_html}</div>{_FOOTER}'


def deliver(brief_md: str, subject: str, date_str: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    to_addr = os.environ.get("EMAIL_TO")
    if not host or not to_addr:
        print("Email not configured (SMTP_HOST / EMAIL_TO missing) — skipping delivery.")
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("EMAIL_FROM", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(brief_md)  # plain-text fallback for clients that block HTML
    msg.add_alternative(_render_html(brief_md, date_str), subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        if user and password:
            server.login(user, password)
        server.send_message(msg)
    print(f"Emailed brief to {to_addr}")
    return True
