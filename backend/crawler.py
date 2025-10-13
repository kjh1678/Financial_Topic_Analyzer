import requests #기사본문 크롤링 라이브러리
#from playwright.sync_api import sync_playwright #기사목록 크롤링 라이브러리
from bs4 import BeautifulSoup #HTML 파싱 라이브러리
from datetime import datetime #날짜처리 라이브러리
import time, random #딜레이처리 라이브러리
import sqlite3 #DB처리 라이브러리

DB_PATH = 'data/news.db' # 데이터베이스 파일 경로

# 다양한 User-Agent 리스트
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
    # 필요에 따라 더 추가
]

# 프록시 리스트 예시 (실제 사용 가능한 프록시로 교체 필요)
proxies_list = [
    # 'http://username:password@proxy1.example.com:8080',
    # 'http://proxy2.example.com:3128',
    # 'https://proxy3.example.com:443',
    # 무료 프록시는 신뢰성이 낮으니, 유료/자체 프록시 추천
]

crawled_news=0 # 크롤링한 뉴스 기사 수

def get_random_headers():
    return {
        'User-Agent': random.choice(user_agents)
    }

def get_random_proxy():
    if proxies_list:
        return {'http': random.choice(proxies_list), 'https': random.choice(proxies_list)}
    else:
        return None

def setup_database():
    """데이터베이스와 테이블이 없으면 생성합니다."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            content TEXT,
            article_date TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"데이터베이스 '{DB_PATH}' 준비 완료.")
    
def save_daily_articles_to_db(articles_list):
    """
    하루치 기사 데이터 리스트 전체를 DB에 저장합니다.
    """
    if not articles_list:
        print("저장할 새로운 기사가 없습니다.")
        return 0
    
    setup_database()  # DB와 테이블 준비
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        sql = '''
            INSERT OR IGNORE INTO articles (title, content, article_date) 
            VALUES (?, ?, ?)
        '''
        cur.executemany(sql, articles_list)
        conn.commit()
        print(f"--- 총 {len(articles_list)}개 기사를 DB에 성공적으로 저장했습니다. ---")
        return len(articles_list)
    except Exception as e:
        print(f"!!! DB 저장 중 오류 발생: {e}")
        return 0
    finally:
        conn.close()
    
def crawl_naver_news_article(url):
        
    try:
        headers = get_random_headers()
        proxies = get_random_proxy()
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        response.encoding='utf-8'
        
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag= soup.select_one("h2#title_area")
        title=title_tag.get_text(strip=True) if title_tag else 'No Title Found'
        content_tag=soup.select_one('article#dic_area')
        
        if content_tag:
            for photo_tag in content_tag.select('span.end_photo_org'):
                photo_tag.decompose()
            content=content_tag.get_text(strip=True) 
        else:
            content='No Content Found'
        
        date_tag=soup.select_one('span.media_end_head_info_datestamp_time._ARTICLE_DATE_TIME') 
        date=date_tag.get('data-date-time') if date_tag else 'No Date Found'
       
        print("="*50)
        print(f"기사 제목: {title}")
        print("="*50)
        print(f"기사 본문:\n{content}")
        print("="*50)
        print(f"기사 작성일: {date}")
        return (
            title,
            content,
            date
        )
        
    except requests.exceptions.RequestException as e:
        print(f"!!! HTTP 요청 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"!!! 크롤링 중 오류 발생: {e}")
        return None

    
def crawl_onePage(html):
    global crawled_news 
    soup = BeautifulSoup(html, 'html.parser')
    a_tags = soup.select("dd.articleSubject a")
    urls = [a.get('href') for a in a_tags if a.get('href')]
    all_articles_for_onePage = [] # 한 페이지 기사 데이터를 저장할 리스트
    for link in urls:
        print(f"크롤링 중인 URL: {link}")
        article_data = crawl_naver_news_article(link)
        all_articles_for_onePage.append(article_data)
        crawled_news += 1
        print(f"현재까지 크롤링한 뉴스 기사 수: {crawled_news}")
        time.sleep(random.uniform(1, 4))  # 1~4초 랜덤 딜레이

    return all_articles_for_onePage

def check_last_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    td_tags = soup.select('table[summary="페이지 네비게이션 리스트"] tbody tr td')  # '다음' 버튼 선택
    if not td_tags:
        return True  # 페이지 버튼이 없으면 마지막 페이지로 간주
    last_td = td_tags[-1]
    # 마지막 td의 class가 'on'이면 마지막 페이지
    return 'on' in last_td.get('class', [])

def crawl_daily_news(date):
    
    date_str = date.strftime('%Y-%m-%d') 
    nth_page=1 # 시작 페이지 번호
    crawled_news=0
    all_articles_for_the_day = [] # 하루치 기사 데이터를 저장할 리스트
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # 크로미움 브라우저 실행
        page = browser.new_page()   # 새 페이지 열기
        last_page=False # 마지막 페이지 여부
        while not last_page:
            page.goto(f"https://finance.naver.com/news/mainnews.naver?date={date_str}&page={nth_page}")
            page.wait_for_selector("dd.articleSubject a")  # 요소가 로드될 때까지 대기
            html = page.content() # 페이지 HTML 가져오기
            all_articles_for_the_day.extend(crawl_onePage(html) ) # 한 페이지 기사 크롤링 및 저장
            print(f"{date_str} {nth_page}페이지 크롤링 완료")
            last_page=check_last_page(html)
            if not last_page:
                time.sleep(random.uniform(1, 3))  # 1~3초 랜덤 딜레이
                nth_page += 1
            
            
        browser.close()
        
    save_daily_articles_to_db(all_articles_for_the_day)
   

if __name__ == '__main__':
    target_date = datetime(2025, 9, 20)  # 크롤링할 날짜 설정
    crawl_daily_news(target_date)
 
 
