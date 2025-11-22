import sqlite3
import json
import time
import os
from google import genai
from google.genai import types

# ==========================================
# 1. 설정 및 데이터베이스 연결
# ==========================================
# API 키 입력
API_KEY = "AIzaSyCeTC1TeKmmQtk16PnEtf469Q2nkgGt2MA"  # 실제 키로 교체해주세요
client = genai.Client(api_key=API_KEY)

# 파일 경로 설정
DB_CLUSTER_PATH = "data/cluster.db"
DB_NEWS_PATH = "data/news.db"
BATCH_INPUT_FILE = "tempfile/cluster_topic_input.jsonl"
BATCH_OUTPUT_FILE = "tempfile/cluster_topic_output.jsonl"

# 프롬프트 설정
refined_system_prompt = """Analyze the given news article titles to extract frequently appearing core keywords and formulate a core topic as a cohesive noun phrase based on them.
Constraints:
The output must be in Korean language.
Do not include any introductory text, explanations, or markdown formatting.
Exclude all particles (josa) and predicates; construct the topic strictly as a noun-based phrase (e.g., 'Samsung Electronics semiconductor investment expansion').
**IMPORTANT: Do not simply list or enumerate keywords; synthesize them into a single, coherent compound noun phrase representing the overall meaning.**"""


# ==========================================
# 2. 데이터 추출 및 전처리 (DB -> Memory)
# ==========================================
print("1. 데이터베이스에서 데이터 추출 중...")

conn_cluster = sqlite3.connect(DB_CLUSTER_PATH)
cursor_cluster = conn_cluster.cursor()
cursor_cluster.execute("SELECT id, samples FROM clusters")
cluster_rows = cursor_cluster.fetchall()

conn_news = sqlite3.connect(DB_NEWS_PATH)
cursor_news = conn_news.cursor()

batch_request_data = []

for row in cluster_rows:
    cluster_id = row[0]
    samples_str = row[1]
    
    try:
        article_ids = json.loads(samples_str)
        if not article_ids: continue
            
        placeholders = ','.join('?' for _ in article_ids)
        query = f"SELECT title FROM articles WHERE id IN ({placeholders})"
        
        cursor_news.execute(query, article_ids)
        titles_rows = cursor_news.fetchall()
        titles = [t[0] for t in titles_rows]
        
        if titles:
            batch_request_data.append({
                "cluster_id": cluster_id,
                "titles": titles
            })
    except Exception:
        continue

conn_news.close()
conn_cluster.close()
print(f"   -> 총 {len(batch_request_data)}개의 클러스터 데이터를 준비했습니다.")

# ==========================================
# 3. JSONL 파일 생성
# ==========================================
print(f"2. 배치 입력 파일 생성 중... ({BATCH_INPUT_FILE})")

with open(BATCH_INPUT_FILE, "w", encoding="utf-8") as f:
    for data in batch_request_data:
        content_text = "\n".join(data["titles"])
        
        request_object = {
            "custom_id": str(data["cluster_id"]),
            "request": {
                "system_instruction": {
                    "parts": [{"text": refined_system_prompt}]
                },
                "contents": [
                    {"parts": [{"text": content_text}]}
                ]
            }
        }
        f.write(json.dumps(request_object, ensure_ascii=False) + "\n")

# ==========================================
# 4. Batch API 작업 실행
# ==========================================
print("3. 파일 업로드 및 배치 작업 시작...")

# 파일 업로드
upload_file = client.files.upload(
    file=BATCH_INPUT_FILE, 
    config={"mime_type": "application/json"}
)
print(f"   -> 파일 업로드 완료: {upload_file.name}")

# 배치 작업 생성
batch_job = client.batches.create(
    model="gemini-2.5-flash-lite",
    src=upload_file.name,
    config=types.CreateBatchJobConfig(
        display_name="cluster_topic_labeling"
    )
)

print(f"   -> 작업 ID: {batch_job.name}")

