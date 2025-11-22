import chromadb
import json
import numpy as np
import math

# --- 1. 설정 (사용자 변경 필요) ---
CHROMA_DB_PATH = 'data/embedding_db'
COLLECTION_NAME = 'reduced_emb'
OUTPUT_JSON_PATH = 'chromadb_export.json'
CHUNK_SIZE = 1000

# --- 2. 사용자 정의 JSON 인코더 (NumPy 배열 처리용) ---
class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

# --- 3. 메인 로직 ---
def export_collection_to_json():
    print("ChromaDB에 연결 중...")
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        print(f"'{COLLECTION_NAME}' 컬렉션을 성공적으로 불러왔습니다.")
    except Exception as e:
        print(f"오류: ChromaDB에 연결하거나 컬렉션을 불러올 수 없습니다. {e}")
        return

    total_count = collection.count()
    if total_count == 0:
        print("컬렉션에 데이터가 없습니다. 프로그램을 종료합니다.")
        return
        
    print(f"총 {total_count:,}개의 데이터를 내보냅니다. 청크 크기: {CHUNK_SIZE:,}")

    all_data = []
    num_batches = math.ceil(total_count / CHUNK_SIZE)

    try:
        for i in range(num_batches):
            offset = i * CHUNK_SIZE
            print(f"데이터 가져오는 중... ({i+1}/{num_batches} 배치, offset: {offset})")
            
            chunk = collection.get(
                limit=CHUNK_SIZE,
                offset=offset,
                include=["metadatas"]
            )

            num_items_in_chunk = len(chunk['ids'])
            for j in range(num_items_in_chunk):
                # ★★★★★★★★★★★★★★★★★
                # 오류가 수정된 부분
                # ★★★★★★★★★★★★★★★★★
                item = {
                    'id': chunk['ids'][j],
                    'metadata': chunk['metadatas'][j],
                    
                }
                all_data.append(item)
        
        print("\n모든 데이터를 성공적으로 메모리로 불러왔습니다.")
        print("JSON 파일로 저장하는 중...")

        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False, cls=NumpyArrayEncoder)

        print(f"\n완료! 모든 데이터가 '{OUTPUT_JSON_PATH}' 파일에 성공적으로 저장되었습니다.")

    except Exception as e:
        print(f"\n데이터 처리 또는 파일 저장 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    export_collection_to_json()