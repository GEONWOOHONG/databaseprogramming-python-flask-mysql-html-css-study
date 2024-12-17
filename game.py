from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import pymysql
import random
import time
import json

# 블루프린트 정의
game_blueprint = Blueprint("game", __name__)

# MySQL 연결 설정
def get_db_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="1234",
        db="dbpDB",
        charset="utf8mb4"
    )

# 글로벌 변수
random_words = []  # 랜덤으로 가져온 단어들
current_index = 0  # 현재 단어 인덱스
start_time = 0  # 시작 시간
total_correct = []  # 각 단어별 글자 맞춤 여부
total_characters = 0  # 총 입력한 글자 수

# 자주 틀리는 글자 기반 단어와 랜덤 단어 생성 함수
def generate_words(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 사용자 스코어 가져오기
        cursor.execute("SELECT char_score FROM user_scores WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        frequent_words = set()
        if result:
            char_score = json.loads(result[0])

            # 음수 스코어가 있는 글자만 정렬
            low_score_chars = sorted(
                [char for char, score in char_score.items() if score < 0],
                key=lambda x: char_score[x]
            )[:4]  # 상위 4개 글자만 선택

            # 각 상위 글자별 최대 3개의 단어 가져오기
            for char in low_score_chars:
                cursor.execute("""
                    SELECT DISTINCT word 
                    FROM three_words 
                    WHERE letter1 = %s OR letter2 = %s OR letter3 = %s 
                    LIMIT 3
                """, (char, char, char))
                words = [row[0] for row in cursor.fetchall()]
                frequent_words.update(words)

            # 부족한 단어를 다른 상위 글자에서 가져오기
            for char in low_score_chars:
                while len(frequent_words) < 12:
                    cursor.execute("""
                        SELECT DISTINCT word 
                        FROM three_words 
                        WHERE (letter1 = %s OR letter2 = %s OR letter3 = %s) 
                        AND word NOT IN %s
                        LIMIT 1
                    """, (char, char, char, tuple(frequent_words) if frequent_words else ("",)))
                    word = cursor.fetchone()
                    if word:
                        frequent_words.add(word[0])
                    else:
                        break  # 더 이상 가져올 단어가 없으면 종료

        # 상위 글자에 포함되지 않는 랜덤 단어 8개 가져오기
        excluded_words = tuple(frequent_words) if frequent_words else ("",)
        cursor.execute("""
            SELECT DISTINCT word 
            FROM three_words 
            WHERE word NOT IN %s 
            ORDER BY RAND() 
            LIMIT 8
        """, (excluded_words,))
        random_words = [row[0] for row in cursor.fetchall()]

        # 스코어가 없는 경우: 랜덤 단어 20개 가져오기
        if not frequent_words:
            cursor.execute("SELECT word FROM three_words ORDER BY RAND() LIMIT 20")
            frequent_words.update(row[0] for row in cursor.fetchall())
            random_words = []

    finally:
        connection.close()

    # 최종 단어 리스트: 12개 단어 + 8개 랜덤 단어
    final_words = list(frequent_words)[:12] + random_words
    random.shuffle(final_words)  # 섞어서 반환
    return final_words

# 게임 메인 페이지
@game_blueprint.route("/index", methods=["GET", "POST"])
def index():
    global random_words, current_index, start_time, total_correct, total_characters

    if "user_id" not in session:
        return redirect(url_for("login"))  # 로그인하지 않은 경우 로그인 페이지로 이동

    if request.method == "POST":
        if "start_game" in request.form:
            user_id = session["user_id"]
            random_words = generate_words(user_id)

            current_index = 0
            start_time = time.time()  # 게임 시작 시간 기록
            total_correct = []
            total_characters = 0
            return redirect(url_for("game.play_game"))

    return render_template("index.html", nickname=session.get("nickname"))

# 게임 진행 페이지
@game_blueprint.route("/play", methods=["GET"])
def play_game():
    global random_words, current_index, start_time, total_correct, total_characters

    if "user_id" not in session:
        return redirect(url_for("login"))

    if current_index >= len(random_words):
        return redirect(url_for("game.results_page"))

    current_word = random_words[current_index]
    elapsed_time = int(time.time() - start_time)
    accuracy = (sum([sum(word) for word in total_correct]) / total_characters) * 100 if total_characters > 0 else 0

    return render_template(
        "play.html",
        current_word=current_word,
        current_index=current_index + 1,
        elapsed_time=elapsed_time,
        accuracy=accuracy
    )

# AJAX로 단어 확인 및 진행
@game_blueprint.route("/check_word", methods=["POST"])
def check_word():
    global random_words, current_index, total_correct, total_characters

    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"})

    if current_index >= len(random_words):  # 범위 초과 방지
        return jsonify({"success": True, "completed": True})

    user_input = request.json.get("user_input", "").strip()
    current_word = random_words[current_index]

    user_input = user_input[:len(current_word)]  # 입력값 길이 제한

    # 글자 비교 결과
    word_result = [1 if i < len(user_input) and user_input[i] == current_word[i] else 0 
                   for i in range(len(current_word))]
    total_correct.append(word_result)
    total_characters += len(current_word)

    current_index += 1

    if current_index >= len(random_words):  # 마지막 단어 처리
        return jsonify({"success": True, "completed": True})

    # 다음 단어 반환
    next_word = random_words[current_index]
    accuracy = (sum([sum(word) for word in total_correct]) / total_characters) * 100 if total_characters > 0 else 0

    return jsonify({"success": True, "completed": False, "next_word": next_word, "current_index": current_index + 1, "accuracy": accuracy})

# user_scores 테이블 업데이트 함수
def update_user_scores(user_id, words, total_correct):
    connection = get_db_connection()
    cursor = connection.cursor()

    # 기존 사용자 스코어 가져오기
    cursor.execute("SELECT char_score FROM user_scores WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    # 새로운 점수 계산
    char_scores = {} if not result else json.loads(result[0])
    for word, correct in zip(words, total_correct):
        for i, char in enumerate(word):
            if char not in char_scores:
                char_scores[char] = 0
            # 맞춘 글자는 +1, 틀린 글자는 -1
            char_scores[char] += 1 if correct[i] else -1

    # 스코어 업데이트 또는 삽입
    if not result:
        # 새 사용자 점수 삽입
        cursor.execute(
            "INSERT INTO user_scores (user_id, char_score) VALUES (%s, %s)",
            (user_id, json.dumps(char_scores))
        )
    else:
        # 기존 점수 업데이트
        cursor.execute(
            "UPDATE user_scores SET char_score = %s WHERE user_id = %s",
            (json.dumps(char_scores), user_id)
        )

    connection.commit()
    connection.close()

# 결과 페이지
@game_blueprint.route("/results")
def results_page():
    global random_words, start_time, total_correct

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # 데이터의 길이가 일치하지 않는 경우 초기화 처리
    if len(random_words) != len(total_correct):
        total_correct = []  # 비정상 데이터 초기화
        return redirect(url_for("game.restart_game"))

    elapsed_time = int(time.time() - start_time)
    accuracy = (sum([sum(word) for word in total_correct]) / sum([len(word) for word in total_correct])) * 100

    # 한 사이클의 결과를 기록
    update_user_scores(user_id, random_words, total_correct)

    return render_template("results.html", elapsed_time=elapsed_time, accuracy=accuracy)

# 다시하기 버튼 처리
@game_blueprint.route("/restart")
def restart_game():
    global random_words, current_index, start_time, total_correct, total_characters

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    random_words = generate_words(user_id)  # 새 단어 리스트 생성

    current_index = 0
    start_time = time.time()  # 게임 시작 시간 초기화
    total_correct = []
    total_characters = 0
    return redirect(url_for("game.play_game"))

# 사용자 데이터베이스에서 가장 잘 맞춘 글자와 가장 어려운 글자 추출
@game_blueprint.route("/get_user_score_data", methods=["GET"])
def get_user_score_data():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"})

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # 사용자 스코어 가져오기
    cursor.execute("SELECT char_score FROM user_scores WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if not result:
        connection.close()
        return jsonify({"success": False, "message": "No score data available."})

    char_score = json.loads(result[0])

    # 잘 맞춘 글자 상위 4개
    best_chars = sorted(char_score.items(), key=lambda x: x[1], reverse=True)[:4]

    # 어려운 글자 하위 4개
    worst_chars = sorted(char_score.items(), key=lambda x: x[1])[:4]

    connection.close()

    return jsonify({"success": True, "best_chars": best_chars, "worst_chars": worst_chars})