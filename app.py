from flask import Flask, render_template, request,flash, redirect, url_for, session, jsonify
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
# 자꾸 키 오류나서 data_0, data_1 초기화 추가 <- 저만 문제일수도 있어서 이건 잘 돌아가시면 무시하셔도 됩니다.
def view_list():
    page = request.args.get("page", 0, type=int)
    per_page=8
    per_row=4
    row_count=int(per_page/per_row)
    start_idx=per_page*page
    end_idx=per_page*(page+1)

    data = DB.get_item_list()
    item_counts = len(data)

    data_0 = {}
    data_1 = {}
    if item_counts > 0:
    # 상품이 있는 경우에만 페이징 처리 및 행 분할 로직 실행
        data = dict(list(data.items())[start_idx:end_idx])
        tot_count = len(data)
    
    for i in range(row_count):
        # 상품 분할 로직은 그대로 유지하되, locals() 대신 명시적인 변수에 할당
        current_data = dict(list(data.items())[i*per_row:] if (i == row_count-1) and (tot_count%per_row != 0)
                            else dict(list(data.items())[i*per_row:(i+1)*per_row]))
        
        # i 값에 따라 동적으로 할당하는 대신 명시적 변수에 할당 (코드 가독성 및 안전성 확보)
        if i == 0:
            data_0 = current_data
        elif i == 1:
            data_1 = current_data
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
    seller_nickname = DB.get_user_nickname(data.get('seller'))
    return render_template("item_detail.html", name=name, data=data, nickname=seller_nickname)

# 상품 구매  (임시 - 수정해주세요!)
@application.route("/order_item/<name>/")
def order_item(name):
    if 'id' not in session or not session['id']:
        flash('로그인을 해주세요.')
        return redirect(url_for('login'))

    user_id = session['id']
    item_data = DB.get_item_byname(str(name))
    address = item_data.get("addr", "임시 주소")

    order_id = f"{name}_{user_id}"

    order_data = {
        "buyerID": user_id,
        "productID": name,
        "address": address,
    }

    DB.insert_order(order_id, order_data)
    flash("구매가 완료되었습니다.")

    return redirect(url_for("mypage_buy"))

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
    
    return redirect(url_for('view_item_detail', name=data['name']))

# 12주차 리뷰 등록을 위한 경로 추가 시작
@application.route("/reg_review_init/<name>/")
def reg_review_init(name):
    return render_template("reg_reviews.html", name=name)

@application.route("/reg_review", methods=['POST'])
def reg_review():
    if 'id' not in session:
        return redirect(url_for('login'))

    form_data = request.form
    img_paths = [] 
    
    try:
        # 다중 이미지 처리
        images = request.files.getlist("photos") 
        for image in images:
            if image.filename:
                image.save("static/images/{}".format(image.filename))
                img_paths.append(image.filename)
                if len(img_paths) >= 5: break 
    except KeyError:
        pass 

    mapped_data = {
        "productID": form_data['productID'],      
        "title": form_data['title'],
        "rating": form_data['rating'],
        "content": form_data['content'],
        "buyerID": session['id'] 
    }
    
    DB.reg_review(mapped_data, img_paths)
    
    return redirect(url_for('view_review'))

@application.route("/reviews")
def view_review():
    page = request.args.get("page", 0, type=int)
    order_param = request.args.get("order", "최신순")
    rating_param = request.args.get("rating", "별점높은순")
    
    # 1. 정렬 기준 설정
    sort_key = 'timestamp'
    reverse = True
    if rating_param == '별점낮은순':
        sort_key = 'rate'
        reverse = False
    elif rating_param == '별점높은순':
        sort_key = 'rate'
        reverse = True
    elif order_param == '오래된 순':
        sort_key = 'timestamp'
        reverse = False
    
    # 2. DB에서 가져오기
    data = DB.get_reviews(sort_key, reverse)
    
    # 3. 닉네임 추가 & 이미지 리스트 처리
    final_data = {}
    for key, value in data.items():
        # 닉네임 조회
        writer_id = value.get('buyerID')
        value['nickname'] = DB.get_user_nickname(writer_id) if writer_id else "알 수 없음"
        
        # 템플릿 오류 방지: img_path가 리스트일 경우 첫 번째 사진만 대표 이미지로 문자열 변환
        # (HTML을 수정하지 않고 백엔드에서 처리해주는 방식)
        imgs = value.get('img_path')
        if isinstance(imgs, list) and len(imgs) > 0:
            value['img_path'] = imgs[0] # 리스트의 첫 번째 사진을 대표 사진으로
        elif not imgs:
            value['img_path'] = "" 
            
        final_data[key] = value

    # 4. 페이지네이션 
    per_page = 6 
    per_row = 3 
    row_count = int(per_page/per_row)
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    
    item_counts = len(final_data)
    data_list = list(final_data.items()) # 이미 정렬된 상태
    data_paged = dict(data_list[start_idx:end_idx])
    
    locals_data = {}
    # ... (row 분할 로직 기존과 동일) ...
    tot_count = len(data_paged)
    for i in range(row_count):
        start = i * per_row
        end = (i + 1) * per_row
        if i == row_count - 1 and tot_count % per_row != 0:
            current_data = dict(list(data_paged.items())[start:])
        else:
            current_data = dict(list(data_paged.items())[start:end])
        locals_data[f'data_{i}'] = current_data

    return render_template(
        "reviews.html",
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=int((item_counts + per_page - 1) / per_page), 
        total=item_counts
    )
    
