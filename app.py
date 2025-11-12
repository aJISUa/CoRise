from flask import Flask, render_template, request,flash, redirect, url_for, session
from database import DBhandler
import hashlib
import sys

application = Flask(__name__)
application.config["SECRET_KEY"] = "helloosp"
DB = DBhandler()

@application.route("/")
def hello():
    return redirect(url_for('view_list'))

@application.route("/list")
def view_list():
    page = request.args.get("page", 0, type=int)
    per_page=8
    per_row=4
    row_count=int(per_page/per_row)
    start_idx=per_page*page
    end_idx=per_page*(page+1)
    data = DB.get_item_list()
    item_counts = len(data)
    data = dict(list(data.items())[start_idx:end_idx])
    tot_count = len(data)
    for i in range(row_count):
        if (i == row_count-1) and (tot_count%per_row != 0):
            locals()['data_{}'.format(i)] = dict(list(data.items())[i*per_row:])
        else:
            locals()['data_{}'.format(i)] = dict(list(data.items())[i*per_row:(i+1)*per_row])
    return render_template (
        "items.html", 
        datas=data.items(), 
        row1 = locals()['data_0'].items(),
        row2 = locals()['data_1'].items(),
        limit=per_page,
        page=page,
        page_count=int((item_counts/per_page)+1),
        total=item_counts
    )    

@application.route('/view_detail/<name>/')
def view_item_detail(name):
    print("###name:",name)
    data = DB.get_item_byname(str(name))
    print("###data:",data)
    return render_template("item_detail.html", name=name, data=data)

# 상품등록 페이지 반환 (reg_items.html)
@application.route("/reg_items")
def reg_item():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    else:
        return render_template("reg_items.html")

# reg_items.html에 입력한 값들 db에저정 -> 상품상세 페이지 념겨줌
@application.route("/submit_item_post", methods=['POST'])
def reg_item_submit_post():
    image_file=request.files["file"]
    image_file.save("static/images/{}".format(image_file.filename))
    data=request.form
    DB.insert_item(data['name'], data, image_file.filename, session['id'])
    seller_nickname = DB.get_user_nickname(session['id'])
    return render_template(
        "item_detail.html",
        data=data,
        img_path="static/images/{}".format(image_file.filename),
        nickname = seller_nickname,
    )

@application.route("/reg_reviews")
def reg_review():
    return render_template("reg_reviews.html")

@application.route("/reviews")
def view_review():
    return render_template("reviews.html")

@application.route("/reviews_by_item")
def view_review_by_item():
    return render_template("reviews_by_item.html")

@application.route("/login")
def login():
    return render_template("login.html")

@application.route("/login_confirm", methods=['POST'])
def login_user():
    id_=request.form['id']
    pw=request.form['pw']
    pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if DB.find_user(id_,pw_hash):
        session['id']=id_
        return redirect(url_for('view_list'))
    else:
        flash("Wrong ID or PW!")
        return render_template("login.html")

@application.route("/signup")
def signup():
    return render_template("signup.html")

@application.route("/signup_post", methods=['POST'])
def register_user():
    data=request.form
    pw=request.form['pw']
    pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if DB.insert_user(data,pw_hash):
        return render_template("login.html")
    else:
        flash("user id already exist!")
        return render_template("signup.html")
    
@application.route("/logout")
def logout_user():
    session.clear()
    return redirect(url_for('view_list'))

#마이페이지 관련 코드 
@application.route("/mypage")
def mypage():
    return render_template("mypage/mypage.html")

@application.route("/mypage_edit")
def mypage_edit():
    return render_template("mypage/mypage_edit.html")

@application.route("/mypage_buy")
def mypage_buy():
    return render_template("mypage/mypage_buy.html")

@application.route("/mypage_sell")
def mypage_sell():
    return render_template("mypage/mypage_sell.html")

@application.route("/mypage_sell_edit")
def mypage_sell_edit():
    return render_template("mypage/mypage_sell_edit.html")

if __name__ == "__main__":
    application.run(host='0.0.0.0')


