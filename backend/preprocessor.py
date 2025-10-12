
import sqlite3
import pandas as pd
from pathlib import Path
import json
import re
import warnings

# JPype 경고 억제
warnings.filterwarnings('ignore', category=UserWarning, module='jpype')
warnings.filterwarnings('ignore', message='.*restricted method.*')

from konlpy.tag import Okt

class TextPreprocessor:
    def __init__(self):
        
        self.okt = Okt()
        # 불용어 설정 (가독성을 위해 카테고리별로 분리)
        #data/stopwords.json 파일로부터 불용어 로드
        with open("data/stopwords-ko.json", "r", encoding="utf-8") as f:
            self.stopwords = set(json.load(f))
        # 추가적인 불용어 로드    
        with open("data/stopwords.txt", "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:  # 빈 문자열이 아닌 경우만 추가
                    self.stopwords.add(word)
      
        
        
       
        
    def preprocess(self, text):
        
            # 1. 입력값 타입 체크 (Robustness)
        if not isinstance(text, str):
            return ""

        # 2. 텍스트 정제 (Cleansing)
        #   - HTML 태그 제거 (웹 크롤링 데이터의 경우)
        text = re.sub(r'<[^>]*>', '', text)
        #   - 언론사 정보, 이메일, URL 등 불필요한 패턴 제거
        text = re.sub(r'\[.*?\]|\(.*?\)|\【.*?\】', '', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        #   - 한글, 영어, 숫자를 제외한 모든 특수문자 제거
        text = re.sub(r'[^가-힣A-Za-z0-9\s]', '', text)
        #   - 여러 개의 공백을 하나로 축소
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return ""

        # 3. 형태소 분석 및 품사 태깅 (POS Tagging)
        #   - norm=True: 'ㅋㅋㅋ'와 같은 정규화되지 않은 단어를 처리
        #   - stem=True: 어간 추출 (예: '달렸다' -> '달리다')
        pos_tagged = self.okt.pos(text, norm=True, stem=True)

        # 4. 필요한 품사 추출 및 불용어/한 글자 단어 제거
        meaningful_words = []
        for word, pos in pos_tagged:
            #   - 명사(Noun), 동사(Verb), 형용사(Adjective)만 추출 (분석 목적에 따라 변경 가능)
            if pos in ['Noun', 'Verb', 'Adjective']:
                #   - 불용어 사전에 없고, 길이가 1보다 큰 단어만 포함
                if word not in self.stopwords and len(word) > 1:
                    meaningful_words.append(word)

        # 5. 공백으로 구분된 하나의 문자열로 최종 결과 반환
        return ' '.join(meaningful_words)
        





class DatabaseLoader:
    """SQLite 데이터베이스에서 데이터를 로드하는 클래스"""
    
    def __init__(self, db_path="data/news.db"):
        """
        데이터베이스 연결 초기화
        
        Args:
            db_path (str): 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
    
    def get_connection(self):
        """데이터베이스 연결 객체 반환"""
        return sqlite3.connect(self.db_path)
    
    def get_contents(self):
        """articles 테이블에서 본문을 가져와서 pandas dataframe에 저장"""
        with self.get_connection() as conn:
            query = "SELECT id, content, preprocessed_content FROM articles WHERE article_date >= DATE('now', '-1 year') AND  preprocessed_content is NULL;"
            df_iterator = pd.read_sql_query(query, conn, chunksize=10000)
            return df_iterator
    
    def load_all_data(self, table_name=None):
        """
        테이블의 모든 데이터 로드
        
        Args:
            table_name (str, optional): 특정 테이블명. None이면 첫 번째 테이블 사용
            
        Returns:
            pandas.DataFrame: 로드된 데이터
        """
        with self.get_connection() as conn:
            if table_name is None:
                # 첫 번째 테이블 사용
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
                result = cursor.fetchone()
                if not result:
                    raise ValueError("데이터베이스에 테이블이 없습니다.")
                table_name = result[0]
            
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql_query(query, conn)
            print(f"테이블 '{table_name}'에서 {len(df)}개 행 로드됨")
            return df
    
    
    
        
    def preprocess_data(self):
        """데이터 전처리 함수""" #전처리 데이터를 news.db의 preprocessed_content 속성에 저장
        contents = self.get_contents()
        preprocessor = TextPreprocessor()
        
        # pandas 출력 옵션 설정 (생략 없이 전체 텍스트 출력)
        pd.set_option('display.max_colwidth', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_columns', None)
        
        for chunk_df in contents:
            print(f"처리할 데이터 청크 크기: {len(chunk_df)}")
            # 여기서 df의 'content' 컬럼을 전처리하고 'preprocessed_content'에 저장
            chunk_df['preprocessed_content'] = chunk_df['content'].apply(preprocessor.preprocess)
            print(chunk_df['preprocessed_content'])  # 전처리 결과 출력
            # 전처리된 데이터를 데이터베이스에 업데이트
            preprocessed_tuples = list(zip(chunk_df['preprocessed_content'], chunk_df['id']))
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    "UPDATE articles SET preprocessed_content = ? WHERE id = ?",
                    preprocessed_tuples
                )
                conn.commit()
        
        
if __name__ == "__main__":
    DatabaseLoader().preprocess_data()

# def main():
#     """메인 실행 함수 - 사용 예제"""
#     try:
#         # 데이터베이스 로더 초기화
#         loader = DatabaseLoader("data/news.db")
        
#         # 1. 데이터베이스 정보 확인
#         print("=== 데이터베이스 정보 ===")
#         table_info = loader.get_table_info()
#         for table_name, info in table_info.items():
#             print(f"\n테이블: {table_name}")
#             print(f"행 수: {info['row_count']}")
#             print("컬럼 정보:")
#             for col in info['columns']:
#                 print(f"  - {col[1]} ({col[2]})")
        
#         # 2. 샘플 데이터 로드
#         print("\n=== 샘플 데이터 ===")
#         sample_df = loader.load_sample_data(n=5)
#         print(sample_df.head())
        
#         # 3. 전체 데이터 로드
#         print("\n=== 전체 데이터 로드 ===")
#         all_data = loader.load_all_data()
#         print(f"데이터 형태: {all_data.shape}")
#         print(f"컬럼들: {list(all_data.columns)}")
        
#         # 4. 조건부 데이터 로드 (예시)
#         # print("\n=== 조건부 데이터 로드 ===")
#         # filtered_data = loader.load_filtered_data(
#         #     table_name="news",  # 실제 테이블명으로 변경
#         #     conditions={"category": "경제"},  # 실제 컬럼과 값으로 변경
#         #     columns=["title", "content", "date"]  # 실제 컬럼명으로 변경
#         # )
#         # print(filtered_data.head())
        
#         # 5. 사용자 정의 쿼리 (예시)
#         # print("\n=== 사용자 정의 쿼리 ===")
#         # custom_query = "SELECT COUNT(*) as total_count FROM your_table_name"
#         # result = loader.load_with_query(custom_query)
#         # print(result)
        
#         return all_data
        
#     except Exception as e:
#         print(f"오류 발생: {e}")
#         return None


# # 추가 유틸리티 함수들
# def quick_load(db_path="data/news.db", table_name=None):
#     """빠른 데이터 로드 함수"""
#     loader = DatabaseLoader(db_path)
#     return loader.load_all_data(table_name)

# def inspect_database(db_path="data/news.db"):
#     """데이터베이스 구조 빠른 확인"""
#     loader = DatabaseLoader(db_path)
#     return loader.get_table_info()

# def load_with_pandas(db_path="data/news.db", query="SELECT * FROM sqlite_master WHERE type='table'"):
    # """Pandas로 직접 로드하는 간단한 방법"""
    # conn = sqlite3.connect(db_path)
    # df = pd.read_sql_query(query, conn)
    # conn.close()
    # return df



