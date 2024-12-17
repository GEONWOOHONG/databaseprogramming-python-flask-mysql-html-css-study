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

    # 사용자 스코어 가져오기
    cursor.execute("SELECT char_score FROM user_scores WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result:
        # JSON 데이터를 딕셔너리로 변환
        char_score = json.loads(result[0])

        # 음수 스코어 필터링 및 정렬
        negative_scores = {char: score for char, score in char_score.items() if score < 0}
        if negative_scores:
            sorted_chars = sorted(negative_scores.items(), key=lambda x: x[1])  # 스코어 기준 정렬
            grouped_chars = {}
            for char, score in sorted_chars:
                grouped_chars.setdefault(score, []).append(char)

            # 동일한 스코어 그룹에서 랜덤 순서로 글자를 선택
            selected_chars = []
            for score, chars in grouped_chars.items():
                random.shuffle(chars)  # 랜덤으로 섞기
                selected_chars.extend(chars)

            # 상위 4개 글자를 선택
            low_score_chars = selected_chars[:4]
        else:
            # 음수 스코어가 없는 경우 20개 랜덤 단어 반환
            cursor.execute("SELECT word FROM three_words ORDER BY RAND() LIMIT 20")
            random_words = [row[0] for row in cursor.fetchall()]
            connection.close()
            return random_words
    else:
        # 스코어 데이터가 없으면 랜덤 단어 20개 반환
        cursor.execute("SELECT word FROM three_words ORDER BY RAND() LIMIT 20")
        random_words = [row[0] for row in cursor.fetchall()]
        connection.close()
        return random_words

    # 상위 4개 글자를 포함하는 단어 추출
    frequent_words = []
    for char in low_score_chars:
        cursor.execute("SELECT word FROM three_words WHERE letter1 = %s OR letter2 = %s OR letter3 = %s LIMIT 3", (char, char, char))
        frequent_words.extend([row[0] for row in cursor.fetchall()])

    # 부족한 경우 상위 글자 단어로 추가
    while len(frequent_words) < 12:
        cursor.execute("SELECT word FROM three_words WHERE letter1 IN %s OR letter2 IN %s OR letter3 IN %s LIMIT %s",
                       (tuple(low_score_chars), tuple(low_score_chars), tuple(low_score_chars), 12 - len(frequent_words)))
        frequent_words.extend([row[0] for row in cursor.fetchall()])

    # 랜덤 단어 8개 추출 (상위 글자 단어 제외)
    cursor.execute("SELECT word FROM three_words WHERE word NOT IN %s ORDER BY RAND() LIMIT 8", (tuple(frequent_words),))
    random_words = [row[0] for row in cursor.fetchall()]

    connection.close()

    # 섞어서 반환: 자주 틀리는 단어 + 랜덤 단어
    combined_words = []
    for i in range(12):
        combined_words.append(frequent_words[i])
        if i < 8:
            combined_words.append(random_words[i])
    return combined_words

    # 상위 4개 글자를 포함하는 단어 추출
    frequent_words = []
    for char in low_score_chars:
        cursor.execute("SELECT word FROM three_words WHERE letter1 = %s OR letter2 = %s OR letter3 = %s LIMIT 3", (char, char, char))
        frequent_words.extend([row[0] for row in cursor.fetchall()])

    # 부족한 경우 상위 글자 단어로 추가
    while len(frequent_words) < 12:
        cursor.execute("SELECT word FROM three_words WHERE letter1 IN %s OR letter2 IN %s OR letter3 IN %s LIMIT %s",
                       (tuple(low_score_chars), tuple(low_score_chars), tuple(low_score_chars), 12 - len(frequent_words)))
        frequent_words.extend([row[0] for row in cursor.fetchall()])

    # 랜덤 단어 8개 추출 (상위 글자 단어 제외)
    cursor.execute("SELECT word FROM three_words WHERE word NOT IN %s ORDER BY RAND() LIMIT 8", (tuple(frequent_words),))
    random_words = [row[0] for row in cursor.fetchall()]

    connection.close()

    # 섞어서 반환: 자주 틀리는 단어 + 랜덤 단어
    combined_words = []
    for i in range(12):
        combined_words.append(frequent_words[i])
        if i < 8:
            combined_words.append(random_words[i])
    return combined_words

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

    # current_index가 random_words의 범위를 초과하지 않는지 확인
    if current_index >= len(random_words):
        return jsonify({"success": False, "message": "Index out of range"})

    user_input = request.json.get("user_input", "").strip()  # 공백 제거
    current_word = random_words[current_index]

    # 입력값을 현재 단어 길이까지만 자르기
    user_input = user_input[:len(current_word)]

    # 글자 비교 결과를 저장
    word_result = []
    for i in range(len(current_word)):
        if i < len(user_input) and user_input[i] == current_word[i]:
            word_result.append(1)
        else:
            word_result.append(0)
    total_correct.append(word_result)
    total_characters += len(current_word)  # 총 글자 수는 현재 단어의 길이만 반영

    current_index += 1

    # current_index가 random_words의 길이를 초과하면 완료 응답 반환
    if current_index >= len(random_words):
        return jsonify({"success": True, "completed": True})

    # 다음 단어 및 정확도 계산
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
    random_words = generate_words(user_id)

    current_index = 0
    start_time = time.time()  # 게임 시작 시간 초기화
    total_correct = []
    total_characters = 0
    return redirect(url_for("game.play_game"))
