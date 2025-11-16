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
        if self.user_duplicate_check(str(data['id'])): #아이디 중복체크
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
    
    #중복체크
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
            # 사용자가 제공한 딕셔너리 키를 사용합니다.
            "title": data['title'],
            "rate": data['reviewStar'],
            "review": data['reviewContents'],
            "img_path": img_path
        }
        # 상품 이름을 파이어베이스의 child 키로 사용하여 리뷰를 설정(set)합니다.
        self.db.child("review").child(data['name']).set(review_info)
        return True
    
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
            "orderDate": pyrebase.database.ServerTimestamp # 서버 타임스탬프
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