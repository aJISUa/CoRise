# database.py 파일
import pyrebase
import json
import hashlib
import sys

class DBhandler:
    def __init__(self):
        # 3단계에서 생성한 JSON 파일에서 설정 정보 로드
        with open('./authentication/firebase_auth.json') as f:
            config = json.load(f) # JSON 파일을 읽어 Python dictionary로 로드 [cite: 702]
        
        # Pyrebase 앱 초기화
        firebase = pyrebase.initialize_app(config)
        
        # Realtime Database 인스턴스 저장
        self.db = firebase.database()
    
#----------------------------------------------------------------------------
#User 관련 CRUD 
#----------------------------------------------------------------------------
    #회원가입
    def insert_user(self, data, pw):
        user_info ={
            "id": data['id'],
            "pw": pw,
            "nickname": data['nickname'],
            "email": data.get('email', ''), 
            "phoneNumber": data.get('phone', ''),
            "autoLoginEnabled": False
            }
        #아이디 및 닉네임 중복체크
        id_check = self.user_duplicate_check(str(data['id']))
        nickname_check = self.nickname_duplicate_check(str(data['nickname']))
        if id_check and nickname_check:
            self.db.child("user").push(user_info)
            print(data)
            return True
        else:
            return False
    
    #회원 닉네임 가져오기
    def get_user_nickname(self, user_id):
        snap = self.db.child("user").get()
        data = snap.val() or {}
        for _, user in data.items():
            if str(user.get("id")) == str(user_id):
                return user.get("nickname")
        return None
    
    #회원 정보 가져오기
    def get_user_info(self, user_id):
        snap = self.db.child("user").get()
        data = snap.val() or {}
        for _, user in data.items():
            if str(user.get("id")) == str(user_id):
                return user

        return None
    
    #아이디 중복체크
    def user_duplicate_check(self, id_string):
        users = self.db.child("user").get()
        print("users###",users.val())
        if str(users.val()) == "None": # first registration
            return True
        else:
            for res in users.each():
                value = res.val()
                if value['id'] == id_string:
                    return False
            return True
        
        #닉네임 중복체크
    def nickname_duplicate_check(self, nickname_string):
        users = self.db.child("user").get()
        if str(users.val()) == "None": # first registration
            return True
        else:
            for res in users.each():
                value = res.val() or {}
                if str(value.get('nickname')) == str(nickname_string):
                    return False
            return True
    
    #로그인 로직
    def find_user(self, id_, pw_):
        users = self.db.child("user").get()
        target_value=[]
        for res in users.each():
            value = res.val()
            if value['id'] == id_ and value['pw'] == pw_:
                return True
        return False
#----------------------------------------------------------------------------
#Item/Product 관련 CRUD 
#----------------------------------------------------------------------------        
    #아이템 삽입 (상품 등록)
    def insert_item(self, data, img_path, user_id):
        item_info ={
            "name":data['name'],
            "price": int(data['price']),
            "seller": user_id,
            "addr": data['addr'],
            #"email": data['email'],
            "category": data['category'],
            #"card": data['card'],
            #"status": data['status'],
            "description": data['description'],
            #"phone": data['phone'],
            "img_path": img_path,
            #"addDate": pyrebase.database.ServerTimestamp --> 에러 떠서 아래로 임시 수정
            "addDate": {".sv": "timestamp"}
            }
        
        # 상품 이름 대신 Firebase가 생성하는 고유 키를 사용
        result = self.db.child("item").push(item_info)
        print(data,img_path)
        return result['name']
    
    # 아이템의 좋아요(찜) 수 계산
    def _get_item_likes(self): # 내부 전용 메서드라서 _ 접두사 사용
        hearts_snap = self.db.child("heart").get()
        likes_count = {}

        if hearts_snap.val():
            all_hearts = hearts_snap.val()
            for user_id, user_hearts in all_hearts.items():
                if isinstance(user_hearts, dict): 
                    for item_id, heart_data in user_hearts.items():
                        # 'interested' 필드가 'Y'인 경우만 좋아요로 카운트
                        if heart_data and heart_data.get('interested') == 'Y':
                            likes_count[item_id] = likes_count.get(item_id, 0) + 1
        return likes_count
    
    # 상품 목록 조회 및 정렬 통합
    def get_item_list(self, category="all", sort="latest", price_order="low", search_query=""):
        items_snap = self.db.child("item").get()
        data = items_snap.val() or {} # data 변수에 모든 상품 정보 저장
        
        # 좋아요 카운트 계산
        likes_count = self._get_item_likes()
        # items의 key는 이제 고유 ID이므로 key -> item_id로 변경
        for item_id, value in data.items():
            value['likes'] = likes_count.get(item_id, 0)
            value['item_id'] = item_id
            
        # 카테고리 필터링
        filtered_items = {}
        for key, value in data.items():
            if category == "all" or value.get('category') == category:
                filtered_items[key] = value
                
        items_list = list(filtered_items.items())

        # 검색어 필터링
        if search_query:
            temp_filtered_items = {}
            query = search_query.lower().strip()
            for key, value in filtered_items.items():
                item_name = value.get('name', '').lower()
                # 상품 설명에서도 검색 <- 제거 오직 상품명으로만 검색
                # item_desc = value.get('description', '').lower()
                # 상품명 또는 상품 설명에 검색어가 포함되어 있는지 확인
                # if query in item_name or query in item_desc:
                if query in item_name:
                    temp_filtered_items[key] = value
            filtered_items = temp_filtered_items # 검색 결과로 업데이트

        items_list = list(filtered_items.items())

        # 정렬 (최신순 또는 인기순)
        if sort == "latest": # 최신순 (addDate 기준 내림차순, Firebase timestamp)
            sorted_items_list = sorted(items_list, 
                                       key=lambda item: item[1].get('addDate', 0), 
                                       reverse=True)
        elif sort == "popular": # 인기순 (likes 기준 내림차순)
            sorted_items_list = sorted(items_list, 
                                       key=lambda item: item[1].get('likes', 0), 
                                       reverse=True)
        else: # 기본 정렬: 최신순
            sorted_items_list = sorted(items_list, 
                                       key=lambda item: item[1].get('addDate', 0), 
                                       reverse=True)
            
        # 가격 정렬 (2차 정렬 또는 독립적 정렬)
        if price_order == "low": # 낮은 가격 순 (오름차순)
            sorted_items_list = sorted(sorted_items_list, 
                                       key=lambda item: item[1].get('price', sys.maxsize), 
                                       reverse=False)
        elif price_order == "high": # 높은 가격 순 (내림차순)
            sorted_items_list = sorted(sorted_items_list, 
                                       key=lambda item: item[1].get('price', 0), 
                                       reverse=True)
        
        return dict(sorted_items_list)
    
    #카테고리별 상품 조회
    def get_items_bycategory(self, cate):
        return self.get_item_list(category=cate)
    
    # 상품 이름 -> id로 item 테이블에서 정보 가져오기로 변경
    def get_item_byid(self, item_id):
        item_snap = self.db.child("item").child(item_id).get()
        return item_snap.val()
    
    #카테고리 초기 데이터 삽입
    def insert_categories(self):
        categories_data = [
            {"categoryID": "C001", "name": "Clothes"},
            {"categoryID": "C002", "name": "Beauty"},
            {"categoryID": "C003", "name": "Books"}
        ]
        for cat in categories_data:
            self.db.child("category").child(cat['categoryID']).set(cat)
        return True


