"""Alerts: status of Telegram / e-mail channels and a test message."""

from __future__ import annotations

import streamlit as st

from services.alerts import Alert, email_configured, send_email, send_telegram, telegram_configured

st.set_page_config(page_title="Alerts", page_icon="🔔", layout="wide")
st.title("🔔 Alerts")
st.caption(
    "Alerts tell you when a watched symbol's strategy signal changes or its drawdown passes a "
    "limit. Run `python scripts/run_alerts.py` from cron to send them on a schedule. Analysis "
    "only; nothing here trades."
)

tg, em = telegram_configured(), email_configured()
c1, c2 = st.columns(2)
with c1:
    st.metric("Telegram", "configured" if tg else "not configured")
with c2:
    st.metric("E-mail", "configured" if em else "not configured")
st.markdown(
    "Set secrets as environment variables or in `.env` (never in code): `TELEGRAM_BOT_TOKEN`, "
    "`TELEGRAM_CHAT_ID`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, "
    "`ALERT_EMAIL_TO`, plus `ALERT_SYMBOLS`, `ALERT_STRATEGY`, `ALERT_DRAWDOWN` for the script. "
    "Values are never displayed."
)

if st.button("Send a test alert", disabled=not (tg or em)):
    test = Alert("test", "Test alert", "Alerts are working.")
    for name, ok, sender in (("Telegram", tg, send_telegram), ("E-mail", em, send_email)):
        if not ok:
            continue
        try:
            sender(test)
            st.success(f"{name}: sent.")
        except RuntimeError as exc:
            st.error(str(exc))
