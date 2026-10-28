import json

import gspread
from google.oauth2.service_account import Credentials

from .config import Settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = ["Дата/Время", "Имя официанта", "Telegram ID", "Номер стола", "Состав заказа", "Итоговая сумма", "ID заказа"]


class SheetsStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.worksheet = None

    def connect(self):
        if self.settings.google_credentials_json:
            credentials = Credentials.from_service_account_info(
                json.loads(self.settings.google_credentials_json), scopes=SCOPES
            )
        else:
            credentials = Credentials.from_service_account_file(
                self.settings.google_credentials_file, scopes=SCOPES
            )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(self.settings.spreadsheet_id)
        try:
            self.worksheet = spreadsheet.worksheet(self.settings.worksheet_name)
        except gspread.WorksheetNotFound:
            self.worksheet = spreadsheet.add_worksheet(
                title=self.settings.worksheet_name, rows=1000, cols=len(HEADERS)
            )
        if not self.worksheet.row_values(1):
            self.worksheet.append_row(HEADERS, value_input_option="USER_ENTERED")

    def append_order(self, values: list):
        if self.worksheet is None:
            self.connect()
        self.worksheet.append_row(values, value_input_option="USER_ENTERED")