#----------------------------------------------------------------------------
#Review 관련 CRUD 
#----------------------------------------------------------------------------            
    #리뷰 등록
    def insert_review(self, review_id, data, img_urls):
        review_info = {
            "reviewID": review_id,
            "orderID": data['orderID'], 
            "buyerID": data['buyerID'],
            "productID": data['productID'],
            "title": data['title'],
            "rating": int(data['rating']), 
            "description": data['description'],
            "image": img_urls, 
            "addDate": pyrebase.database.ServerTimestamp
        }

        self.db.child("Review").child(review_id).set(review_info)
        print("Review data inserted:", review_info)
        return True
    
    # 12주차 리뷰 등록
    def reg_review(self, data, img_path):
        review_info ={
            # 상품 id 추가
            "item_id": data['item_id'],
            "title": data['title'],
            "rate": data['reviewStar'],
            "review": data['reviewContents'],
            "img_path": img_path,
            "buyerID": data['buyerID']
        }
        # self.db.child("review").child(data['name']).set(review_info)
        self.db.child("review").push(review_info) # .push()를 사용하여 고유 ID 생성
        return True
    
    # 12주차 리뷰 조회를 위한 함수
    def get_reviews(self):
        # "review" 테이블의 모든 데이터를 가져오기
        reviews = self.db.child("review").get().val()
        # 데이터가 없는 경우 빈 딕셔너리를 반환
        return reviews if reviews else {}


    # 상품별 리뷰 조회 (정렬 포함)
    def get_reviews_by_product(self, product_id, sort_by='addDate', order='desc'):
        reviews_ref = self.db.child("Review")
        
        # productID를 기준으로 필터링하여 쿼리 실행
        query = reviews_ref.order_by_child("productID").equal_to(product_id).get()
        
        reviews_list = []
        for review in query.each():
            reviews_list.append(review.val())
            
        # Python에서 정렬 (Timestamp는 Firebase에서 오름차순으로만 정렬되므로 Python 정렬 사용)
        if sort_by == 'addDate' or sort_by == 'rating':
            reviews_list.sort(key=lambda x: x.get(sort_by, 0), reverse=(order=='desc'))
            
        return reviews_list
    
    # 리뷰 수정
    def update_review(self, review_id, update_data, new_img_urls=None):
        review_ref = self.db.child("Review").child(review_id)
        
        # 수정할 데이터 딕셔너리 구성 (Rating은 int로 변환)
        data_to_update = {}
        for key, value in update_data.items():
            if key in ['rating'] and value:
                data_to_update[key] = int(value)
            elif key in ['title', 'description'] and value:
                data_to_update[key] = value
                
        if new_img_urls:
             data_to_update['image'] = new_img_urls
        
        # Firebase 업데이트 실행
        if data_to_update:
            review_ref.update(data_to_update)
            return True
        return False

    # 리뷰 삭제
    def delete_review(self, review_id):
        self.db.child("Review").child(review_id).remove()
        return True
    
