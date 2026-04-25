import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL

def post_digest(report, trend, sheet_url, om_base_url, ai_summary):
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN is not set.")
    
    client = WebClient(token=SLACK_BOT_TOKEN)
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛡️ Weekly Data Quality Report",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Total Failures:* {report.total_failures} | *P1 Critical:* {report.p1_count} | *P2 High:* {report.p2_count} | *P3 Low:* {report.p3_count}\n*Most Impacted Domain:* {report.most_impacted_domain or 'N/A'}"
            }
        }
    ]
    
    if ai_summary:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🤖 AI Executive Summary:*\n>{ai_summary}"
            }
        })
        
    if sheet_url != "#":
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📊 <{sheet_url}|View the full Google Sheets Report>"
            }
        })

    try:
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL,
            blocks=blocks,
            text="Your Weekly Data Quality Report is here!"
        )
        return response
    except SlackApiError as e:
        raise Exception(f"Slack API Error: {e.response['error']}")
