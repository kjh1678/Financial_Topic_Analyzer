import chromadb
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, pairwise_distances_argmin_min
from sklearn.metrics.pairwise import cosine_distances
import sys
import sqlite3
import json
import os
from datetime import datetime, timedelta
import random
from sklearn.preprocessing import normalize

# ==============================================================================
# 1. 글로벌 설정
# ==============================================================================
STOP_THRESHOLD_CH = 30.0
MIN_CLUSTER_SIZE = 50
MERGE_THRESHOLD = 0.15
sys.setrecursionlimit(5000)

PERSISTENT_PATH = "data/embedding_db"
TARGET_COL_NAME = "reduced_emb"
CLUSTER_DB_PATH = "data/cluster.db"
NEWS_DB_PATH = "data/news.db" 

os.makedirs("data", exist_ok=True)

START_DATE = "2024-11-20"
END_DATE = "2025-11-18"

# ==============================================================================
# 2. 클러스터 DB 초기화
# ==============================================================================
def init_cluster_db():
    conn = sqlite3.connect(CLUSTER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS clusters")
    # [수정] keywording_samples 컬럼 삭제
    cursor.execute('''
        CREATE TABLE clusters (
            id TEXT PRIMARY KEY,
            depth INTEGER,
            ch_score REAL,
            size INTEGER,
            reason TEXT,
            samples TEXT,
            is_leaf INTEGER,
            topic TEXT,
            keywords TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"1. 클러스터 DB 초기화 완료")

init_cluster_db()

# ==============================================================================
# 3. 데이터 로드
# ==============================================================================
client = chromadb.PersistentClient(path=PERSISTENT_PATH)
collection = client.get_collection(TARGET_COL_NAME)

print(f"2. 데이터 로드 중... ({START_DATE} ~ {END_DATE})")

def generate_date_range(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    date_list = []
    curr = start
    while curr <= end:
        date_list.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return date_list

target_dates = generate_date_range(START_DATE, END_DATE)
filter_condition = { "article_date": { "$in": target_dates } }

data = collection.get(where=filter_condition, include=["embeddings"])
ids = np.array(data["ids"])
raw_embeddings = np.array(data["embeddings"])
# 정규화
embeddings = normalize(raw_embeddings, axis=1, norm='l2')
n_samples = len(ids)

print(f"   -> 데이터 개수: {n_samples}개")
if n_samples < MIN_CLUSTER_SIZE:
    print("❌ 데이터 부족")
    exit()

# ==============================================================================
# 4. 헬퍼 함수
# ==============================================================================
def get_dynamic_k_range(n_curr):
    min_k = 2
    if n_curr >= 50000: max_k = 30
    elif n_curr >= 10000: max_k = 20
    elif n_curr >= 5000: max_k = 15
    elif n_curr >= 1000: max_k = 10
    elif n_curr >= 100: max_k = 5
    else: max_k = 3
    return min_k, max_k

def get_sample_count_by_size(size):
    if size < 100: return 40
    if size < 1000: return 70
    if size < 5000: return 100
    return 150

# [수정] keywording_samples 관련 인자 및 SQL 제거
def insert_cluster_to_db(conn, info):
    cursor = conn.cursor()
    samples_json = json.dumps(info['samples'], ensure_ascii=False)
    
    cursor.execute('''
        INSERT INTO clusters (id, depth, ch_score, size, reason, samples, is_leaf)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        info['id'],
        info['depth'],
        info['ch_score'],
        info['size'],
        info['reason'],
        samples_json,
        info['is_leaf']
    ))
    conn.commit()

# ==============================================================================
# 5. 재귀 클러스터링 엔진
# ==============================================================================
conn_cluster = sqlite3.connect(CLUSTER_DB_PATH)
leaf_article_mappings = []
leaf_centroids = {} 

