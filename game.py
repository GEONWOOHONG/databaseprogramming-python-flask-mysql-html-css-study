from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import pymysql
import random
import time

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
total_correct = 0  # 총 맞춘 글자 수
total_characters = 0  # 총 입력한 글자 수

# 게임 메인 페이지
@game_blueprint.route("/index", methods=["GET", "POST"])
def index():
    global random_words, current_index, start_time, total_correct, total_characters

    if "user_id" not in session:
        return redirect(url_for("login"))  # 로그인하지 않은 경우 로그인 페이지로 이동

    if request.method == "POST":
        if "start_game" in request.form:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT word FROM three_words ORDER BY RAND() LIMIT 20")
            random_words = [row[0] for row in cursor.fetchall()]
            connection.close()

            current_index = 0
            start_time = time.time()  # 게임 시작 시간 기록
            total_correct = 0
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
    accuracy = (total_correct / total_characters) * 100 if total_characters > 0 else 0

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

    user_input = request.json.get("user_input", "").strip()  # 공백 제거
    current_word = random_words[current_index]

    # 글자 비교
    for i in range(len(current_word)):
        if i < len(user_input) and user_input[i] == current_word[i]:
            total_correct += 1
        total_characters += 1

    current_index += 1
    if current_index >= len(random_words):
        return jsonify({"success": True, "completed": True})

    next_word = random_words[current_index]
    accuracy = (total_correct / total_characters) * 100 if total_characters > 0 else 0
    return jsonify({"success": True, "completed": False, "next_word": next_word, "current_index": current_index + 1, "accuracy": accuracy})


# 결과 페이지
@game_blueprint.route("/results")
def results_page():
    global start_time, total_correct, total_characters

    if "user_id" not in session:
        return redirect(url_for("login"))

    elapsed_time = int(time.time() - start_time)
    accuracy = (total_correct / total_characters) * 100 if total_characters > 0 else 0

    return render_template("results.html", elapsed_time=elapsed_time, accuracy=accuracy)

# 다시하기 버튼 처리
@game_blueprint.route("/restart")
def restart_game():
    global random_words, current_index, start_time, total_correct, total_characters

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT word FROM three_words ORDER BY RAND() LIMIT 20")
    random_words = [row[0] for row in cursor.fetchall()]
    connection.close()

    current_index = 0
    start_time = time.time()  # 게임 시작 시간 초기화
    total_correct = 0
    total_characters = 0
    return redirect(url_for("game.play_game"))
