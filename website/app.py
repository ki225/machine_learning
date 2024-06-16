# import module
from flask import Flask, request, jsonify, render_template, redirect, url_for
import pandas as pd 
import numpy as np
import joblib
import os
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from configparser import ConfigParser
import tensorflow as tf
from keras.preprocessing import image


# Config Parser
config = ConfigParser()
config.read("config.ini")

#把密碼寫到環境變數
os.environ["GOOGLE_API_KEY"] = config["Gemini"]["API_KEY"]

llm = ChatGoogleGenerativeAI(model="gemini-pro")

house_model = joblib.load('model/collision.pkl')

app = Flask(__name__)

# 圖片上傳限制變數
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
FIXED_FILENAME = 'crack.png'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 載入已訓練的模型
model_inceptionV3 = tf.keras.models.load_model('model/Crack_Detection_InceptionV3_model.h5')
model_X_inceptionV3 = tf.keras.models.load_model('model/X-shaped_Crack_Detection_InceptionV3_model.h5')
model_Y_inceptionV3 = tf.keras.models.load_model('model/Y-shaped_Crack_Detection_InceptionV3_model.h5')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 圖片辨識
def predict_image(img_path):
    
    # 針對model_inceptionV3、model_X_inceptionV3調整圖片大小為150x150，並讀取處理圖片
    img = image.load_img(img_path, target_size=(150, 150)) 
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0  

    # 預測
    prediction = model_inceptionV3.predict(img_array)
    predictionX = model_X_inceptionV3.predict(img_array)
    
    # 針對model_Y_inceptionV3調整圖片大小為224x224，並讀取處理圖片
    img = image.load_img(img_path, target_size=(224, 224))  
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0  
    
    # 預測
    predictionY = model_Y_inceptionV3.predict(img_array)
    
    reply_image = ''
    
    if prediction[0] > 0.5:
        reply_image += "這張圖片被判定為有裂縫"   
        if predictionX[0] < 0.5:
            reply_image += "，且被判定為X型裂縫"
        elif predictionY[0][0] < 0.5:
            reply_image += "，且被判定為Y型裂縫"      
        else:
            reply_image += "，且是一般形狀的裂縫"
    else:
        reply_image += "這張圖片被判定為沒有裂縫"
        
    return reply_image

# 裂縫結合大型語言模型
def reply_image(result):

    if result == "這張圖片被判定為有裂縫，且被判定為X型裂縫":
        result += " ，請告訴使用者判定結果，並且提醒用戶有X型裂縫是房屋損壞的警訊，而且如果斜線在「大梁、大柱或是剪力牆上」，危險度就更高，很有可能成為危樓，然後再提醒用戶需要注意甚麼以及該做的措施。"
        message = HumanMessage(
            content=[
                {
                "type": "text",
                "text": result,
                }
            ]
        )
        result = llm.invoke([message])
        reply = result.content
        
    if result == "這張圖片被判定為有裂縫，且被判定為Y型裂縫":
        result += " ，請告訴使用者判定結果，並且提醒用戶有Y型裂縫是房屋損壞的警訊，而且如果斜線在「大梁、大柱或是剪力牆上」，危險度就更高，很有可能成為危樓，然後再提醒用戶需要注意甚麼以及該做的措施。"
        message = HumanMessage(
            content=[
                {
                "type": "text",
                "text": result,
                }
            ]
        )
        result = llm.invoke([message])
        reply = result.content
        
        
    if result == "這張圖片被判定為有裂縫，且是一般形狀的裂縫":
        result += " ，請告訴使用者判定結果，並且提醒用戶要注意裂縫的位置跟大小，以及其他要注意的事。"
        message = HumanMessage(
            content=[
                {
                "type": "text",
                "text": result,
                }
            ]
        )
        result = llm.invoke([message])
        reply = result.content
        
        
    if result == "這張圖片被判定為沒有裂縫":
        result += " ，請告訴使用者判定結果，並且回答像是牆壁沒有損壞，房屋應該是安全之類的話。"
        message = HumanMessage(
            content=[
                {
                "type": "text",
                "text": result,
                }
            ]
        )
        result = llm.invoke([message])
        reply = result.content
    
    print(reply)
    return reply

