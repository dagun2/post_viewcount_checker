import os
import re
import time
import random
import shutil
import pandas as pd
import sys
import logging
import platform
import subprocess
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    UnexpectedAlertPresentException, NoAlertPresentException,
    TimeoutException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from pandas import ExcelWriter


# =========================
# 경로 유틸 (입력 엑셀은 절대 변경 X)
# =========================
def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../../../"))
    else:
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    # .app 실행 시 base path는 Contents/MacOS가 됨
    if getattr(sys, 'frozen', False):
        base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


# =========================
# 기본 경로/파일
# =========================
BASE_DIR = get_executable_dir()

URL_FILE_PATH = os.path.join(BASE_DIR, "네이버_검색어.xlsx")  # 입력 엑셀: 위치 그대로 유지
FILES_DIR = os.path.join(BASE_DIR, "files")                  # 출력 폴더
os.makedirs(FILES_DIR, exist_ok=True)

LOGS_DIR = os.path.join(BASE_DIR, "logs")                    # 로그 폴더
os.makedirs(LOGS_DIR, exist_ok=True)

current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
today_prefix = datetime.now().strftime("%Y%m%d")

# 출력 엑셀 파일명(요청: "_수집" 제거)
OUTPUT_XLSX = os.path.join(FILES_DIR, f"카페글_조회수_{current_time}.xlsx")