def recursive_clustering(curr_ids, curr_embs, depth, path_str, inherited_score):
    n_curr = len(curr_ids)
    
    # 중심점 계산
    centroid = np.mean(curr_embs, axis=0).reshape(1, -1)
    closest_idx, _ = pairwise_distances_argmin_min(centroid, curr_embs)
    center_id = curr_ids[closest_idx[0]]
    
    # 일반 샘플 추출
    candidates = [x for x in curr_ids if x != center_id]
    target_count = get_sample_count_by_size(n_curr)
    pick_count = min(len(candidates), target_count -1)
    random_samples = random.sample(candidates, pick_count)
    final_samples = [center_id] + random_samples

    # 저장 헬퍼 
    def save_current_node(reason, is_leaf_flag):
        # [수정] keywording_samples 생성 로직 제거
        if is_leaf_flag == 1:
            leaf_centroids[path_str] = centroid[0]

        insert_cluster_to_db(conn_cluster, {
            "id": path_str,
            "depth": depth,
            "ch_score": inherited_score,
            "size": n_curr,
            "reason": reason,
            "samples": final_samples,
            "is_leaf": is_leaf_flag
            # keywording_samples 필드 제거
        })

        if is_leaf_flag == 1:
            for article_id in curr_ids:
                leaf_article_mappings.append([path_str, article_id])

    # [STOP] 사이즈 미달
    if n_curr < MIN_CLUSTER_SIZE:
        save_current_node(f"Size Limit (<{MIN_CLUSTER_SIZE})", 1)
        return

    # [PROCESS] K 탐색
    min_k, max_k = get_dynamic_k_range(n_curr)
    real_max_k = min(max_k, int(np.sqrt(n_curr)))
    
    if real_max_k < 2:
        save_current_node("Cannot Split", 1)
        return

    next_best_k = 2
    next_best_model = None
    next_best_score = -1.0

    for k in range(min_k, real_max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=3)
        labels = kmeans.fit_predict(curr_embs)
        if len(np.unique(labels)) < 2: continue
        score = calinski_harabasz_score(curr_embs, labels)
        if score > next_best_score:
            next_best_score = score
            next_best_k = k
            next_best_model = kmeans

    # [STOP] 모델 실패
    if next_best_model is None:
        save_current_node("Fit Failed", 1)
        return

    # [STOP] 다음 분할 점수 미달
    if next_best_score < STOP_THRESHOLD_CH:
        save_current_node(f"Next Split Low ({next_best_score:.1f})", 1)
        return

    # [GO] 분할 성공 (Branch)
    if depth < 2:
        print(f"{'  ' * depth}↳ [{path_str}] Split:{next_best_k} (New Score:{next_best_score:.1f})")

    save_current_node("Split", 0)
    
    child_labels = next_best_model.labels_
    for i in range(next_best_k):
        mask = (child_labels == i)
        child_ids = curr_ids[mask]
        child_embs = curr_embs[mask]
        if len(child_ids) == 0: continue
        
        next_path = f"{i}" if path_str == "Root" else f"{path_str}-{i}"
        
        recursive_clustering(child_ids, child_embs, depth + 1, next_path, float(next_best_score))

# ==============================================================================
# 6. 실행
# ==============================================================================
print(f"\n3. 재귀 클러스터링 시작 (점수 상속 모드)...\n")
recursive_clustering(ids, embeddings, 0, "Root", 0.0)
print("\n   -> 기본 클러스터링 완료. 병합 전처리 대기 중...")