# 處理縣市輸入
def city_data(s):
    city5_list = ["花蓮縣"]
    city4_list = ["台東縣", "臺東縣"]
    city3_list = ["台中市", "台南市", "南投縣", "臺中市", "臺南市"]
    city2_list = ["台北市", "桃園市",  "新竹市", "新竹縣", "彰化縣", "臺北市"]
    city1_list = [ "新北市", "高雄市", "基隆市", "嘉義市", "苗栗縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣"] 
    for city in city5_list:
        if s in city:
            return 5
    for city in city4_list:
        if s in city:
            return 4
    for city in city3_list:
        if s in city:
            return 3
    for city in city2_list:
        if s in city:
            return 2
    for city in city1_list:
        if s in city:
            return 1
    return 2

# 處理建材輸入
def material_data(s):
    material0_list = ["沙拉油桶、報紙、紙袋混充", "豆腐渣"]
    material1_list = ["鐵皮", "無筋磚砌體（無地基）", "土"]
    material2_list = ["洗石", "檜木", "木材", "石塊", "磚木"]
    material3_list = ["紅磚","磚瓦", "磚", "大理石"]
    material4_list = ["鋼筋混凝土", "混泥土", "水泥", "鋼筋混凝土+鐵皮", "鋼筋混土"]
    for material in material0_list:
        if s in material:
            return 0
    for material in material1_list:
        if s in material:
            return 1
    for material in material2_list:
        if s in material:
            return 2
    for material in material3_list:
        if s in material:
            return 3
    for material in material4_list:
        if s in material:
            return 4
    return 3

@app.route('/')
def index():
    return app.send_static_file('index.html')

# 介面右測bot
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()

    # user_mess 的type 是str
    user_message = data['message']
    if "我要預測" in user_message:
        reply = f"請在左邊表單輸入要預測的建築物資訊啾咪"
        return jsonify({'reply': reply})
    
    user_message += " ，請使用繁體中文回答。"
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": user_message,
            }
        ]
    )
    result = llm.invoke([message])
    reply = result.content
    return jsonify({'reply': reply})

# 介面左測表單
@app.route('/submit', methods=['POST'])
def submit_form():

    # 處理房屋倒塌預測資料
    city = request.form.get('City')
    fault = request.form.get('Fault')
    soil_liquefaction = request.form.get('Soil_Liquefaction')
    land_subsidence = request.form.get('Land_Subsidence')
    material = request.form.get('Material')
    floor = request.form.get('Floor')

    City_ = city_data(city)
    Material_ = material_data(material)
    data = [
        [
            City_,
            int(fault),
            int(soil_liquefaction),
            int(land_subsidence),
            Material_,
            float(floor),
        ]
    ]
    data = np.array(data).reshape(1, -1)
    result = house_model.predict(data)
    result_proba = house_model.predict_proba(data)
    ans = ""
    if result[0] == 0:
        ans = "大概不會倒"
        prediction = f"系統信心 {result_proba[0][0]:.5f}"

    else:
        ans = "有可能會倒喔"
        prediction = f"系統信心 {result_proba[0][1]:.5f}"

    print(ans)
    # 處理圖片上傳
    if 'image' not in request.files:
        return 'No file part'
    file = request.files['image']

    if file.filename == '':
        return 'No selected file'
    if file and allowed_file(file.filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], FIXED_FILENAME)
        file.save(file_path)
        result_img = predict_image(file_path)
        reply = reply_image(result_img)
        return jsonify({'result': ans, 'prediction': prediction, 'image_status': result_img, 'img_reply': reply})
    return jsonify({'result': ans, 'image_status': 'File type not allowed'})
 
if __name__ == '__main__':
    app.run(debug=True)



