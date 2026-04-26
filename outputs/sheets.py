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
    
    # 1. Ensure Tabs Exist
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    existing_tabs = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet['sheets']}
    
    required_tabs = ["Executive Summary", "Incident List", "Triage by Owner"]
    new_tab_requests = []
    for tab in required_tabs:
        if tab not in existing_tabs:
            new_tab_requests.append({"addSheet": {"properties": {"title": tab}}})
    
    if new_tab_requests:
        service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": new_tab_requests}).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        existing_tabs = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet['sheets']}

    # 2. Clear All Required Tabs
    clear_ranges = [f"'{tab}'!A1:Z1000" for tab in required_tabs]
    service.spreadsheets().values().batchClear(spreadsheetId=SHEET_ID, body={"ranges": clear_ranges}).execute()

    # 3. Data Preparation
    summary_values = [
        ["DQ-Agent Autonomous Report Summary", "", "", ""],
        ["Status", "Operational" if report.p1_count == 0 else "Action Required", "Total Failures", str(report.total_failures)],
        ["P1 Critical", str(report.p1_count), "P2 High", str(report.p2_count)],
        ["P3 Low", str(report.p3_count), "Most Impacted Domain", report.most_impacted_domain or "N/A"],
        ["", "", "", ""],
        ["AI Executive Summary", "", "", ""],
        [ai_summary, "", "", ""],
    ]
    
    incident_values = [["Table FQN", "Test Case", "Severity", "Failure Count", "Tags", "Owner", "Domain", "OM Link"]]
    for inc in report.incidents:
        incident_values.append([inc.table_fqn, inc.test_case_name, inc.severity, inc.failure_count, ", ".join(inc.tags) if inc.tags else "None", inc.owner or "Unowned", inc.domain or "Unknown", inc.om_deep_link])

    owner_values = [["Owner", "Table", "Incident", "Severity", "Action"]]
    for owner, incs in report.by_owner.items():
        for inc in incs:
            owner_values.append([owner, inc.table_name, inc.test_case_name, inc.severity, "Investigate root cause"])

    # 4. Write Values
    write_data = [
        {"range": "'Executive Summary'!A1", "values": summary_values},
        {"range": "'Incident List'!A1", "values": incident_values},
        {"range": "'Triage by Owner'!A1", "values": owner_values},
    ]
    service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body={"valueInputOption": "USER_ENTERED", "data": write_data}).execute()

    # 5. Advanced Aesthetic Formatting
    format_requests = []
    
    # 5a. First, delete all existing banding and conditional formatting to avoid duplicates/errors
    for tab_name, tab_id in existing_tabs.items():
        if tab_name not in required_tabs: continue
        
        # Find banding IDs in the metadata
        for s in spreadsheet['sheets']:
            if s['properties']['sheetId'] == tab_id:
                for br in s.get('bandedRanges', []):
                    format_requests.append({"deleteBanding": {"bandedRangeId": br['bandedRangeId']}})
                # Optional: clear existing conditional rules too if needed, 
                # though index-based adding is usually fine.
    
    for tab_name, tab_id in existing_tabs.items():
        if tab_name not in required_tabs: continue
        
        # Auto-resize & Header Freeze
        format_requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1, "hideGridlines": True}},
                "fields": "gridProperties(frozenRowCount, hideGridlines)"
            }
        })
        format_requests.append({
            "autoResizeDimensions": {"dimensions": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 8}}
        })
        
        # Main Header Style
        format_requests.append({
            "repeatCell": {
                "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 8},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.05, "green": 0.05, "blue": 0.2},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 11},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        })

        if tab_name != "Executive Summary":
            # Add Alternating Colors (Banding)
            format_requests.append({
                "addBanding": {
                    "bandedRange": {
                        "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 100, "startColumnIndex": 0, "endColumnIndex": 8},
                        "rowProperties": {
                            "headerColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            "firstBandColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                            "secondBandColor": {"red": 0.96, "green": 0.96, "blue": 0.98}
                        }
                    }
                }
            })
            
            # Conditional Formatting for Severity
            for sev, color in [("P1", {"red": 0.9, "green": 0.1, "blue": 0.1}), ("P2", {"red": 0.9, "green": 0.8, "blue": 0.1}), ("P3", {"red": 0.1, "green": 0.4, "blue": 0.9})]:
                format_requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 100, "startColumnIndex": 2, "endColumnIndex": 4}],
                            "booleanRule": {
                                "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": sev}]},
                                "format": {"backgroundColor": color, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1} if sev == "P1" else {"red": 0, "green": 0, "blue": 0}}}
                            }
                        },
                        "index": 0
                    }
                })

    # Summary Specific: KPI Box
    summary_id = existing_tabs["Executive Summary"]
    format_requests.append({
        "repeatCell": {
            "range": {"sheetId": summary_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8} if report.p1_count == 0 else {"red": 1.0, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True}
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)"
        }
    })

    service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": format_requests}).execute()
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
