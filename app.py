from flask import Flask, render_template, request,flash, redirect, url_for, session, jsonify
from database import DBhandler
import hashlib
import sys
import math

application = Flask(__name__)
application.config["SECRET_KEY"] = "helloosp"
DB = DBhandler()

@application.route("/")
def hello():
    return redirect(url_for('view_list'))

@application.route("/list")
def view_list():
    page = request.args.get("page", 0, type=int)
    category = request.args.get("category", "all")
    # 정렬 및 가격 정렬 매개변수 추가 (URL 파라미터: sort, price)
    sort = request.args.get("sort", "latest")
    price_order = request.args.get("price", "low")
    search_query = request.args.get("q", "") 

    per_page=8
    per_row=4
    row_count=int(per_page/per_row)
    start_idx=per_page*page

    # DB 함수 호출: 카테고리, 정렬, 가격 정렬 매개변수 전달
    data_sorted = DB.get_item_list(category=category, sort=sort, price_order=price_order, search_query=search_query)    
    # 기존 수동 정렬 및 category 분기 로직 제거됨

    item_counts = len(data_sorted)
    data_list = list(data_sorted.items())
    
    # 페이징 처리
    end_idx=per_page*(page+1)
    data_page_list = data_list[start_idx:min(end_idx, item_counts)]
        
    data = dict(data_page_list) # 현재 페이지 상품 데이터
    
    # 행 분할 로직 (data_page_list 사용)
    row_data = {}
    for i in range(row_count):
        start = i * per_row
        end = (i + 1) * per_row
        current_row_list = data_page_list[start:end]
        row_data[f"data_{i}"] = dict(current_row_list)
        if not current_row_list:
            break
            
    # row1, row2에 데이터가 없을 경우를 대비해 기본값 설정
    row1_items = row_data.get("data_0", {}).items()
    row2_items = row_data.get("data_1", {}).items()
    
    return render_template (
        "items.html", 
        datas=data.items(), 
        row1=row1_items,
        row2=row2_items,
        limit=per_page,
        page=page,
        page_count=int(math.ceil(item_counts/per_page)), # 전체 상품 수 기준으로 페이지 수 계산
        total=item_counts,
        category=category,
        # 정렬 및 가격 정렬 매개변수 추가 전달
        sort=sort,
        price_order=price_order,
        search_query=search_query
    )

# 상품 상세 조회: <name> -> <item_id>로 변경
@application.route('/view_detail/<item_id>/')
def view_item_detail(item_id):
    print("###item_id:", item_id)
    data = DB.get_item_byid(item_id)
    
    if data is None:
        flash("존재하지 않는 상품입니다.")
        return redirect(url_for('view_list'))
        
    print("###data:",data)
    seller_nickname = DB.get_user_nickname(data.get('seller'))
    return render_template("item_detail.html",
                            name=data.get('name'), # 상품명은 data에서 가져와 템플릿에 전달
                            data=data, 
                            nickname=seller_nickname,
                            item_id=item_id # 템플릿에서 좋아요/리뷰 링크에 사용할 ID 전달
                    )

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

    # 카테고리 미선택 시 '기타'로 자동 설정
    category = data.get('category', '').strip()
    if not category:
        data = data.to_dict()
        data['category'] = '기타'
    else:
        data = data.to_dict() # 불변 대비 딕셔너리로 변환

    # DB.insert_item 호출 수정 (상품명 인자 제거, item_id를 반환받음)
    item_id = DB.insert_item(data, image_file.filename, session['id'])
    
    # redirect URL 수정: name 대신 item_id 사용
    return redirect(url_for('view_item_detail', item_id=item_id))

@application.route("/reg_reviews")
#def reg_review():
#    return render_template("reg_reviews.html")
# 12주차 리뷰 등록을 위한 경로

# 12주차 리뷰 등록을 위한 경로 추가 시작
# 리뷰 등록 시작 경로: <name> -> <item_id>로 변경
@application.route("/reg_review_init/<item_id>/")
def reg_review_init(item_id):
    # reg_reviews.html로 item_id를 전달
    return render_template("reg_reviews.html", item_id=item_id)
