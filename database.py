# database.py 파일
import pyrebase
import json

class DBhandler:
    def __init__(self):
        # 3단계에서 생성한 JSON 파일에서 설정 정보 로드
        with open('./authentication/firebase_auth.json') as f:
            config = json.load(f) # JSON 파일을 읽어 Python dictionary로 로드 [cite: 702]
        
        # Pyrebase 앱 초기화
        firebase = pyrebase.initialize_app(config)
        
        # Realtime Database 인스턴스 저장
        self.db = firebase.database()
    
    #아이템 삽입
    def insert_item(self, name, data, img_path):
        item_info ={
            "seller": data['seller'],
            "addr": data['addr'],
            "email": data['email'],
            "category": data['category'],
            "card": data['card'],
            "status": data['status'],
            "phone": data['phone'],
            "img_path": img_path
            }
        self.db.child("item").child(name).set(item_info)
        print(data,img_path)
        return True
    
    #회원가입
    def insert_user(self, data, pw):
        user_info ={
            "id": data['id'],
            "pw": pw,
            "nickname": data['nickname']
            }
        if self.user_duplicate_check(str(data['id'])): #아이디 중복체크
            self.db.child("user").push(user_info)
            print(data)
            return True
        else:
            return False
    
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