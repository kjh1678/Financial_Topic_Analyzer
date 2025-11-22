import sqlite3

# 데이터베이스 경로 설정
NEWS_DB_PATH = 'data/news.db'
CLUSTER_DB_PATH = 'data/cluster.db'

def get_cluster_counts(start_date, end_date):
    """
    articles 테이블에서 기간 내 cluster_id별 기사 수를 가져옵니다.
    (토픽 병합 없이 ID별로 Grouping)
    """
    data = []
    conn = sqlite3.connect(NEWS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 기사 날짜 기간으로 필터링하여 cluster_id별 개수 집계
        # 개수가 많은 순서대로 정렬 (ORDER BY COUNT(*) DESC)
        query = """
            SELECT cluster_id, COUNT(*) 
            FROM articles 
            WHERE article_date BETWEEN ? AND ? 
            GROUP BY cluster_id
            ORDER BY COUNT(*) DESC
        """
        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        
        for r in rows:
            if r[0]: # cluster_id가 존재하는 경우만
                data.append((r[0], r[1]))
                
    except sqlite3.Error as e:
        print(f"News DB Error: {e}")
    finally:
        conn.close()
        
    return data

def get_cluster_details(cluster_ids):
    """
    cluster_id 리스트를 받아 cluster.db에서 topic과 keywords를 조회합니다.
    """
    info_map = {}
    if not cluster_ids:
        return info_map
        
    conn = sqlite3.connect(CLUSTER_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # IN 절을 사용하여 한 번에 조회
        placeholders = ','.join(['?'] * len(cluster_ids))
        query = f"SELECT id, topic, keywords FROM clusters WHERE id IN ({placeholders})"
        cursor.execute(query, cluster_ids)
        
        rows = cursor.fetchall()
        for r in rows:
            c_id, topic, keywords = r
            info_map[c_id] = {
                'topic': topic if topic else "Unknown",
                'keywords': keywords if keywords else ""
            }
            
    except sqlite3.Error as e:
        print(f"Cluster DB Error: {e}")
    finally:
        conn.close()
        
    return info_map

def main():
    # 1. 사용자 입력 (원하시는 날짜로 수정해서 쓰시면 됩니다)
    start_date = "2024-12-04"
    end_date = "2024-12-04"
    
    print(f"\nFetching articles from {start_date} to {end_date}...\n")
    
    # 2. News DB에서 ID별 개수 가져오기
    # raw_data 형태: [('1-0-2', 15), ('2-1', 10), ...]
    raw_data = get_cluster_counts(start_date, end_date)
    
    if not raw_data:
        print("해당 기간에 조회된 기사가 없습니다.")
        return

    # 3. Cluster DB에서 상세 정보(Topic, Keywords) 가져오기
    all_ids = [item[0] for item in raw_data]
    details_map = get_cluster_details(all_ids)
    
    # 4. 결과 출력 (합치기 없이 ID별로 출력)
    print(f"{'Cluster ID':<15} | {'Count':<6} | {'Topic':<30} | {'Keywords'}")
    print("="*120)
    
    total_articles = 0
    
    for c_id, count in raw_data:
        info = details_map.get(c_id, {'topic': 'Unknown', 'keywords': ''})
        topic = info['topic']
        keywords = info['keywords']
        
        print(f"{c_id:<15} | {count:<6} | {topic:<30} | {keywords}")
        total_articles += count
        
    print("="*120)
    print(f"총 {len(raw_data)}개의 클러스터 ID 조회됨 (총 기사 수: {total_articles})")

if __name__ == "__main__":
    main()