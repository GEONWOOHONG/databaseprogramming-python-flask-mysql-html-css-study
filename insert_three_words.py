import pymysql
import pandas as pd
import os

try:
    # 데이터베이스 연결
    db = pymysql.connect(
        host = "127.0.0.1",
        user = "root",
        password = "1234",
        db = "dbpDB",
        charset = "utf8mb4",
        autocommit = False
    )
    print("데이터베이스 연결 완료")

    # 커서 생성
    cur = db.cursor()

    try:
        # 폴더 경로 설정
        folder_path = "./data"

        # 폴더 내 파일 목록 확인 (확장자가 .xlsx인 파일만 포함)
        files = [f for f in os.listdir(folder_path) if f.endswith(".xlsx")]

        inserted_count = 0  # 삽입된 단어 개수 추적

        for file in files:
            file_path = f"{folder_path}/{file}"
            print(f"파일 처리 중: {file}")

            # 엑셀 파일 읽기 (첫 번째 열에 단어가 있다고 가정)
            df = pd.read_excel(file_path, header = None)

            # 단어 데이터 삽입
            for _, row in df.iterrows():
                word = row[0]  # 첫 번째 열에서 단어를 가져옴

                # 데이터 유효성 검사
                if not (isinstance(word, str) and len(word) == 3):  # 유효하지 않은 단어 건너뛰기
                    continue

                letter1, letter2, letter3 = word[0], word[1], word[2]

                insert_sql = """
                INSERT IGNORE INTO three_words (word, letter1, letter2, letter3)
                VALUES (%s, %s, %s, %s)
                """
                try:
                    cur.execute(insert_sql, (word, letter1, letter2, letter3))
                    inserted_count += cur.rowcount  # 실제 삽입된 행만 카운트
                except Exception as e:
                    print(f"단어 삽입 오류: {word}", e)

            # 각 파일 처리 후 커밋
            db.commit()
            print(f"파일 {file} 처리 완료")

        # 최종 삽입된 단어 개수 출력
        print(f"총 삽입된 단어 개수: {inserted_count}")

        # 테이블에 있는 총 단어 개수 출력
        cur.execute("SELECT COUNT(*) FROM three_words")
        print(f"테이블에 있는 총 단어 개수: {cur.fetchone()[0]}")

    except Exception as e:
        print("작업 중 오류 발생:", e)

        # 오류 발생 시 롤백
        db.rollback()
        print("변경 사항 복구 완료")

except pymysql.MySQLError as e:
    print("데이터베이스 연결 또는 작업 중 오류 발생:", e)

finally:
    # 연결 종료
    try:
        if cur:
            cur.close()
        if db:
            db.close()
        print("데이터베이스 연결 종료")
    except NameError:
        pass