#----------------------------------------------------------------------------
# Order 및 Like 관련 CRUD
#----------------------------------------------------------------------------
   #order 정보 insert
    def insert_order(self, order_id, data):
        order_info = {
            "orderID": order_id,
            "buyerID": data['buyerID'], 
            "productID": data['productID'],
            "address": data['address'],
            "orderDate": {".sv": "timestamp"}
            #"orderDate": pyrebase.database.ServerTimestamp # 서버 타임스탬프
        }
        self.db.child("Order").child(order_id).set(order_info)
        print("Order data inserted:", order_info)
        return True
    
    #Likes 정보 insert
    def insert_like(self, like_id, data):
        like_info = {
            "likeID": like_id,
            "userID": data['userID'],
            "productID": data['productID']
        }
        
        self.db.child("Like").child(like_id).set(like_info)
        print("Like data inserted:", like_info)
        return True
    
    # 하트(찜) 상태 조회, update: 상품 이름 -> id 기반으로 변경
    def get_heart_byid(self, uid, item_id):
        hearts = self.db.child("heart").child(str(uid)).child(str(item_id)).get()
        return hearts.val()
    
    def update_heart(self, user_id, isHeart, item_id):
        heart_info = {
            "interested" : isHeart
        }
        self.db.child("heart").child(user_id).child(item_id).set(heart_info)
        return True


#----------------------------------------------------------------------------
#MyPage 관련 CRUD 
#---------------------------------------------------------------------------- 

    #회원 정보 수정
    def edit_user_info(self, user_id, new_nickname, new_univ, new_intro):
        snap = self.db.child("user").get()
        users = snap.each()
        if not users:
            return False
        for i in users:
            if str(i.val().get("id")) == str(user_id):
                self.db.child("user").child(i.key()).update({
                    "nickname": new_nickname,
                    "univ": new_univ,
                    "intro": new_intro
                })
                return True
        return False
    
    #구매 내역 조회
    def get_orders_by_buyer(self, user_id):
        snap = self.db.child("Order").get()
        orders_list = []
        if snap.each():
            for i in snap.each():
                order_data = i.val() or {}
                order_data['orderID'] = i.key()
                # buyerID 기준으로 필터링
                if str(order_data.get("buyerID")) != str(user_id):
                    continue
                # 상품 정보 조회
                product_id = order_data.get("productID")
                if product_id:
                    item_data = self.get_item_byname(product_id) or {}
                else:
                    item_data = {}
                # 상품 정보
                order_data['item_name'] = item_data.get("name", product_id)
                order_data['item_price'] = item_data.get("price")
                order_data['item_img'] = item_data.get("img_path")
                order_data['seller'] = item_data.get("seller")
                orders_list.append(order_data)
        return orders_list
    
    #판매 내역 조회
    def get_items_by_seller(self, user_id):
        snap = self.db.child("item").get()
        orders_list = []
        if snap.each():
            for i in snap.each():
                item_data = i.val() or {}
                # seller 기준으로 필터링
                if str(item_data.get("seller")) != str(user_id):
                    continue
                item_data['productID'] = i.key()
                # 상품 정보
                item_data['item_name'] = item_data.get("name", item_data.get("productID"))
                item_data['item_price'] = item_data.get("price")
                item_data['item_img'] = item_data.get("img_path")
                item_data['seller'] = item_data.get("userID") or item_data.get("seller")
                orders_list.append(item_data)
        return orders_list
    
    #작성한 리뷰 조회
    def get_reviews_by_user(self, user_id, sort_by='addDate', order='desc'):
        snap = self.db.child("review").get()
        reviews_list = []
        if snap.each():
            for i in snap.each():
                review = i.val() or {}
                review_id = i.key()
                review["reviewID"] = review_id
                # buyerID 기준으로 필터링
                if str(review.get("buyerID")) != str(user_id):
                    continue
                reviews_list.append((review_id, review))

        # Python에서 정렬
        if sort_by in ('addDate', 'rating'):
            reviews_list.sort(key=lambda x: x[1].get(sort_by, 0), reverse=(order == 'desc'))

        reviews_dict = dict(reviews_list)

        return reviews_dict
    
    #하트(찜) 조회
    def get_likes_by_user(self, user_id):
        likes = self.db.child("heart").child(str(user_id)).get().val() or {}
        result = {}

        for product_id, info in likes.items():
            interested = None
            if isinstance(info, dict):
                interested = info.get("interested")
            else:
                interested = info
            if str(interested).upper() not in ("Y", "TRUE", "1"):
                continue
            item_data = self.get_item_byid(product_id) or {}
            # 상품 정보
            result[product_id] = {
                "productID": product_id,
                "name": item_data.get("name", product_id),
                "price": item_data.get("price"),
                "img_path": item_data.get("img_path"),
                "seller": item_data.get("seller"),
                "category": item_data.get("category"),
            }

        return result