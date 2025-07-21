
import os
import re
import time
import random
import shutil
import pandas as pd
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from pandas import ExcelWriter
from selenium.webdriver.chrome.service import Service  # ✅ 이 줄 추가


def get_executable_dir():
    if getattr(sys, 'frozen', False):
        # .app이 있는 폴더
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 스크립트가 있는 폴더
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    # .app 실행 시 base path는 Contents/MacOS가 됨
    if getattr(sys, 'frozen', False):
        base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

CHROMEDRIVER_PATH = resource_path("resources/chromedriver")

BASE_DIR = get_executable_dir()
URL_FILE_PATH = os.path.join(BASE_DIR, "네이버_검색어.xlsx")
FILES_DIR = os.path.join(BASE_DIR, "files")
BACKUP_DIR = os.path.join(FILES_DIR, "백업")
ACCUMULATED_FILE_PATH = os.path.join(FILES_DIR, "카페글_조회수_수집_누적.xlsx")

os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

today_prefix = datetime.now().strftime("%Y%m%d")
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

# ✅ 누적 파일 백업
if os.path.exists(ACCUMULATED_FILE_PATH):
    backup_filename = f"카페글_조회수_수집_누적_{current_time}.xlsx"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    shutil.copy(ACCUMULATED_FILE_PATH, backup_path)
    print(f"🗂️ 누적 파일 백업 완료: {backup_path}")
else:
    print("⚠️ 누적 파일이 없어 백업은 생략됩니다.")

# ✅ 크롬 드라이버 실행 및 로그인 대기
print("🆕 Chrome driver 실행")
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


service = Service(executable_path=CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)
print(f"✅ 사용되는 chromedriver 경로: {CHROMEDRIVER_PATH}")
print(f"✅ 파일 존재 여부: {os.path.exists(CHROMEDRIVER_PATH)}")
driver.get("https://naver.com")
print("🔓 네이버 로그인 시간을 60초 드립니다...")
time.sleep(60)

# ✅ 카페 URL 목록 로딩
cafe_df = pd.read_excel(URL_FILE_PATH)
CAFE_VIEW_LIST = []

try:
    for idx, row in cafe_df.iterrows():
        keyword = row.get("키워드", "")
        visit_cafe_url = row["링크"]

        driver.get(visit_cafe_url)
        time.sleep(random.uniform(2, 3))

        count = 0
        try:
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//iframe[@id='cafe_main']"))
            )
            driver.switch_to.frame(iframe)

            try:
                elem = driver.find_element(By.XPATH, "/html/body/div/div/div/div[2]/div[1]/div[2]/div[2]/div[2]/span[2]")
                text = elem.text.strip()
                count = int(re.sub(r"\D", "", text)) if "조회" in text else int(text)
                print(f"[{visit_cafe_url}] ▶ 조회수: {count}")
            except Exception as e:
                print(f"[{visit_cafe_url}] ❌ 조회수 추출 실패: {e}")
        except UnexpectedAlertPresentException:
            try:
                alert = driver.switch_to.alert
                print(f"[{visit_cafe_url}] ⚠️ Alert 감지: {alert.text}")
                alert.accept()
            except NoAlertPresentException:
                pass
        except Exception as e:
            print(f"[{visit_cafe_url}] ❌ iframe 진입 실패: {e}")

        CAFE_VIEW_LIST.append([keyword, visit_cafe_url, count])
        time.sleep(random.uniform(3, 5))
finally:
    driver.quit()

# ✅ 오늘자 데이터 저장
if CAFE_VIEW_LIST:
    df_today = pd.DataFrame(CAFE_VIEW_LIST, columns=["키워드", "링크", today_prefix])
    today_filename = os.path.join(FILES_DIR, f"카페글_조회수_수집_{current_time}.xlsx")
    with ExcelWriter(today_filename, engine="xlsxwriter") as writer:
        df_today.to_excel(writer, index=False, sheet_name="조회수기록")

    # ✅ 누적파일 로딩 및 병합
    try:
        df_old = pd.read_excel(ACCUMULATED_FILE_PATH)
    except FileNotFoundError:
        df_old = pd.DataFrame(columns=["키워드", "링크"])

    df_old = df_old.loc[:, ~df_old.columns.astype(str).str.contains("조회수 변화량")]
    df_merged = pd.merge(df_old, df_today, on=["키워드", "링크"], how="outer")

    df_merged.columns = df_merged.columns.map(str)
    date_cols_in_order = sorted([col for col in df_merged.columns if re.fullmatch(r"\d{8}", col)])

    if len(date_cols_in_order) >= 2:
        prev_col = date_cols_in_order[-2]
        last_col = date_cols_in_order[-1]
        last_values = pd.to_numeric(df_merged[last_col], errors="coerce").fillna(0)
        prev_values = pd.to_numeric(df_merged[prev_col], errors="coerce").fillna(0)
        df_merged["조회수 변화량"] = last_values - prev_values
    else:
        last_col = today_prefix
        df_merged["조회수 변화량"] = 0

    with ExcelWriter(ACCUMULATED_FILE_PATH, engine="xlsxwriter") as writer:
        df_merged.to_excel(writer, index=False, sheet_name="조회수기록")
        workbook = writer.book
        worksheet = writer.sheets["조회수기록"]

        yellow_fmt = workbook.add_format({'bg_color': '#FFF2CC'})
        text_fmt = workbook.add_format({'num_format': '@'})

        for col in date_cols_in_order:
            if col in df_merged.columns:
                col_idx = df_merged.columns.get_loc(col)
                col_letter = chr(ord("A") + col_idx)
                worksheet.set_column(f"{col_letter}:{col_letter}", None, text_fmt)

        for col in [last_col, "조회수 변화량"]:
            if col in df_merged.columns:
                col_idx = df_merged.columns.get_loc(col)
                col_letter = chr(ord("A") + col_idx)
                worksheet.set_column(f"{col_letter}:{col_letter}", None, workbook.add_format({'num_format': '0'}))

        row_count = len(df_merged) + 1
        diff_idx = df_merged.columns.get_loc("조회수 변화량")
        today_idx = df_merged.columns.get_loc(last_col)
        diff_col_letter = chr(ord("A") + diff_idx)
        today_col_letter = chr(ord("A") + today_idx)

        worksheet.conditional_format(f"{diff_col_letter}2:{diff_col_letter}{row_count}", {
            'type': 'cell',
            'criteria': '>=',
            'value': 100,
            'format': yellow_fmt
        })
        worksheet.conditional_format(f"{today_col_letter}2:{today_col_letter}{row_count}", {
            'type': 'formula',
            'criteria': f"=${diff_col_letter}2>=100",
            'format': yellow_fmt
        })

    print(f"✅ 누적 엑셀 저장 완료: {ACCUMULATED_FILE_PATH}")
else:
    print("⚠️ 저장할 데이터가 없습니다.")
