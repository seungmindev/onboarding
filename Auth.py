from flask import Flask, request, redirect, url_for, session, jsonify, abort, render_template_string

app = Flask(__name__)
app.secret_key = 'test_secret'

# 메모리 기반 게시글 (post_id: {"title": str, "content": str, "is_secret": bool, "owner": str})
posts = {
    1: {"title": "공개 글입니다", "content": "누구나 볼 수 있어요", "is_secret": False, "owner": "user1"},
    37: {"title": "환불 부탁드립니다.", "content": "Pringles입니다. Pringles 가격이 너무 사악합니다. 환불할게요 계좌번호 100-123-1234입니다. 감사합니다.", "is_secret": True, "owner": "Pringles"},
}

# 템플릿
login_form = '''
<h2>로그인</h2>
<form method="POST">
  사용자명: <input name="username">
  비밀번호: <input name="password">
  <button type="submit">로그인</button>
</form>
'''

mfa_form = '''
<h2>2차 인증</h2>
<p>코드가 전송되었습니다.</p>
<form id="mfaForm">
  인증 코드: <input id="code" name="code">
  <button type="submit">인증</button>
</form>
<script>
document.getElementById('mfaForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const code = document.getElementById('code').value;
  const res = await fetch("/mfa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code })
  });
  const data = await res.json();
  if (data.result === true) {
    window.location.href = "/mfa/result";
  } else {
    alert("인증 실패!");
  }
});
</script>
'''

@app.route("/", methods=["GET"])
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    
    post_list_html = ""
    for post_id, post in posts.items():
        post_list_html += f'<li><a href="/posts/{post_id}">{post["title"]}</a></li>'

    return f'''
    <h2>메인 페이지</h2>
    <ul>
      {post_list_html}
    </ul>
    '''

####################################################
# 로그인 과정
####################################################
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["username"] = request.form["username"]
        return redirect(url_for("mfa_page"))
    return login_form

# 2차인증 
@app.route("/mfa_page", methods=["GET"])
def mfa_page():
    return mfa_form

@app.route("/mfa", methods=["GET", "POST"])
def mfa():
    data = request.get_json()
    code = data.get("code", "")

    if code == "123456":  # 임시 코드
        return jsonify({"result": True})
    else:
        return jsonify({"result": False})
    return mfa_form

@app.route("/mfa/result")
def mfa_result():
    # 이 페이지에서 인증 확정 처리
    session["authenticated"] = True
    return redirect(url_for("index"))

####################################################
# 게시글 
####################################################
@app.route("/posts/<int:post_id>")
def view_post(post_id):
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    post = posts.get(post_id)
    if not post:
        return "해당 글이 존재하지 않습니다.", 404

    username = session.get("username")
    is_owner = (username == post["owner"])

    # 비밀글은 소유자만 접근 가능
    if post['is_secret'] and not is_owner:
        return "권한이 없습니다 (비밀글).", 403

    edit_button = f'<a href="/posts/{post_id}/edit"><button>✏️ 수정</button></a>' if is_owner else ""
    
    return f"""
    <h2>{post['title']}</h2>
    <p>{post['content']}</p>
    {edit_button}
    <br><a href='/'>🏠 홈으로</a>
    """


# 게시글 수정 (인가 체크 X → 의도된 취약점)
@app.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    post = posts.get(post_id)
    if not post:
        return "해당 글이 존재하지 않습니다.", 404

    if request.method == "POST":
        new_title = request.form.get("title")
        new_content = request.form.get("content")
        post["title"] = new_title
        post["content"] = new_content
        return f"<h2>수정 완료</h2><a href='/posts/{post_id}'>돌아가기</a>"

    # 누구나 이 페이지에 접근 가능하고 파라미터만 조작하면 비밀글도 수정 가능
    return f'''
    <h2>게시글 수정 - {post_id}번</h2>
    <form method="POST">
      제목: <input name="title" value="{post['title']}"><br>
      내용: <textarea name="content">{post['content']}</textarea><br>
      <button type="submit">수정</button>
    </form>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
