import chromadb
import numpy as np
from sklearn.decomposition import PCA
import pickle
import os
from tqdm import tqdm
from datetime import datetime, timedelta

# ==========================================
# 1. 환경 설정 (파일명 및 경로)
# ==========================================
PERSISTENT_PATH = "data/embedding_db"
SOURCE_COL_NAME = "news_articles_v1"        # 원본 데이터 있는 곳
TARGET_COL_NAME = "reduced_emb"   # 20차원 데이터 넣을 곳
MODEL_FILENAME = "pca_model_master.pkl"        # pca 모델 파일 이름

# 작업할 데이터의 날짜 범위 (예시: 이번 달 데이터 추가)
# * 주의: 맨 처음 실행할 때는 데이터가 20개 이상이어야 합니다.
START_DATE = "2024-11-20"
END_DATE = "2025-11-18"


# ==========================================
# 2. 데이터 가져오기 (Source)
# ==========================================
client = chromadb.PersistentClient(path=PERSISTENT_PATH)
source_collection = client.get_collection(SOURCE_COL_NAME)

print(f"🔍 '{SOURCE_COL_NAME}'에서 데이터 검색 중 ({START_DATE} ~ {END_DATE})...")

def generate_date_range(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    date_list = []
    
    curr = start
    while curr <= end:
        date_list.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return date_list

# 기간 내의 모든 날짜를 리스트로 만듦 (예: ['2025-08-01', '2025-08-02'])
target_dates = generate_date_range(START_DATE, END_DATE)

print(f"   -> 검색 대상 날짜: {target_dates}")

# 필터 조건: article_date가 target_dates 리스트 안에 있는 경우만 가져옴
filter_condition = {
    "article_date": {
        "$in": target_dates
    }
}


data = source_collection.get(
    where=filter_condition,
    include=["embeddings", "metadatas"] 
)

ids = data["ids"]
embeddings = data["embeddings"]
metadatas = data["metadatas"]

count = len(ids)
print(f"✅ 처리할 데이터 개수: {count}개")

if count == 0:
    print("⚠️ 데이터가 없습니다. 프로그램을 종료합니다.")
    exit()

# ==========================================
# 3. PCA 모델 로드 또는 생성 (핵심 로직)
# ==========================================
reduced_embeddings = []

# [케이스 1] 모델 파일이 이미 존재하는 경우 -> "불러와서 쓰기"
if os.path.exists(MODEL_FILENAME):
    print(f"📂 기존 모델 파일({MODEL_FILENAME})을 발견했습니다.")
    print("   👉 기존 모델을 불러와서 '변환(Transform)'만 수행합니다.")
    
    # 1. 모델 로드
    with open(MODEL_FILENAME, "rb") as f:
        pca = pickle.load(f)
    
    # 2. 변환 (절대 fit하지 않음)
    reduced_embeddings_np = pca.transform(embeddings)
    reduced_embeddings = reduced_embeddings_np.tolist()
    
    # 3. 타겟 컬렉션 가져오기 (기존 것 사용)
    # 만약 컬렉션이 없으면 만드는 get_or_create 사용
    target_collection = client.get_or_create_collection(
        name=TARGET_COL_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    print("   👉 기존 컬렉션에 데이터를 추가(Append)합니다.")

# [케이스 2] 모델 파일이 없는 경우 -> "처음이니 새로 만들기"
else:
    print(f"🆕 모델 파일({MODEL_FILENAME})이 없습니다.")
    print("   👉 PCA 모델을 새로 학습(Fit)하고 저장합니다.")
    
    if count < 20:
        raise ValueError(f"데이터가 {count}개뿐이라 20차원 학습이 불가능합니다. 데이터를 더 확보하세요.")

    # 1. 학습 및 변환
    pca = PCA(n_components=20)
    reduced_embeddings_np = pca.fit_transform(embeddings)
    reduced_embeddings = reduced_embeddings_np.tolist()
    
    # 2. 모델 저장
    with open(MODEL_FILENAME, "wb") as f:
        pickle.dump(pca, f)
    print(f"   💾 새 모델이 '{MODEL_FILENAME}'로 저장되었습니다.")
    
    # 3. 타겟 컬렉션 새로 만들기 (혹시 기존에 찌꺼기가 있다면 초기화)
    try:
        client.delete_collection(TARGET_COL_NAME)
        print(f"   🗑️ 기존 '{TARGET_COL_NAME}' 컬렉션을 초기화했습니다.")
    except:
        pass
        
    target_collection = client.create_collection(
        name=TARGET_COL_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    print("   👉 새 컬렉션을 생성하고 데이터를 입력합니다.")

# ==========================================
# 4. 데이터 저장 (Batch Processing)
# ==========================================
BATCH_SIZE = 5000
print(f"\n📥 DB 저장 시작 (총 {count}건, 배치 크기 {BATCH_SIZE})...")

for i in tqdm(range(0, count, BATCH_SIZE), desc="Inserting"):
    end_idx = min(i + BATCH_SIZE, count)
    
    target_collection.add(
        ids=ids[i:end_idx],
        embeddings=reduced_embeddings[i:end_idx],
        metadatas=metadatas[i:end_idx]
        
    )

print(f"\n🎉 모든 작업 완료! ('{TARGET_COL_NAME}' 컬렉션 확인)")