# =========================
# 로깅 설정 (파일 + 콘솔)
# =========================
LOG_FILE = os.path.join(LOGS_DIR, f"run_{current_time}.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("crawler")

log.info(f"BASE_DIR: {BASE_DIR}")
log.info(f"INPUT  : {URL_FILE_PATH}")
log.info(f"OUTPUT : {OUTPUT_XLSX}")
log.info(f"LOG    : {LOG_FILE}")

# =========================
# Selenium (크롬 버전 독립 실행)
# - Selenium Manager 사용: 드라이버 자동 매칭
# =========================
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
chrome_options.add_experimental_option("useAutomationExtension", False)

# 로드 전략: DOM 로드까지만 (속도 개선)
chrome_options.page_load_strategy = "eager"

# 필요시 헤드리스 전환 가능(로그인 과정에선 UI가 보이는게 안전)
# chrome_options.add_argument("--headless=new")

# ✅ 핵심: Service(executable_path=...) 미지정 → Selenium Manager가 자동으로 크롬 버전에 맞는 드라이버 설치/사용
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(20)
wait = WebDriverWait(driver, 12)


# =========================
# 보조 함수
# =========================
def safe_int_from_text(t: str) -> int:
    nums = re.findall(r"\d+", t or "")
    return int(nums[0]) if nums else 0

def open_log_after_finish(path: str):
    """작업 후 macOS에서 로그 파일 열기"""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        elif platform.system() == "Windows":
            os.startfile(path)  # type: ignore
        else:
            # Linux 등은 xdg-open 시도
            subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        log.warning(f"로그 자동 열기 실패(무시 가능): {e}")

def human_delay(min_s=0.6, max_s=1.4):
    """봇 탐지 완화용 사람같은 랜덤 지연"""
    time.sleep(random.uniform(min_s, max_s))


# =========================
# 로그인 (매 실행 새 로그인 OK)
# =========================
try:
    driver.get("https://www.naver.com")
    log.info("네이버 접속. 로그인 대기 60초(요청에 따라 세션 재사용 안함).")
    # 로그인 유지를 원치 않으므로 기존 구조 유지
    time.sleep(60)
except TimeoutException:
    log.warning("네이버 첫 페이지 로드 타임아웃. 계속 진행해봅니다.")

human_delay(1.0, 2.0)

# =========================
# 입력 엑셀 읽기
# =========================
if not os.path.exists(URL_FILE_PATH):
    log.error("입력 엑셀(네이버_검색어.xlsx)이 존재하지 않습니다. 작업을 종료합니다.")
    try:
        driver.quit()
    except Exception:
        pass
    sys.exit(1)

try:
    cafe_df = pd.read_excel(URL_FILE_PATH)
except Exception as e:
    log.error(f"입력 엑셀 로드 실패: {e}")
    try:
        driver.quit()
    except Exception:
        pass
    sys.exit(1)

# 필수 컬럼 점검
if not set(["키워드", "링크"]).issubset(set(cafe_df.columns)):
    log.error("입력 엑셀에 '키워드', '링크' 컬럼이 필요합니다.")
    try:
        driver.quit()
    except Exception:
        pass
    sys.exit(1)

# =========================
# 크롤링
# =========================
CAFE_VIEW_LIST = []
total = len(cafe_df)
log.info(f"총 {total}건 수집 시작")

try:
    for idx, row in cafe_df.iterrows():
        keyword = str(row.get("키워드", "")).strip()
        visit_cafe_url = str(row["링크"]).strip()

        log.info(f"[{idx+1}/{total}] 방문: {visit_cafe_url}")
        try:
            driver.get(visit_cafe_url)
        except TimeoutException:
            log.warning("페이지 로드 타임아웃 → 0으로 기록하고 다음으로 진행")
            CAFE_VIEW_LIST.append([keyword, visit_cafe_url, 0])
            human_delay(1.0, 2.0)
            continue

        # iframe 진입
        count = 0
        try:
            iframe = wait.until(EC.presence_of_element_located((By.ID, "cafe_main")))
            driver.switch_to.frame(iframe)

            # 조회수 요소 탐색(텍스트/클래스 모두 대응)
            # - contains(., '조회') 텍스트 포함
            # - 흔한 카운터 클래스명 대비: view, count 등
            xpath_candidates = [
                "//span[contains(., '조회')]",
                "//*[contains(@class,'view') and (self::span or self::em or self::div)]",
                "//*[contains(@class,'count') and (self::span or self::em or self::div)]",
                # 필요시 더 추가
            ]

            elem = None
            for xp in xpath_candidates:
                try:
                    elem = WebDriverWait(driver, 4).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    # 가장 먼저 잡힌 후보를 사용
                    text = elem.text.strip()
                    val = safe_int_from_text(text)
                    if val > 0:
                        count = val
                        break
                except TimeoutException:
                    continue

            # 후보들에서 못 찾았으면 마지막으로 한 번 더 시도(원래 XPath가 있다면 여기에)
            if count == 0:
                try:
                    elem = driver.find_element(By.XPATH, "/html/body/div/div/div/div[2]/div[1]/div[2]/div[2]/div[2]/span[2]")
                    count = safe_int_from_text(elem.text.strip())
                except Exception:
                    pass

            if count == 0:
                log.warning(f"조회수 추출 실패(0으로 기록) URL: {visit_cafe_url}")
            else:
                log.info(f"▶ 조회수: {count}")

        except UnexpectedAlertPresentException:
            try:
                alert = driver.switch_to.alert
                log.warning(f"Alert 감지: {alert.text}")
                alert.accept()
            except NoAlertPresentException:
                pass
        except Exception as e:
            log.warning(f"iframe/파싱 실패: {e}")
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

        CAFE_VIEW_LIST.append([keyword, visit_cafe_url, count])

        # 사람같은 지연(페이지별)
        human_delay(0.8, 1.8)

finally:
    try:
        driver.quit()
    except Exception:
        pass

# =========================
# 오늘자 결과 엑셀 저장 (누적 관련 전부 제거)
# =========================
if CAFE_VIEW_LIST:
    df_today = pd.DataFrame(CAFE_VIEW_LIST, columns=["키워드", "링크", today_prefix])
    try:
        with ExcelWriter(OUTPUT_XLSX, engine="xlsxwriter") as writer:
            df_today.to_excel(writer, index=False, sheet_name="조회수기록")
        log.info(f"✅ 결과 저장 완료: {OUTPUT_XLSX}")
    except Exception as e:
        log.error(f"엑셀 저장 실패: {e}")
else:
    log.warning("⚠️ 저장할 데이터가 없습니다(수집 결과 0건).")

log.info("모든 작업 완료. 로그 파일을 열겠습니다.")
open_log_after_finish(LOG_FILE)
