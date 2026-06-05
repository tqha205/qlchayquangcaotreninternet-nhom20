from app.models.daily_report import DailyReportModel
import json

try:
    print(json.dumps(DailyReportModel.get_cashflow_forecast(), ensure_ascii=False))
except Exception as e:
    print("Error:", e)
