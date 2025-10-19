import sqlite3
import pandas as pd
import google import genai
from google.genai import types
import chromadb
import time
import json
import tempfile
import os
from pathlib import Path

# --- 1. 설정 (Configuration) ---
# 본인의 Gemini API 키를 입력하세요.
# (실제 서비스에서는 환경 변수나 Secret Manager를 사용하는 것이 안전합니다.)
GOOGLE_API_KEY = 'YOUR_API_KEY_HERE'

# 사용할 임베딩 모델
EMBEDDING_MODEL = 'gemini-embedding-001'

# 원본 데이터베이스 파일 경로
DB_FILE_PATH = 'data/news.db'

# 벡터 데이터베이스 설정
CHROMA_DB_PATH = 'data/chroma_db' # 벡터 DB 파일이 저장될 디렉토리
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
        self.batch_job= None
        
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
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            print(f"ChromaDB 클라이언트가 준비되었고 '{self.collection_name}' 컬렉션을 사용합니다.")
        except Exception as e:
            print(f"ChromaDB 설정 실패: {e}")
            raise e
        
    
    
    def load_data_chunked(self, start_date, end_date, chunk_size=10000):
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
    
    def _create_batch_input_file(self, chunk_df, f):
       
        for row in chunk_df.itertuples():

            id = row.id
            title_and_content = f"뉴스 기사 제목: {row.title}\n뉴스 기사 본문: {row.content}"
            date = row.article_date

            # Batch API 요청 형식
            request = {
                "key": f"{id}_{date}",
                "request": {
                    "output_dimensionality" : 1536,
                    "contents":[{"parts": [{"text": title_and_content}] }],
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')

        print(f" {len(chunk_df):,}개 문서 입력 완료")

    def _create_batch_job(self, file_path):
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
                config=types.UploadFileConfig(mime_type="jsonl")
            )
            print(f"Create the Batch Job: {uploaded_batch_requests.name}")
            
            batch_job = self.gemini_client.batches.create_embeddings(
                model=self.embedding_model,
                src=types.embedding.BatchJobSource(file_name=uploaded_batch_requests.name), 
            )
            print(f"Created batch job from file: {batch_job.name}")
            
            self.batch_job = batch_job
            
        except Exception as e:
            print(f"파일 업로드 실패: {e}")
            raise e
    
    # def _create_batch_job(self, input_file_uri):
    #     """
    #     Batch 작업 생성
        
    #     Args:
    #         input_file_uri (str): 입력 파일 URI
            
    #     Returns:
    #         object: Batch 작업 객체
    #     """
    #     try:
    #         # Batch 작업 생성
    #         batch_job = genai.create_batch(
    #             input_file_uri=input_file_uri
    #         )
            
    #         print(f"✅ Batch 작업 생성: {batch_job.name}")
    #         return batch_job
            
    #     except Exception as e:
    #         print(f"🚨 Batch 작업 생성 실패: {e}")
    #         raise e
    
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
        
        return batch_job.state.name
        # waited_time = 0
        
        # while waited_time < max_wait_time:
        #     try:
        #         # 작업 상태 확인
        #         status = genai.get_batch(batch_job.name)
                
        #         if status.state == "COMPLETED":
        #             print("✅ Batch 작업 완료!")
        #             return status
        #         elif status.state == "FAILED":
        #             print("🚨 Batch 작업 실패!")
        #             return None
        #         else:
        #             print(f"🔄 진행 중... (상태: {status.state}, 대기시간: {waited_time}초)")
        #             time.sleep(check_interval)
        #             waited_time += check_interval
                    
        #     except Exception as e:
        #         print(f"🚨 상태 확인 실패: {e}")
        #         time.sleep(check_interval)
        #         waited_time += check_interval
        
        # print(f"⏰ 최대 대기 시간({max_wait_time}초) 초과")
        # return None
    
    # def _download_batch_results(self, completed_job):
    #     """
    #     Batch 작업 결과 다운로드 및 처리
        
    #     Args:
    #         completed_job: 완료된 Batch 작업
            
    #     Returns:
    #         list: 임베딩 벡터 리스트
    #     """
    #     try:
    #         # # 결과 파일 다운로드
    #         # output_file = genai.download_file(completed_job.output_file_uri)
            
    #         # embeddings = []
    #         # with open(output_file, 'r', encoding='utf-8') as f:
    #         #     for line in f:
    #         #         result = json.loads(line)
    #         #         if 'response' in result and 'embedding' in result['response']:
    #         #             embedding = result['response']['embedding']['values']
    #         #             embeddings.append(embedding)
    #         #         else:
    #         #             print(f"⚠️ 임베딩 실패 응답: {result.get('error', 'Unknown error')}")
    #         #             embeddings.append(None)
            
    #         # print(f"✅ {len([e for e in embeddings if e is not None]):,}개 임베딩 다운로드 완료")
    #         # return embeddings
    #         if completed_job.state.name == 'JOB_STATE_SUCCEEDED':
    #             # The output is in another file.
    #             result_file_name = completed_job.dest.file_name
    #             print(f"Results are in file: {result_file_name}")

    #             print("\nDownloading and parsing result file content...")
    #             file_content_bytes = self.gemini_client.files.download(file=result_file_name)
    #             file_content = file_content_bytes.decode('utf-8')

    #             # The result file is also a JSONL file. Parse and print each line.
    #             for line in file_content.splitlines():
    #                 if line:
    #                     parsed_response = json.loads(line)
    #                     # Pretty-print the JSON for readability
    #                     print(json.dumps(parsed_response, indent=2))
    #                     print("-" * 20)
    #         else:
    #             print(f"Job did not succeed. Final state: {completed_job.state.name}")

    #     except Exception as e:
    #         print(f"🚨 Batch 결과 다운로드 실패: {e}")
    #         return []

    def _download_and_store_embeddings(self, batch_df, embeddings, texts_to_embed):
        """
        임베딩을 ChromaDB에 저장
        
        Args:
            batch_df: 배치 데이터프레임
            embeddings: 임베딩 벡터 리스트
            texts_to_embed: 원본 텍스트 리스트
        """
        if self.batch_job.state.name == 'JOB_STATE_SUCCEEDED':
                # The output is in another file.
                result_file_name = self.batch_job.dest.file_name
                print(f"Results are in file: {result_file_name}")

                print("\nDownloading and parsing result file content...")
                file_content_bytes = self.gemini_client.files.download(file=result_file_name)
                file_content = file_content_bytes.decode('utf-8')
                
        else:
            print(f"Job did not succeed. Final state: {self.batch_job.state.name}")
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
                

        # None 값 제거 및 인덱스 정렬
        valid_data = []
        for i, (emb, text) in enumerate(zip(embeddings, texts_to_embed)):
            if emb is not None:
                valid_data.append((i, emb, text))
        
        if not valid_data:
            print("⚠️ 유효한 임베딩이 없습니다.")
            return
        
        try:
            # 유효한 데이터만 처리
            valid_indices = [idx for idx, _, _ in valid_data]
            valid_embeddings = [emb for _, emb, _ in valid_data]
            valid_texts = [text for _, _, text in valid_data]
            valid_batch_df = batch_df.iloc[valid_indices]
            
            # ChromaDB에 저장할 데이터 형식으로 변환
            ids = [f"news_{row['id']}" for index, row in valid_batch_df.iterrows()]
            metadatas = [
                {
                    "article_date": row['article_date'],
                    "title": row['title'][:500] if row['title'] else "",
                    "original_article_id": str(row['id'])
                }
                for index, row in valid_batch_df.iterrows()
            ]
            
            # ChromaDB에 데이터 추가 (청크 단위로 나누어 저장)
            storage_chunk_size = 1000
            
            for i in range(0, len(ids), storage_chunk_size):
                chunk_ids = ids[i:i+storage_chunk_size]
                chunk_embeddings = valid_embeddings[i:i+storage_chunk_size]
                chunk_documents = valid_texts[i:i+storage_chunk_size]
                chunk_metadatas = metadatas[i:i+storage_chunk_size]
                
                self.collection.upsert(
                    ids=chunk_ids,
                    embeddings=chunk_embeddings,
                    documents=chunk_documents,
                    metadatas=chunk_metadatas
                )
                
                print(f"  💾 저장 진행: {i+len(chunk_ids):,}/{len(ids):,}")
            
            print(f"✅ {len(valid_embeddings):,}개 임베딩 저장 완료")
            
        except Exception as e:
            print(f"🚨 ChromaDB 저장 실패: {e}")
    
    def embed_and_store_batch(self, start_date, end_date, chunk_size=10000, batch_size=50000):
        """
        Batch API를 사용한 대량 임베딩 및 저장
        
        Args:
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
            chunk_size (int): 데이터베이스 청크 크기
            batch_size (int): Batch API 배치 크기
        """
        print(f"\n🚀 Batch API를 사용하여 임베딩을 시작합니다...")
        print(f"📊 설정: DB 청크={chunk_size:,}, Batch 크기={batch_size:,}")
        
        all_data = []
        
        # 먼저 모든 데이터를 수집
        for chunk_df in self.load_data_chunked(start_date, end_date, chunk_size):
            all_data.append(chunk_df)
        
        if not all_data:
            print("⚠️ 처리할 데이터가 없습니다.")
            return
        
        # 모든 청크를 합치기
        full_df = pd.concat(all_data, ignore_index=True)
        print(f"📊 총 {len(full_df):,}개 문서를 Batch API로 처리합니다.")
        
        # 대용량 배치로 나누어 처리
        for i in range(0, len(full_df), batch_size):
            batch_df = full_df.iloc[i:i+batch_size]
            texts_to_embed = batch_df['full_text'].tolist()
            
            print(f"\n📦 배치 {i//batch_size + 1} 처리 중 ({len(texts_to_embed):,}개 문서)...")
            
            try:
                # 1. Batch 입력 파일 생성
                input_file_path = self._create_batch_input_file(
                    texts_to_embed, 
                    f"batch_{i//batch_size + 1}"
                )
                
                # 2. 파일 업로드
                uploaded_file = self._upload_batch_file(input_file_path)
                
                # 3. Batch 작업 생성
                batch_job = self._create_batch_job(uploaded_file.uri)
                
                # 4. 작업 완료 대기
                completed_job = self._wait_for_batch_completion(batch_job)
                
                if completed_job:
                    # 5. 결과 다운로드 및 처리
                    embeddings = self._download_batch_results(completed_job)
                    
                    if embeddings:
                        # 6. ChromaDB에 저장
                        self._store_embeddings(batch_df, embeddings, texts_to_embed)
                
                # 임시 파일 정리
                os.remove(input_file_path)
                
            except Exception as e:
                print(f"🚨 배치 {i//batch_size + 1} 처리 중 오류: {e}")
                continue
        
        print("\n🎉 모든 배치 처리 완료!")
        print(f"현재 '{self.collection_name}' 컬렉션에 저장된 총 데이터 수: {self.collection.count():,}개")
    
    def search_similar(self, query_text, n_results=5):
        """
        유사한 문서 검색
        
        Args:
            query_text (str): 검색할 쿼리 텍스트
            n_results (int): 반환할 결과 개수
        
        Returns:
            dict: 검색 결과
        """
        try:
            # 쿼리 임베딩
            query_result = genai.embed_content(
                model=self.embedding_model,
                content=[query_text],
                task_type="RETRIEVAL_QUERY"
            )
            query_embedding = query_result['embedding'][0]
            
            # 유사 문서 검색
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            return results
            
        except Exception as e:
            print(f"🚨 검색 중 에러 발생: {e}")
            return None
    
    def get_collection_info(self):
        """컬렉션 정보 반환"""
        if self.collection:
            return {
                "name": self.collection_name,
                "count": self.collection.count(),
                "path": self.chroma_path
            }
        return None
    
    def delete_collection(self):
        """컬렉션 삭제"""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"✅ '{self.collection_name}' 컬렉션이 삭제되었습니다.")
        except Exception as e:
            print(f"🚨 컬렉션 삭제 실패: {e}")

def main():
    """메인 실행 함수 (Batch API 전용)"""
    try:
        # Embedder 인스턴스 생성
        embedder = Embedder()
        
        # Batch API로 임베딩 및 저장
        embedder.embed_and_store_batch(
            start_date='2023-01-01',
            end_date='2024-12-31',
            chunk_size=10000,   # DB에서 한 번에 읽어올 문서 수
            batch_size=50000    # Batch API로 한 번에 처리할 문서 수
        )
        
        # 컬렉션 정보 출력
        info = embedder.get_collection_info()
        print(f"\n📊 컬렉션 정보: {info}")
        
        # 테스트 검색
        print("\n🔍 테스트 검색 수행...")
        results = embedder.search_similar("경제 뉴스", n_results=3)
        
        if results:
            print("검색 결과:")
            for i, doc in enumerate(results['documents'][0]):
                print(f"{i+1}. {doc[:100]}...")
        
    except Exception as e:
        print(f"🚨 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()