# ==========================================
# 5. 대기 (요청하신 1번 로직 유지)
# ==========================================
print("4. 작업 완료 대기 중...")

while True:
    # 상태 업데이트
    batch_job = client.batches.get(name=batch_job.name)
    
    if batch_job.state.name in ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED'):
        break
    
    print(f"Job not finished. Current state: {batch_job.state.name}. Waiting 30 seconds...")
    time.sleep(30)

# ==========================================
# 6. 결과 다운로드 (수정된 2번 로직)
# ==========================================
if batch_job.state.name == "JOB_STATE_SUCCEEDED":
    print(f"\n5. 결과 파일 확인 및 다운로드...")
    
    target_file_name = None
    
    # 1. dest 속성 확인 (우선순위)
    if hasattr(batch_job, 'dest') and batch_job.dest and batch_job.dest.file_name:
        target_file_name = batch_job.dest.file_name
        
    # 2. output_uri 속성 확인 (백업)
    elif hasattr(batch_job, 'output_uri') and batch_job.output_uri:
        target_file_name = batch_job.output_uri
        if "/files/" in target_file_name:
            target_file_name = "files/" + target_file_name.split("/files/")[-1]

    if target_file_name:
        print(f"   -> 다운로드 경로: {target_file_name}")
        
        try:
            # [핵심 수정] content() 대신 download() 사용, 파라미터는 name=
            content = client.files.download(file=target_file_name)
    
            with open(BATCH_OUTPUT_FILE, "wb") as f:
                f.write(content)
            print(f"   -> 다운로드 완료! ({BATCH_OUTPUT_FILE})")
            
        except Exception as e:
            print(f"   -> [에러] 파일 다운로드 중 문제 발생: {e}")
            # 만약 SDK download 메서드도 실패할 경우를 대비한 HTTP 요청 방식 (주석 처리)
            # import requests
            # url = f"https://generativelanguage.googleapis.com/v1beta/{target_file_name}"
            # resp = requests.get(url, headers={"x-goog-api-key": API_KEY})
            # if resp.status_code == 200:
            #     with open(BATCH_OUTPUT_FILE, "wb") as f:
            #         f.write(resp.content)
            #     print("   -> (HTTP 요청으로 다운로드 성공)")
            # else:
            #     print(f"   -> HTTP 요청 실패: {resp.status_code} {resp.text}")
            exit()
            
    else:
        print("\n[에러] 완료되었으나 결과 파일 경로(dest.file_name)를 찾을 수 없습니다.")
        print("--- Batch Job 객체 정보 ---")
        print(batch_job)
        exit()

else:
    print(f"작업이 성공하지 못했습니다. 상태: {batch_job.state.name}")
    exit()

# ==========================================
# 7. 결과 파싱 및 DB 업데이트
# ==========================================
print("6. DB 업데이트 시작 (clusters 테이블 topic 컬럼)...")

conn_cluster = sqlite3.connect(DB_CLUSTER_PATH)
cursor_cluster = conn_cluster.cursor()

update_count = 0

if os.path.exists(BATCH_OUTPUT_FILE):
    with open(BATCH_OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                res = json.loads(line)
                
                c_id = res.get('custom_id')
                
                if 'response' in res and 'candidates' in res['response']:
                    generated_topic = res['response']['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    cursor_cluster.execute(
                        "UPDATE clusters SET topic = ? WHERE id = ?", 
                        (generated_topic, c_id)
                    )
                    update_count += 1
                else:
                    # 에러 응답 등은 패스
                    pass
                    
            except Exception as e:
                print(f"   -> 처리 중 에러 발생: {e}")

    conn_cluster.commit()
    conn_cluster.close()
    print(f"\n[완료] 총 {update_count}개의 클러스터 토픽이 업데이트되었습니다.")
else:
    print(f"[에러] 결과 파일이 없어 업데이트를 진행하지 못했습니다.")