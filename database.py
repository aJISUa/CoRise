# database.py 파일
import pyrebase
import json
import hashlib

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
    def insert_item(self, name, data, img_path, user_id):
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
        self.db.child("item").child(name).set(item_info)
        print(data,img_path)
        return True
    
    # 상품 목록 조회
    def get_item_list(self):
        items = self.db.child("item").get()
        if items.val():
            return items.val()
        return {}
    
    #상품이름으로 item 테이블에서 정보 가져오기
    def get_item_byname(self, name):
        items = self.db.child("item").get()
        target_value=""
        print("###########",name)

        for res in items.each():
            key_value = res.key()
            if key_value == name:
                target_value=res.val()
                
        return target_value
    
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
    # 리뷰 등록 (다중 이미지 + 고유 ID 생성)
    def reg_review(self, data, img_paths):
        review_info = {
            "title": data['title'],
            "rate": int(data['rating']),
            "review": data['content'],
            "img_path": img_paths,
            "buyerID": data['buyerID'],
            "productID": data['productID'],
            "timestamp": {".sv": "timestamp"}
        }

        self.db.child("review").push(review_info)
        return True
    
    # 리뷰 전체 조회
    def get_reviews(self, sort_key='timestamp', reverse=True):
        reviews = self.db.child("review").get().val()
        
        if not reviews:
            return {}

        reviews_list = list(reviews.items())
        
        # 정렬 로직
        # sort_key가 'rate'면 별점순, 'timestamp'면 최신순
        try:
            reviews_list.sort(key=lambda x: int(x[1].get(sort_key, 0)), reverse=reverse)
        except ValueError:
            reviews_list.sort(key=lambda x: 0, reverse=reverse)
        
        return dict(reviews_list)

    # 리뷰 상세 조회
    def get_review_by_id(self, review_id):
        return self.db.child("review").child(review_id).get().val()
    
    # 리뷰 수정
    def update_review(self, review_id, update_data, new_img_urls=None):
        review_ref = self.db.child("review").child(review_id)
        
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
        self.db.child("review").child(review_id).remove()
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
    
    # 하트(찜)
    def get_heart_byname(self, uid, name):
        hearts = self.db.child("heart").child(uid).get()
        target_value=""
        if hearts.val() == None:
            return target_value
        
        for res in hearts.each():
            key_value = res.key()
            if key_value == name:
                target_value=res.val()
        return target_value
    
    def update_heart(self, user_id, isHeart, item):
        heart_info ={
            "interested": isHeart
        }
        self.db.child("heart").child(user_id).child(item).set(heart_info)
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
            item_data = self.get_item_byname(product_id) or {}
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