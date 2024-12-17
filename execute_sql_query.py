import pymysql

try:
    # 데이터베이스 연결
    db = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="1234",
        db="dbpDB",
        charset="utf8",
        autocommit=False
    )
    print("데이터베이스 연결 완료")

    # 커서 생성
    cur = db.cursor()

    three_words_table_query = """
        CREATE TABLE IF NOT EXISTS three_words (
        id INT AUTO_INCREMENT PRIMARY KEY, -- 단어 고유 ID
        word VARCHAR(10) NOT NULL,         -- 단어
        letter1 VARCHAR(5) NOT NULL,       -- 첫 번째 글자
        letter2 VARCHAR(5) NOT NULL,       -- 두 번째 글자
        letter3 VARCHAR(5) NOT NULL        -- 세 번째 글자
        );
    """
    
    # users 테이블 생성 쿼리
    users_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY, -- 사용자 고유 ID
            nickname VARCHAR(20) NOT NULL,     -- 닉네임
            username VARCHAR(20) UNIQUE NOT NULL, -- 사용자 아이디
            password VARCHAR(255) NOT NULL     -- 비밀번호 (암호화 가능)
        );
    """

    # user_scores 테이블 생성 쿼리
    user_scores_table_query = """
        CREATE TABLE IF NOT EXISTS user_scores (
            user_id INT NOT NULL,              -- 사용자 고유 ID (users 테이블의 id와 연관)
            char_score JSON NOT NULL,          -- 글자와 점수를 JSON 형식으로 저장
            PRIMARY KEY (user_id),             -- user_id를 Primary Key로 설정
            FOREIGN KEY (user_id) REFERENCES users(id) -- users 테이블의 id와 연결
        );
    """
    
    try:
        # three_words 테이블 생성
        cur.execute(three_words_table_query)
        print("three_words 테이블 생성 완료")

        # users 테이블 생성
        cur.execute(users_table_query)
        print("users 테이블 생성 완료")

        # user_scores 테이블 생성
        cur.execute(user_scores_table_query)
        print("user_scores 테이블 생성 완료")

        # 커밋
        db.commit()
        print("데이터베이스 커밋 완료")

    except Exception as e:
        print("작업 중 오류 발생: ", e)

        # 오류 발생 시 롤백
        db.rollback()
        print("변경 사항 복구 완료")

except pymysql.MySQLError as e:
    print("데이터베이스 연결 또는 작업 중 오류 발생: ", e)

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