@application.route('/view_review_detail/<key>/')
def view_review_detail(key):
    review_data = DB.get_review_by_id(key)
    if review_data:
        writer_id = review_data.get('buyerID')
        nickname = DB.get_user_nickname(writer_id)
        
        return render_template("review_detail.html", 
                                data=review_data,
                                name=review_data.get('productID'),
                                nickname=nickname)
    else:
        flash("리뷰가 없습니다.")
        return redirect(url_for('view_review'))



@application.route("/reviews_by_item/<name>/")
def view_review_by_item(name):
    all_reviews = DB.get_reviews() 
    target_reviews = {}
    
    for key, value in all_reviews.items():
        if value.get('productID') == name:
            # 닉네임 가져오기
            writer_id = value.get('buyerID')
            value['nickname'] = DB.get_user_nickname(writer_id) or "알 수 없음"
            
            # 이미지 처리 (리스트의 첫 번째만 썸네일로 사용)
            imgs = value.get('img_path')
            if isinstance(imgs, list) and len(imgs) > 0:
                value['img_path'] = imgs[0]
            
            target_reviews[key] = value

    return render_template("reviews_by_item.html", 
                           reviews=target_reviews, 
                           product_name=name)

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
        flash("중복 확인이 필요합니다.")
        return render_template("signup.html")
    
@application.route("/logout")
def logout_user():
    session.clear()
    return redirect(url_for('view_list'))

# auth 중복 확인 -> 버튼에 연결하실 때는 얘를 사용해주시면 될 것 같습니다.
#ID 중복 확인
@application.route("/check_id", methods=["GET"])
def check_id():
    user_id = request.args.get("id", "")
    available = DB.user_duplicate_check(user_id)
    if available:
        return jsonify({"ok": True, "available": True, "message": "사용 가능한 아이디입니다."})
    else:
        return jsonify({"ok": True, "available": False, "message": "이미 사용 중인 아이디입니다."})

#닉네임 중복 확인    
@application.route("/check_nickname", methods=["GET"])
def check_nickname():
    nickname = request.args.get("nickname", "")
    available = DB.nickname_duplicate_check(nickname)
    if available:
        return jsonify({"ok": True, "available": True, "message": "사용 가능한 닉네임입니다."})
    else:
        return jsonify({"ok": True, "available": False, "message": "이미 사용 중인 닉네임입니다."})

# 12주차 좋아요 기능
@application.route('/show_heart/<name>/', methods=['GET'])
def show_heart(name):
    my_heart = DB.get_heart_byname(session['id'],name)
    return jsonify({'my_heart': my_heart})
@application.route('/like/<name>/', methods=['POST'])
def like(name):
    my_heart = DB.update_heart(session['id'],'Y',name)
    return jsonify({'msg': '좋아요 완료!'})
@application.route('/unlike/<name>/', methods=['POST'])
def unlike(name):
    my_heart = DB.update_heart(session['id'],'N',name)
    return jsonify({'msg': '안좋아요 완료!'})


#마이페이지 관련 코드 
#마이페이지(9.1)
@application.route("/mypage")
def mypage():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_info = DB.get_user_info(user_id)
    return render_template("mypage/mypage.html", user=user_info) 

#마이페이지편집(9.1)/GET
@application.route("/mypage_edit", methods=["GET"])
def mypage_edit():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_info = DB.get_user_info(user_id)
    return render_template("mypage/mypage_edit.html", user=user_info)

#마이페이지편집(9.1)/POST -> mypage_edit.html에서 입력한 값들 넘겨줌
@application.route("/mypage_edit_post", methods=["POST"])
def mypage_edit_post():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    new_nickname = request.form.get("nickname")
    new_univ = request.form.get("univ")
    new_intro = request.form.get("intro")
    DB.edit_user_info(user_id, new_nickname, new_univ, new_intro)
    flash("회원 정보가 수정되었습니다.")
    return redirect(url_for('mypage'))

#구매내역페이지(9.2)
@application.route("/mypage_buy")
def mypage_buy():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_name = DB.get_user_nickname(user_id) or user_id

    orders = DB.get_orders_by_buyer(user_id)
    data = { o['orderID']: o for o in orders }
    #페이지네이션
    page = request.args.get("page", 0, type=int)
    per_page = 3
    #per_row = 3
    #row_count = int(per_page / per_row)
    total = len(orders)
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    item_counts = len(data)
    data_list = list(data.items())        
    data_paged = dict(data_list[start_idx:end_idx])
    locals_data = {}
    tot_count = len(data_paged)
    locals_data['data_0'] = data_paged

    #for i in range(row_count):
    #    start = i * per_row
    #    end = (i + 1) * per_row

    #    if i == row_count - 1 and tot_count % per_row != 0:
    #        current_data = dict(data_list[start_idx + start:])
    #    else:
    #        current_data = dict(data_list[start_idx + start: start_idx + end])

    #    locals_data[f'data_{i}'] = current_data
    #작동 확인용  -> 프론트 구현 후 삭제
    # print("=== mypage_buy: data_list ===")
    # print(data_list)
    return render_template(
        "mypage/mypage_buy.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        user_name=user_name,
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=max(1,int((item_counts + per_page - 1) / per_page)),
        total=item_counts
    )


