from flask import Flask, render_template, request,flash, redirect, url_for, session, jsonify
from database import DBhandler
import hashlib
import sys
import math
import time

application = Flask(__name__)
application.config["SECRET_KEY"] = "helloosp"
DB = DBhandler()

#----------------------------------------------------------------------------
#Item
#----------------------------------------------------------------------------  

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

    user_likes = []
    if 'id' in session:
        # DB에서 유저의 찜 목록 가져오기
        likes_data = DB.get_likes_by_user(session['id'])
        user_likes = list(likes_data.keys()) if likes_data else []
    
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
        search_query=search_query,
        user_likes=user_likes
    )

# 상품 상세 조회
@application.route('/view_detail/<item_id>/')
def view_item_detail(item_id):
    print("###item_id:", item_id)
    data = DB.get_item_byid(item_id)
    
    if data is None:
        flash("존재하지 않는 상품입니다.")
        return redirect(url_for('view_list'))
        
    print("###data:",data)
    seller_id = data.get('seller')
    seller_nickname = DB.get_user_nickname(seller_id)

    if not seller_nickname:
        seller_nickname = seller_id if seller_id else "알 수 없음"

    return render_template("item_detail.html",
                            name=data.get('name'), # 상품명은 data에서 가져와 템플릿에 전달
                            data=data, 
                            nickname=seller_nickname,
                            item_id=item_id # 템플릿에서 좋아요/리뷰 링크에 사용할 ID 전달
                    )

# 상품 구매
@application.route("/order_item/<item_id>/")
def order_item(item_id):
    if 'id' not in session or not session['id']:
        flash('로그인을 해주세요.')
        return redirect(url_for('login'))

    user_id = session['id']
    # name 대신 item_id로 상품 정보 조회
    item_data = DB.get_item_byid(item_id)
    
    if not item_data:
        flash("상품 정보를 찾을 수 없습니다.")
        return redirect(url_for('view_list'))
    
    # 상품이 삭제되더라도 내역은 남도록, 구매 시점의 정보를 모두 저장
    order_id = f"{user_id}_{item_id}_{int(time.time())}"

    order_data = {
        "buyerID": user_id,
        "productID": item_id,
        "sellerID": item_data.get("seller"),
        "address": item_data.get("addr", "임시 주소"),
        # 구매 내역 보존을 위한 스냅샷 데이터
        "item_name": item_data.get("name"),
        "item_price": item_data.get("price"),
        "item_img": item_data.get("img_path")
    }

    DB.insert_order(order_id, order_data)

    return f"""
    <script>
        alert("구매가 성공적으로 완료되었습니다!\\n구매 내역 페이지로 이동합니다.");
        location.href = "{url_for('mypage_buy')}";
    </script>
    """


# 상품 삭제 요청 처리
@application.route("/delete/<item_id>")
def delete_item(item_id):
    if 'id' not in session:
        return redirect(url_for('login'))
        
    data = DB.get_item_byid(item_id)
    
    # 상품 데이터가 없는 경우 예외 처리
    if data is None:
        flash("해당 상품을 찾을 수 없습니다.")
        return redirect(url_for('mypage_sell'))

    if data['seller'] != session['id']:
        flash("본인의 상품만 삭제할 수 있습니다.")
        return redirect(url_for('mypage_sell'))
        
    DB.delete_item(item_id)
    flash("상품이 삭제되었습니다.")
    return redirect(url_for('mypage_sell'))

# 상품 수정 페이지 보여주기
@application.route("/edit/<item_id>")
def view_item_edit(item_id):
    if 'id' not in session:
        return redirect(url_for('login'))

    data = DB.get_item_byid(item_id)

    # 상품 데이터가 없는 경우 예외 처리
    if data is None:
        flash("해당 상품을 찾을 수 없습니다.")
        return redirect(url_for('mypage_sell'))
        
    if data['seller'] != session['id']:
        flash("수정 권한이 없습니다.")
        return redirect(url_for('mypage_sell'))

    return render_template("mypage/mypage_sell_edit.html", data=data, item_id=item_id)

# 상품 수정 완료 처리(POST)
@application.route("/update_item_post/<item_id>", methods=['POST'])
def update_item_post(item_id):
    # 로그인 확인
    if 'id' not in session:
        return redirect(url_for('login'))
    
    # 기존 이미지
    existing_imgs = request.form.getlist('existing_images')

    # 새 이미지
    files = request.files.getlist("file")
    img_paths = []

    # 파일이 선택되었는지 확인(빈 파일이 넘어오지 않았는지 체크)
    if files and files[0].filename:
        for file in files:
            if file.filename:
                # 파일 저장
                file.save("static/images/{}".format(file.filename))
                # 리스트에 파일명 추가
                img_paths.append(file.filename)

    final_imgs = (existing_imgs + img_paths)[:5]
    data = request.form
    
    # img_paths 리스트가 비어있지 않으면(새 파일 업로드 됨) DB에 전달
    # 비어있으면(None) DB 함수 내부에서 기존 이미지 유지
    DB.update_item(item_id, data, final_imgs)
    
    flash("상품 정보가 수정되었습니다.")
    return redirect(url_for('view_item_detail', item_id=item_id))


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
    # 파일 하나가 아니라 리스트로 받아옴
    files = request.files.getlist("file")
    # 파일명을 담을 리스트
    img_paths = []

    # 여러 개의 파일을 반복문으로 하나씩 저장
    for file in files:
        if file.filename:
            # 파일 저장
            file.save("static/images/{}".format(file.filename))
            # 저장된 파일명을 리스트에 추가
            img_paths.append(file.filename)

    # 사진을 안 올렸을 경우 대비
    if not img_paths:
        img_paths = [""]

    data = request.form

    category = data.get('category', '').strip()
    if not category:
        data = data.to_dict()
        data['category'] = '기타'
    else:
        data = data.to_dict()

    # img_paths 리스트를 그대로 DB에 넘김
    item_id = DB.insert_item(data, img_paths, session['id'])
    
    return redirect(url_for('view_item_detail', item_id=item_id))

