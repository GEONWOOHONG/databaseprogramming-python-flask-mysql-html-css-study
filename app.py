from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
import hashlib
import re
from game import game_blueprint  # 게임 블루프린트 임포트

# 로그인 상태 확인 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("로그인이 필요합니다.")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = "supersecretkey"  # 세션 암호화 키

# MySQL 연결 함수
def get_db_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="1234",
        db="dbpDB",
        charset="utf8mb4"
    )

# 로그인 페이지
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # 비밀번호 입력 단계
        if "password" in request.form:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            # DB에서 비밀번호 확인
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_password))
            user = cursor.fetchone()
            connection.close()

            if user:
                session["user_id"] = user[0]
                session["nickname"] = user[1]
                return redirect(url_for("game.index"))  # 수정된 부분
            else:
                return render_template("login.html", username=username, show_password_step=True, password_error="잘못된 비밀번호입니다.")

        # 아이디 확인 단계
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        connection.close()

        if user:
            return render_template("login.html", username=username, show_password_step=True)
        else:
            return render_template("login.html", username_error="계정을 찾을 수 없습니다.")

    return render_template("login.html")

# 회원가입 페이지
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nickname = request.form.get("nickname")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        error_messages = {}

        # 닉네임 검증
        if not re.match(r"^[a-zA-Z0-9가-힣!@#$%^&*()]{1,12}$", nickname):
            error_messages["nickname"] = "닉네임은 한글 최대 6자 또는 영문/숫자/특수문자 최대 12자까지 가능합니다."
        if not re.match(r"^[a-z0-9]{6,12}$", username):
            error_messages["username"] = "아이디는 영어 소문자 및 숫자로만 6~12자 이내로 입력하세요."
        if len(password) < 8 or len(set(re.findall(r"[A-Z]", password)) | 
                                 set(re.findall(r"[a-z]", password)) |
                                 set(re.findall(r"\d", password)) | 
                                 set(re.findall(r"\W", password))) < 2:
            error_messages["password"] = "비밀번호는 최소 8자 이상이며, 두 종류 이상의 문자를 사용해야 합니다."
        if password != confirm_password:
            error_messages["confirm_password"] = "비밀번호가 일치하지 않습니다."

        if error_messages:
            return jsonify({"success": False, "errors": error_messages})

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("INSERT INTO users (nickname, username, password) VALUES (%s, %s, %s)", 
                           (nickname, username, hashed_password))
            connection.commit()
            return jsonify({"success": True})  # 성공 시 반환
        except pymysql.IntegrityError:
            return jsonify({"success": False, "errors": {"username": "이미 사용 중인 아이디입니다."}})
        finally:
            connection.close()

    return render_template("register.html", error_messages={}, form_data={})

@app.route("/check-username", methods=["POST"])
def check_username():
    username = request.form.get("username")
    if not username:
        return {"success": False, "error": "아이디를 입력해주세요."}

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    connection.close()

    if user:
        return {"success": True}
    else:
        return {"success": False, "error": "계정을 찾을 수 없습니다."}

# 게임 블루프린트 등록
app.register_blueprint(game_blueprint, url_prefix="/game")

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("nickname", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)