#판매내역페이지(9.3)
@application.route("/mypage_sell")
def mypage_sell():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_name = DB.get_user_nickname(user_id) or user_id

    items = DB.get_items_by_seller(user_id)
    data = { str(idx): item for idx, item in enumerate(items) }
    #페이지네이션
    page = request.args.get("page", 0, type=int)
    per_page = 3
    #per_row = 3
    #row_count = int(per_page / per_row)
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    item_counts = len(data)
    data_list = list(data.items())        
    data_paged = dict(data_list[start_idx:end_idx])
    locals_data = {}
    locals_data['data_0'] = data_paged

    # for i in range(row_count):
    #    start = i * per_row
    #    end = (i + 1) * per_row

    #    if i == row_count - 1 and tot_count % per_row != 0:
    #        current_data = dict(data_list[start_idx + start:])
    #    else:
    #        current_data = dict(data_list[start_idx + start: start_idx + end])

    #    locals_data[f'data_{i}'] = current_data
    #작동 확인용  -> 프론트 구현 후 삭제
    print("=== mypage_sell: data_list ===")
    print(data_list)
    return render_template(
        "mypage/mypage_sell.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        user_name=user_name,
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=max(1, int((item_counts + per_page - 1) / per_page)),
        total=item_counts
    )

#찜목록페이지(9.4)
@application.route("/mypage_like")
def mypage_like():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_name = DB.get_user_nickname(user_id) or user_id

    data = DB.get_likes_by_user(user_id)
    #페이지네이션
    page = request.args.get("page", 0, type=int)
    per_page = 8
    per_row = 4
    row_count = int(per_page / per_row)
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    item_counts = len(data)
    data_list = list(data.items())        
    data_paged = dict(data_list[start_idx:end_idx])
    locals_data = {}
    tot_count = len(data_paged)

    for i in range(row_count):
        start = i * per_row
        end = (i + 1) * per_row

        if i == row_count - 1 and tot_count % per_row != 0:
            current_data = dict(data_list[start_idx + start:])
        else:
            current_data = dict(data_list[start_idx + start: start_idx + end])

        locals_data[f'data_{i}'] = current_data
    #작동 확인용  -> 프론트 구현 후 삭제    
    print("=== mypage_like: data_list ===")
    print(data_list)
    return render_template(
        "mypage/mypage_like.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        user_name=user_name,
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=max(1,int((item_counts + per_page - 1) / per_page)),
        total=item_counts
    )

#작성한리뷰페이지(9.5)
@application.route("/mypage_review")
def mypage_review():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_name = DB.get_user_nickname(user_id) or user_id

    data = DB.get_reviews_by_user(user_id)
    #페이지네이션
    page = request.args.get("page", 0, type=int)
    per_page = 3
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    item_counts = len(data)
    data_list = list(data.items())        
    data_paged = dict(data_list[start_idx:end_idx])

    #작동 확인용  -> 프론트 구현 후 삭제    
    print("=== mypage_review: data_list ===")
    print(data_list)
    return render_template(
        "mypage/mypage_review.html",
        user_name=user_name,
        row1=data_paged.items(), 
        limit=per_page,
        page=page,
        page_count=max(1,int((item_counts + per_page - 1) / per_page)),
        total=item_counts
    )



# mypage 추가 후: item (수정, 삭제), review (등록) 부분
#판매내역수정페이지(9.3.1)
@application.route("/mypage_sell_edit")
def mypage_sell_edit():
    return render_template("mypage/mypage_sell_edit.html")

#작성한리뷰수정페이지(9.5.1)
@application.route("/mypage_review_edit/<key>")
def mypage_review_edit(key):
    if 'id' not in session:
        return redirect(url_for('login'))
        
    # 1. DB에서 해당 리뷰 데이터를 가져옴 (기존 내용 채워넣기 위해)
    review_data = DB.get_review_by_id(key)
    
    if not review_data:
        flash("존재하지 않는 리뷰입니다.")
        return redirect(url_for('mypage_review'))

    # 2. html 파일에 데이터와 key를 함께 보냄
    return render_template("mypage/mypage_review_edit.html", data=review_data, key=key)

# [추가] 리뷰 삭제 기능
@application.route("/delete_review/<key>")
def delete_review(key):
    if 'id' not in session:
        return redirect(url_for('login'))
        
    # DB에서 삭제 함수 호출
    DB.delete_review(key)
    flash("리뷰가 삭제되었습니다.")
    return redirect(url_for('mypage_review'))

if __name__ == "__main__":
    application.run(host='0.0.0.0')




