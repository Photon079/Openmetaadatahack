import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import GOOGLE_SERVICE_ACCOUNT_JSON, SHEET_ID

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def write_report(report, trend, ai_summary):
    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
        raise FileNotFoundError(f"GCP Service Account JSON not found at {GOOGLE_SERVICE_ACCOUNT_JSON}")
    if not SHEET_ID:
        raise ValueError("SHEET_ID is not set.")
        
    creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    
    # Get the actual sheet ID of the first tab
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    first_sheet_name = spreadsheet['sheets'][0]['properties']['title']
    sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
    
    # Clear the sheet first
    service.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID, range=f"{first_sheet_name}!A1:Z1000", body={}
    ).execute()
    
    # Prepare Data
    values = [
        ["DQ-Agent Weekly Report", "", "", "", "", "", ""],
        ["Total Failures", str(report.total_failures), "P1 Critical", str(report.p1_count), "", "", ""],
        ["Most Impacted Domain", report.most_impacted_domain or "N/A", "P2 High", str(report.p2_count), "", "", ""],
        ["", "", "P3 Low", str(report.p3_count), "", "", ""],
        ["", "", "", "", "", "", ""],
        ["AI Executive Summary", "", "", "", "", "", ""],
        [ai_summary, "", "", "", "", "", ""],
        ["", "", "", "", "", "", ""],
        ["Table FQN", "Test Case", "Severity", "Failure Count", "Tags", "Owner", "Domain"]
    ]
    
    for inc in report.incidents:
        values.append([
            inc.table_fqn,
            inc.test_case_name,
            inc.severity,
            inc.failure_count,
            ", ".join(inc.tags) if inc.tags else "None",
            inc.owner or "Unknown",
            inc.domain or "Unknown"
        ])
        
    # Write Values
    body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=f"{first_sheet_name}!A1",
        valueInputOption="USER_ENTERED", body=body
    ).execute()
    
    # Format with batchUpdate
    requests = [
        # Bold and color the Main Header
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.8},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 14}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        # Bold Data Headers
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 8, "endRowIndex": 9, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        "textFormat": {"bold": True, "fontSize": 11}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        # AI Summary background
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.1, "green": 0.6, "blue": 0.3},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        # Auto-resize columns
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 7
                }
            }
        }
    ]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID, body={"requests": requests}
    ).execute()
    
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