#----------------------------------------------------------------------------
#Review
#----------------------------------------------------------------------------     
@application.route("/reg_review_init/<item_id>/")
def reg_review_init(item_id):
    item = DB.get_item_byid(item_id)
    name = item.get("name", "")
    img = item.get("img_path")
    if isinstance(img, list):
        main_img = img[0] if img else None
    else:
        main_img = img

    return render_template(
        "reg_reviews.html",
        item_id=item_id,
        name=name,
        product_img=main_img
    )

# 수정 추가
@application.route("/reg_review", methods=['POST'])
def reg_review():
    if 'id' not in session:
        return redirect(url_for('login'))

    form_data = request.form
    review_key = form_data.get('review_key')
    existing_imgs = request.form.getlist('existing_images')

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

    final_imgs = (existing_imgs + img_paths)[:5]

    mapped_data = {
        "productID": form_data['productID'],      
        "title": form_data['title'],
        "rating": form_data['rating'],
        "content": form_data['content'],
        "buyerID": session['id'],
    }

    if review_key:
        DB.update_review(review_key, mapped_data, final_imgs)
    else:
        DB.reg_review(mapped_data, final_imgs)
    
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

        # 상품명 (productID -> item.name)
        item_id = value.get('productID')
        item = DB.get_item_byid(item_id) if item_id else None
        # 상품이 삭제된 경우: 전체 리뷰 목록에서 제외
        if not item:
            continue
        value['product_name'] = item.get('name') if item else "알 수 없음"
        
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

        item = DB.get_item_byid(review_data.get('productID'))
        product_name = item.get('name', "") if item else ""
        
        return render_template("review_detail.html", 
                                data=review_data,
                                name=product_name,
                                nickname=nickname)
    else:
        flash("리뷰가 없습니다.")
        return redirect(url_for('view_review'))


@application.route("/reviews_by_item/<name>/")
def view_review_by_item(name):
    page = request.args.get("page", 0, type=int)
    order_param = request.args.get("order", "최신순")
    rating_param = request.args.get("rating", "별점높은순")

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

    all_reviews = DB.get_reviews(sort_key, reverse)
    target_reviews = {}
    ratings = []

    for key, value in all_reviews.items():
        item_id = value.get('productID')
        if not item_id:
            continue

        item = DB.get_item_byid(item_id)
        if not item:
            continue

        if item.get('name') == name:
            writer_id = value.get('buyerID')
            value['nickname'] = DB.get_user_nickname(writer_id) or "알 수 없음"

            imgs = value.get('img_path')
            if isinstance(imgs, list) and len(imgs) > 0:
                value['img_path'] = imgs[0]
            elif not imgs:
                value['img_path'] = ""

            # 별점 모으기
            rating = value.get('rate') or value.get('rating')
            if rating is not None:
                ratings.append(float(rating))

            target_reviews[key] = value

    # 평균 별점
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

    # 페이지네이션
    per_page = 6
    item_counts = len(target_reviews)

    data_list = list(target_reviews.items())
    start_idx = per_page * page
    end_idx = start_idx + per_page

    reviews_paged = dict(data_list[start_idx:end_idx])

    page_count = (item_counts + per_page - 1) // per_page

    
    return render_template(
        "reviews_by_item.html",
        reviews=reviews_paged,
        product_name=name,
        total=item_counts,
        page=page,
        page_count=page_count,
        order=order_param,
        rating=rating_param,
        avg_rating=avg_rating, 
    )

#----------------------------------------------------------------------------
#Auth
#----------------------------------------------------------------------------  

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
    
#----------------------------------------------------------------------------
#Mypage
#----------------------------------------------------------------------------  

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
# 데이터 딕셔너리 키를 item_id(productID)로 설정
@application.route("/mypage_sell")
def mypage_sell():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    user_id = session['id']
    user_name = DB.get_user_nickname(user_id) or user_id

    items = DB.get_items_by_seller(user_id)

    data = { item['productID']: item for item in items }
    
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

    #상품명
    for review in data.values():
        pid = review.get('productID')
        product = DB.get_item_byid(pid) if pid else None
        review['product_name'] = (product or {}).get('name', '')
        review['is_deleted_product'] = (product is None)

    #페이지네이션
    page = request.args.get("page", 0, type=int)
    per_page = 3
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    item_counts = len(data)
    data_list = list(data.items())        
    data_paged = dict(data_list[start_idx:end_idx])

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

    # 상품 이름 붙이기 (한 줄로 정리)
    product_id = review_data.get("productID")
    item = DB.get_item_byid(product_id) if product_id else None
    review_data["product_name"] = (item or {}).get("name", "")

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


# 페이지네이션 중복 제거 헬퍼 함수
def paginate_data(data, page, per_page):
    item_counts = len(data)
    # 전체 페이지 수 계산
    page_count = math.ceil(item_counts / per_page)
    
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    
    # 딕셔너리를 리스트로 변환 후 슬라이싱
    data_list = list(data.items())
    current_page_data = dict(data_list[start_idx:end_idx])
    
    return current_page_data, page_count, item_counts