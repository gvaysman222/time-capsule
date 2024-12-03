import gspread
from google.oauth2.service_account import Credentials

# Укажите путь к вашему файлу учетных данных
SERVICE_ACCOUNT_FILE = 'Commons/keys.json'

# Список авторизованных API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Авторизация
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

# Подключение к Google Таблице
SPREADSHEET_ID = '1U6EowzPVdcf2jVBjnfVe0DUZ-Z4ns68rJqnNC_INnIA'  # Укажите ID вашей таблицы
spreadsheet = gc.open_by_key(SPREADSHEET_ID)


# Создание нового листа для команды
def create_team_sheet(team_name, num_questions):
    try:
        # Создаём новый лист с названием команды
        sheet = spreadsheet.add_worksheet(title=team_name, rows="100", cols=str(num_questions + 1))

        # Заголовки: первый столбец — пользователь, остальные — порядковые номера вопросов
        headers = ["Пользователь"] + [str(i + 1) for i in range(num_questions)]
        sheet.append_row(headers)
        return sheet
    except gspread.exceptions.APIError as e:
        print(f"Ошибка при создании листа: {e}")
        return None


# Запись ответов в таблицу
def write_responses_to_sheet(team_name, user_name, responses):
    try:
        # Проверяем, существует ли лист
        sheet = None
        try:
            sheet = spreadsheet.worksheet(team_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = create_team_sheet(team_name, len(responses))

        # Подготовка строки для записи
        row = [user_name] + responses
        sheet.append_row(row)

        print(f"Ответы для команды '{team_name}' успешно записаны.")
    except Exception as e:
        print(f"Ошибка при записи данных: {e}")