@application.route("/reg_review", methods=['POST'])
def reg_review():
    print(request.form)
    form_data=request.form
    try:
        image_file = request.files["photos"]
        
        # 파일이 존재하고 파일명이 있는 경우에만 저장 및 경로 설정
        if image_file.filename:
            image_file.save("static/images/{}".format(image_file.filename))
            img_path = image_file.filename
        else:
            img_path = ""
    except KeyError:
        # 파일 필드가 아예 없거나 잘못된 경우 처리
        img_path = ""
    # 리뷰 데이터에 name -> item_id 사용 (템플릿에서 item_id를 폼 데이터로 보내야 함)
    mapped_data = {
        "item_id": form_data['item_id'],
        "title": form_data['title'],
        "reviewStar": form_data['rating'],
        "reviewContents": form_data['content'],
        "buyerID": session['id'] 
    }
    DB.reg_review(mapped_data, img_path)
    
    # 저장 후 전체 리뷰 목록 페이지로 이동(기존 /reviews 경로 사용)
    return redirect(url_for('view_review'))
# 12주차 리뷰 등록을 위한 경로 추가 끝
# 12주차 리뷰 조회를 위한 경로 추가 시작
# 이 부분도 제가 키 오류가 있어서.. 잘 돌아가시면 원래 로직(상품 관련)으로 하셔도 될 것 같아요!
@application.route("/reviews")
def view_review():
    page = request.args.get("page", 0, type=int)
    per_page=6 
    per_row=3 
    row_count=int(per_page/per_row)
    start_idx=per_page*page
    end_idx=per_page*(page+1)
    data = DB.get_reviews() 
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

    return render_template(
        "reviews.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=int((item_counts + per_page - 1) / per_page), 
        total=item_counts
    )

# 리뷰 상세 조회: <name> -> <review_id>로 변경 및 상품명 조회 로직 추가
@application.route('/view_review_detail/<review_id>/')
def view_review_detail(review_id):
    # review_id를 키로 사용
    review_data = DB.db.child("review").child(str(review_id)).get().val() 
    
    product_name = "알 수 없는 상품"
    if review_data and 'item_id' in review_data:
        # 리뷰 데이터에 저장된 item_id로 상품 정보를 역조회하여 상품명(name)을 가져와야 함
        item_data = DB.get_item_byid(review_data['item_id'])
        if item_data:
            product_name = item_data.get('name')
        
    nickname = None # 현재 로직 유지
    
    if review_data:
        return render_template("review_detail.html", 
                                name=product_name, # 상품명 전달
                                data=review_data,
                                nickname=nickname)
    else:
        # 리뷰가 존재하지 않는 경우 처리
        flash(f"리뷰가 없습니다.")
        return redirect(url_for('view_review'))
# 12주차 리뷰 조회를 위한 경로 추가 끝



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
# 좋아요 기능 모두 <name> -> <item_id>로 변경, DB 호출 함수 변경
@application.route('/show_heart/<item_id>/', methods=['GET'])
def show_heart(item_id):
    my_heart = DB.get_heart_byid(session['id'],item_id)
    return jsonify({'my_heart': my_heart})
@application.route('/like/<item_id>/', methods=['POST'])
def like(item_id):
    DB.update_heart(session['id'],'Y',item_id)
    return jsonify({'msg': '좋아요 완료!'})
@application.route('/unlike/<item_id>/', methods=['POST'])
def unlike(item_id):
    DB.update_heart(session['id'],'N',item_id)
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
    per_page = 6
    per_row = 3
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
    print("=== mypage_buy: data_list ===")
    print(data_list)
    return render_template(
        "mypage/mypage_buy.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        user_name=user_name,
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=int((item_counts + per_page - 1) / per_page),
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
    per_page = 6
    per_row = 3
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
        page_count=int((item_counts + per_page - 1) / per_page),
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
        page_count=int((item_counts + per_page - 1) / per_page),
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
    per_page = 6
    per_row = 3
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
    print("=== mypage_review: data_list ===")
    print(data_list)
    return render_template(
        "mypage/mypage_review.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        user_name=user_name,
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        page_count=int((item_counts + per_page - 1) / per_page),
        total=item_counts
    )



# mypage 추가 후: item (수정, 삭제), review (등록) 부분
#판매내역수정페이지(9.3.1)
@application.route("/mypage_sell_edit")
def mypage_sell_edit():
    return render_template("mypage/mypage_sell_edit.html")

#작성한리뷰수정페이지(9.5.1)
@application.route("/mypage_review_edit")
def mypage_review_edit():
    return render_template("mypage/mypage_review_edit.html")



if __name__ == "__main__":
    application.run(host='0.0.0.0')
