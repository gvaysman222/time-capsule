import gspread
from google.oauth2.service_account import Credentials

# Укажите путь к вашему файлу учетных данных
SERVICE_ACCOUNT_FILE = 'path/to/your/service_account.json'

# Список авторизованных API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Авторизация
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

# Подключение к Google Таблице
SPREADSHEET_ID = 'your_google_sheet_id'  # Укажите ID вашей таблицы
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

# Создание нового листа для команды
def create_team_sheet(team_name):
    try:
        sheet = spreadsheet.add_worksheet(title=team_name, rows="100", cols="10")
        # Добавляем заголовки
        sheet.append_row(["Пользователь", "Вопрос", "Ответ"])
        return sheet
    except gspread.exceptions.APIError as e:
        print(f"Ошибка при создании листа: {e}")
        return None

# Запись ответов в лист
def write_responses_to_sheet(team_name, user_name, responses):
    try:
        # Проверяем, существует ли лист
        sheet = None
        try:
            sheet = spreadsheet.worksheet(team_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = create_team_sheet(team_name)

        # Записываем ответы
        for question, answer in responses:
            sheet.append_row([user_name, question, answer])

        print(f"Ответы для команды '{team_name}' успешно записаны.")
    except Exception as e:
        print(f"Ошибка при записи данных: {e}")