# ==============================================================================
# [NEW] 6-1. 유사 리프 클러스터 병합 (Post-Processing)
# ==============================================================================
def merge_similar_leaves():
    """
    유사도가 높은 리프 클러스터들을 찾아 하나로 병합합니다.
    """
    global leaf_article_mappings
    
    cluster_ids = list(leaf_centroids.keys())
    if len(cluster_ids) < 2:
        return

    print(f"\n3-1. 리프 클러스터 유사도 검사 및 병합 시작 (Threshold: {MERGE_THRESHOLD})...")
    
    # 1. 거리 행렬 계산
    vectors = np.array([leaf_centroids[cid] for cid in cluster_ids])
    dist_matrix = cosine_distances(vectors) 
    
    # 2. 그룹핑 (BFS로 연결된 컴포넌트 찾기)
    n = len(cluster_ids)
    visited = [False] * n
    groups = []
    
    for i in range(n):
        if not visited[i]:
            queue = [i]
            visited[i] = True
            current_group = [i]
            
            while queue:
                curr_idx = queue.pop(0)
                neighbors = np.where(dist_matrix[curr_idx] < MERGE_THRESHOLD)[0]
                
                for neighbor_idx in neighbors:
                    if not visited[neighbor_idx]:
                        visited[neighbor_idx] = True
                        current_group.append(neighbor_idx)
                        queue.append(neighbor_idx)
            
            groups.append(current_group)

    # 3. 병합 처리
    merge_count = 0
    cursor = conn_cluster.cursor()
    
    for group_indices in groups:
        if len(group_indices) < 2:
            continue
            
        merge_count += 1
        group_cids = [cluster_ids[idx] for idx in group_indices]
        
        representative_id = group_cids[0]
        merged_ids = group_cids[1:] 
        
        print(f"   -> 병합 그룹 발생: {representative_id} <= {merged_ids}")
        
        # DB에서 정보 가져와서 합치기
        total_size = 0
        all_samples = []
        
        # [수정] keywording_samples 조회 및 처리 로직 삭제
        placeholders = ','.join(['?'] * len(group_cids))
        cursor.execute(f"SELECT id, size, samples FROM clusters WHERE id IN ({placeholders})", group_cids)
        rows = cursor.fetchall()
        
        for r in rows:
            cid, size, samples_str = r
            total_size += size
            
            try:
                s_list = json.loads(samples_str)
                all_samples.extend(s_list)
            except: pass

        # [수정] samples 개수를 get_sample_count_by_size 함수로 결정
        target_sample_count = get_sample_count_by_size(total_size)
        all_samples = list(set(all_samples))[:target_sample_count]
        
        # 병합된 멤버들 DB에서 제거
        cursor.execute(f"DELETE FROM clusters WHERE id IN ({placeholders})", group_cids)
        
        # 대표 ID로 새 레코드 삽입
        reason_text = f"Merged {len(group_cids)} clusters (Threshold {MERGE_THRESHOLD})"
        
        # [수정] INSERT문에서 keywording_samples 삭제
        cursor.execute('''
            INSERT INTO clusters (id, depth, ch_score, size, reason, samples, is_leaf)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            representative_id, 
            999, 
            0.0, 
            total_size, 
            reason_text, 
            json.dumps(all_samples, ensure_ascii=False), 
            1
        ))
        
        # 매핑 정보 업데이트
        target_ids_set = set(merged_ids)
        for i in range(len(leaf_article_mappings)):
            if leaf_article_mappings[i][0] in target_ids_set:
                leaf_article_mappings[i][0] = representative_id

    conn_cluster.commit()
    print(f"   -> 총 {merge_count}개의 그룹이 병합되었습니다.")

merge_similar_leaves()

conn_cluster.close()
print("\n✅ 클러스터링 및 병합 완료, cluster.db 저장 끝.")


# ==============================================================================
# 7. News DB 업데이트
# ==============================================================================
def update_news_db_final():
    print(f"\n4. News DB ({NEWS_DB_PATH}) 업데이트 시작...")
    
    if not os.path.exists(NEWS_DB_PATH):
        print(f"❌ 오류: {NEWS_DB_PATH} 파일이 없습니다.")
        return

    if not leaf_article_mappings:
        print("⚠️ 업데이트할 매핑 정보가 없습니다.")
        return

    conn_news = sqlite3.connect(NEWS_DB_PATH)
    cursor = conn_news.cursor()

    try:
        cursor.execute("PRAGMA table_info(articles)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "cluster_id" not in columns:
            print("   -> 'cluster_id' 컬럼 생성 중...")
            cursor.execute("ALTER TABLE articles ADD COLUMN cluster_id TEXT")
        
        print(f"   -> 총 {len(leaf_article_mappings)}건의 기사 매핑 정보를 저장합니다...")
        
        cursor.executemany(
            "UPDATE articles SET cluster_id = ? WHERE id = ?", 
            leaf_article_mappings
        )
        
        conn_news.commit()
        print("✅ News DB 업데이트 최종 완료.")
        
    except Exception as e:
        print(f"❌ DB 업데이트 실패: {e}")
    finally:
        conn_news.close()

update_news_db_final()