import sqlite3
import pandas as pd
from google import genai
from google.genai import types
import chromadb
import time
import json
import tempfile
import os
from pathlib import Path
import pickle
from datetime import datetime, timedelta



# --- 1. 설정 (Configuration) ---
# 본인의 Gemini API 키를 입력하세요.
# (실제 서비스에서는 환경 변수나 Secret Manager를 사용하는 것이 안전합니다.)
GOOGLE_API_KEY = 'AIzaSyCeTC1TeKmmQtk16PnEtf469Q2nkgGt2MA'

# 사용할 임베딩 모델
EMBEDDING_MODEL = 'gemini-embedding-001'

# 원본 데이터베이스 파일 경로
DB_FILE_PATH = 'data/news.db'
EMBEDDING_RDB_PATH = 'data/embeddings.db'

# 벡터 데이터베이스 설정
CHROMA_DB_PATH = 'data/embedding_db' # 벡터 DB 파일이 저장될 디렉토리
COLLECTION_NAME = 'news_articles_v1' # 생성할 컬렉션 이름

class Embedder:
    def __init__(self, api_key=GOOGLE_API_KEY, db_path=DB_FILE_PATH, chroma_path=CHROMA_DB_PATH, collection_name=COLLECTION_NAME):
        """
        Embedder 클래스 초기화 (Batch API 전용)
        
        Args:
            api_key (str): Google Gemini API 키
            db_path (str): SQLite 데이터베이스 파일 경로
            chroma_path (str): ChromaDB 저장 경로
            collection_name (str): ChromaDB 컬렉션 이름
        """
        self.api_key = api_key
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.embedding_model = EMBEDDING_MODEL
        self.gemini_client = None
        self.vectorDB_client = None
        self.collection = None
        
       
        self.embedding_db_conn = None
        self.embedding_db_cur = None
        
        self._setup_embedding_db()
        
        # Gemini API 설정
        self._setup_gemini_api()
        
        # ChromaDB 설정
        self._setup_chroma_db()
    
    def _setup_gemini_api(self):
        """Gemini API 설정"""
        try:
            self.gemini_client = genai.Client(api_key=self.api_key)
            print("Gemini API가 성공적으로 설정되었습니다.")
        except Exception as e:
            print(f"Gemini API 설정 실패: {e}")
            raise e
    
    def _setup_chroma_db(self):
        """ChromaDB 클라이언트 설정"""
        try:
            self.vectorDB_client = chromadb.PersistentClient(path=self.chroma_path)
            # 컬렉션이 이미 존재하면 가져오고, 없으면 생성
            self.collection = self.vectorDB_client.get_or_create_collection(name=self.collection_name)
            print(f"ChromaDB 클라이언트가 준비되었고 '{self.collection_name}' 컬렉션을 사용합니다.")
        except Exception as e:
            print(f"ChromaDB 설정 실패: {e}")
            raise e
        
    def _setup_embedding_db(self):
        try:
            self.embedding_db_conn = sqlite3.connect(EMBEDDING_RDB_PATH)
            self.embedding_db_cur = self.embedding_db_conn.cursor()
            self.embedding_db_cur.execute('''
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY,
                    embedding TEXT
                )
            ''')
            self.embedding_db_conn.commit()
            print(f"임베딩 데이터베이스 '{EMBEDDING_RDB_PATH}'가 준비되었습니다.")
        except Exception as e:
            print(f"임베딩 데이터베이스 설정 실패: {e}")
            raise e
    
    def _create_batch_input_file(self, chunk_df, f):
       
        for row in chunk_df.itertuples():

            id = row.id
            title_and_content = f"뉴스 기사 제목: {row.title}\n뉴스 기사 본문: {row.content}"
            date = row.article_date

            # Batch API 요청 형식
            request = {
                "key": f"{id}_{date}",
                "request": {
                    "task_type": "CLUSTERING",
                    "output_dimensionality": 768,
                    "content": {"parts": [{"text": title_and_content}] },
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')

        print(f" {len(chunk_df):,}개 문서 입력 완료")
        
    def load_data_and_store(self, start_date, end_date, chunk_size=10000):
        """
        데이터베이스에서 청크 단위로 데이터를 로드하는 제너레이터
        
        Args:
            start_date (str): 시작 날짜 (YYYY-MM-DD 형식)
            end_date (str): 종료 날짜 (YYYY-MM-DD 형식)
            chunk_size (int): 청크 크기
        
        Yields:
            pd.DataFrame: 청크 단위 데이터프레임
        """
        conn = sqlite3.connect(self.db_path)
        query = "SELECT id, title, content, article_date FROM articles WHERE content IS NOT NULL AND content != '' AND article_date >= ? AND article_date < ?;"
        
        try:
            chunk_iterator = pd.read_sql_query(
                query, 
                conn, 
                params=(start_date, end_date),
                chunksize=chunk_size
            )
            
            chunk_count = 0
            
            temp_fd, temp_file = tempfile.mkstemp(suffix='.jsonl', prefix="embedding_batch")
            os.close(temp_fd)
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                

                for chunk_df in chunk_iterator:
                    chunk_count += 1
                    
                    # 전체 텍스트 컬럼 생성 (title + content)
                    
                    print(f"청크 {chunk_count} 로드: {len(chunk_df)}개 문서")
    
                    self._create_batch_input_file(chunk_df, f) # Batch 입력 파일 생성
                
        except Exception as e:
            print(f"청크 데이터 로드 실패: {e}")
            raise e
        finally:
            conn.close()
            
        return temp_file
    
    

    def create_batch_job(self, file_path):
        """
        Batch 입력 파일을 Google AI Studio에 업로드
        
        Args:
            file_path (str): 업로드할 JSONL 파일 경로
            
        Returns:
            object: 업로드된 파일 객체
        """
        try:
            print(f"Uploading file: {file_path}")
            uploaded_batch_requests = self.gemini_client.files.upload(
                file=file_path,
                config=types.UploadFileConfig(display_name='my-batch-requests', mime_type="jsonl")
            )
            print(f"Create the Batch Job: {uploaded_batch_requests.name}")
            
            batch_job = self.gemini_client.batches.create_embeddings(
                model=self.embedding_model,
                src=types.EmbeddingsBatchJobSource(file_name=uploaded_batch_requests.name),
                config={'display_name': "Input embeddings batch"},
            )
            print(f"Created batch job from file: {batch_job.name}")
            
            return batch_job
            
        except Exception as e:
            print(f"파일 업로드 실패: {e}")
            raise e
    
    
    def Monitor_job_status(self, batch_job, check_interval=30, max_wait_time=3600):
        """
        Batch 작업 완료 대기
        
        Args:
            batch_job: Batch 작업 객체
            check_interval (int): 상태 확인 간격 (초)
            max_wait_time (int): 최대 대기 시간 (초)
            
        Returns:
            object: 완료된 Batch 작업 상태 또는 None
        """
        print(" Batch 작업 완료 대기 중...")

        print(f"Polling status for job: {batch_job.name}")

        # Poll the job status until it's completed.
        while True:
            batch_job = self.gemini_client.batches.get(name=batch_job.name)
            if batch_job.state.name in ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED'):
                break
            print(f"Job not finished. Current state: {batch_job.state.name}. Waiting 30 seconds...")
            time.sleep(30)

        print(f"Job finished with state: {batch_job.state.name}")
        if batch_job.state.name == 'JOB_STATE_FAILED':
            print(f"Error: {batch_job.error}")
        
        return batch_job
       

    def _download_and_store_embeddings(self, batch_job):
        """
        임베딩을 ChromaDB에 저장

        Args:
            batch_job: Batch 작업 객체
        """
        if batch_job.state.name == 'JOB_STATE_SUCCEEDED':
            # The output is in another file.
            result_file_name = batch_job.dest.file_name
            print(f"Results are in file: {result_file_name}")

            print("\nDownloading and parsing result file content...")
            file_content_bytes = self.gemini_client.files.download(file=result_file_name)
            file_content = file_content_bytes.decode('utf-8')

        else:
            print(f"Job did not succeed. Final state: {batch_job.state.name}")
            return

        # 결과 파일 내용 파싱
        embeddings_with_keys = []
        for line in file_content.splitlines():
            if line:
                parsed_response = json.loads(line)
                embedding = parsed_response.get('response', {}).get('embedding', {}).get('values')

                # 'key' 값 추출 (새로 추가)
                key = parsed_response.get('key')
                if key:
                    id, date = key.split('_', 1)
                    # (key, embedding) 튜플 형태로 리스트에 추가
                    if embedding:  # key와 embedding이 모두 존재할 때만 추가
                        embeddings_with_keys.append((id, date, embedding))
                

        print(f" {len(embeddings_with_keys):,}개 임베딩 다운로드 완료")
        
        print(embeddings_with_keys) 
            
        try:
            self.embedding_db_cur.executemany('''
                INSERT INTO embeddings (id, embedding) VALUES (?, ?)
            ''', [(id, str(embedding)) for id, _, embedding in embeddings_with_keys])
            self.embedding_db_conn.commit()
            print(f" {len(embeddings_with_keys):,}개 임베딩 저장 완료")
        except Exception as e:
            print(f" 임베딩 데이터베이스 저장 실패: {e}")
    
        try:
            ids = [id for id, _, _ in embeddings_with_keys]
            embs = [emb for _, _, emb in embeddings_with_keys]
            metadatas = [{"article_date": date} for _, date, _ in embeddings_with_keys]

            # ChromaDB에 데이터 추가 (청크 단위로 나누어 저장)
            storage_chunk_size = 1000
            
            for i in range(0, len(ids), storage_chunk_size):
                chunk_ids = ids[i:i+storage_chunk_size]
                chunk_embeddings = embs[i:i+storage_chunk_size]
                chunk_metadatas = metadatas[i:i+storage_chunk_size]
                
                self.collection.upsert(
                    ids=chunk_ids,
                    embeddings=chunk_embeddings,
                    metadatas=chunk_metadatas
                )
                
                print(f"저장 진행: {i+len(chunk_ids):,}/{len(ids):,}")

            print(f"{len(embeddings_with_keys):,}개 임베딩 저장 완료")

        except Exception as e:
            print(f" ChromaDB 저장 실패: {e}")
    
    def embed_and_store_batch(self, start_date, end_date, chunk_size=10000):
        """
        Batch API를 사용한 대량 임베딩 및 저장
        
        Args:
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
            chunk_size (int): 데이터베이스 청크 크기
            batch_size (int): Batch API 배치 크기
        """
        print(f"\nBatch API를 사용하여 임베딩을 시작합니다...")
        print(f"설정: DB 청크={chunk_size:,}")
        
        try:
            # 먼저 모든 데이터를 수집
            temp_file = self.load_data_and_store(start_date, end_date, chunk_size) # start_date, end_date 기간의 모든 데이터를 jsonl 파일로 생성
            created_batch_job = self.create_batch_job(temp_file) # Batch 작업 생성
            final_batch_job = self.Monitor_job_status(created_batch_job) # 작업 완료 대기

            if final_batch_job.state.name == 'JOB_STATE_SUCCEEDED':
                print("배치 작업이 성공적으로 완료되었습니다.")
            else:
                print(f"배치 작업이 실패하였습니다. 최종 상태: {final_batch_job.state.name}")
                
            self._download_and_store_embeddings(final_batch_job) # 임베딩 다운로드 및 ChromaDB에 저장
            
        except Exception as e:
            print(f"임베딩 및 저장 중 오류 발생: {e}")
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"임시 파일 '{temp_file}'이(가) 삭제되었습니다.")
        
def batch_embedding_main(start, end):
    """메인 실행 함수 (Batch API 전용)"""
    try:
        # Embedder 인스턴스 생성
        embedder = Embedder()
        
        # Batch API로 임베딩 및 저장
        embedder.embed_and_store_batch(
            start_date=start,
            end_date=end,
            chunk_size=10000,   # DB에서 한 번에 읽어올 문서 수
        )
        
    except Exception as e:
        print(f"메인 실행 중 오류 발생: {e}")

   
if __name__ == "__main__":
   for day in pd.date_range(start='2025-08-27', end='2025-11-18', freq='1D'):
     batch_embedding_main(start=day.strftime('%Y-%m-%d'), end=(day + timedelta(days=1)).strftime('%Y-%m-%d'))