from bs4 import BeautifulSoup
import requests
import cv2
import numpy as np
from PIL import Image
import time
from datetime import datetime, timedelta
import mysql.connector

def send_line_notify_with_cropped_image(message, token, cropped_image):
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': 'Bearer ' + token}
    data = {'message': message}
    files = {'imageFile': ('image.jpg', cropped_image, 'image/jpeg')}
    requests.post(url, headers=headers, data=data, files=files)

def save_message_to_db(messages, db_config):
    if not messages:
        messages_str = "ไม่มีฝน"
    else:
        messages_str = "พบฝนที่ " + ', '.join(messages)  # ใช้เครื่องหมายจุลภาคเป็นตัวคั่นและเพิ่มคำนำหน้า
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        query = "UPDATE raindetect SET `ขอนแก่น` = %s ORDER BY id DESC LIMIT 1"
        cursor.execute(query, (messages_str,))
        connection.commit()
        cursor.close()
        connection.close()
        print(f"อัปเดตข้อความลงฐานข้อมูลสำเร็จ: {messages_str}")
    except mysql.connector.Error as err:
        print(f"Error: {err}")

def detect_rain(image_path, line_notify_token1, line_notify_token2, db_config):
    img = cv2.imread(str(image_path))

    if img is None:
        print("ไม่สามารถอ่านภาพไฟล์ได้")
        return

    points_to_detect = [
        (436, 392, 25, "เมือง"),
        (450, 350, 25, "น้ำพอง"),
        (420, 330, 25, "อุบลรัตน์"),
        (420, 330, 25, "เขาสวนกวาง"),
        (485, 350, 20, "กระนวน"),
        (485, 370, 16, "ซำสูง"),
        (390, 350, 30, "ภูเวียง"),
        (350, 350, 20, "หนองนาคำ"),
        (350, 350, 20, "เวียงเก่า"),
        (330, 340, 25, "สีชมพู"),
        (290, 350, 25, "ภูผาม่าน"),
        (400, 392, 30, "บ้านฝาง"),
        (400, 392, 30, "หนองเรือ"),
        (420, 420, 20, "พระยืน"),
        (390, 430, 25, "มัญจาคีรี"),
        (370, 460, 18, "โคกโพธิ์ชัย"),
        (380, 490, 18, "แวงใหญ่"),
        (375, 495, 18, "แวงน้อย"),
        (375, 495, 18, "พล"),
        (440, 510, 25, "หนองสองห้อง"),
        (400, 460, 18, "ชนบท"),
        (420, 475, 16, "โนนศิลา"),
        (445, 485, 16, "เปือยน้อย"),
        (440, 460, 22, "บ้านไผ่"),
        (430, 440, 18, "บ้านแฮด"),
        (320, 370, 20, "ชุมแพ"),
        (400, 457, 18, "พล")
    ]

    detected_messages = []

    for center_x, center_y, radius, name in points_to_detect:
        mask = np.zeros(img.shape[:2], dtype="uint8")
        cv2.circle(mask, (center_x, center_y), radius, 255, -1)

        masked_img = cv2.bitwise_and(img, img, mask=mask)
        hsv = cv2.cvtColor(masked_img, cv2.COLOR_BGR2HSV)

        # ตั้งค่า HSV สำหรับสีเขียวอ่อน
        lower_green_hsv = np.array([0, 100, 100])
        upper_green_hsv = np.array([22, 255, 255])

        mask_green_hsv = cv2.inRange(hsv, lower_green_hsv, upper_green_hsv)
        contours_green, _ = cv2.findContours(mask_green_hsv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        green_area = sum(cv2.contourArea(cnt) for cnt in contours_green)

        print(f"พื้นที่ของฝนสีเขียวที่ {name}: {green_area} Pixel")

        if green_area > 0:
            if green_area >= 3:
                message = f"พบฝนที่ {name}"
                detected_messages.append(name)  # เพิ่มชื่อพื้นที่ที่ตรวจพบฝน

                x, y, w, h = cv2.boundingRect(mask_green_hsv)
                cropped_img = masked_img[y:y+h, x:x+w]
                cv2.imwrite(f'rain_detected_{name}.jpg', cropped_img)

                _, encoded_image = cv2.imencode('.jpg', cropped_img)
                cropped_image = encoded_image.tobytes()

                send_line_notify_with_cropped_image(message, line_notify_token1, cropped_image)
                send_line_notify_with_cropped_image(message, line_notify_token2, cropped_image)
            else:
                detected_messages.append(f"{name}")
                cv2.imwrite(f'no_rain_detected_{name}.jpg', masked_img)
        else:
            print(f"ไม่มีฝนที่ {name}")

    save_message_to_db(detected_messages, db_config)

def download_and_detect():
    db_config = {
        'user': 'varodomc_online',
        'password': 'varodom2011',
        'host': '103.86.51.224',
        'database': 'varodomc_online'
    }
    while True:
        input("กด Enter เพื่อเริ่มต้นดาวน์โหลดและตรวจสอบฝนทุก 15 นาที:")
        while True:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            if current_time.endswith("05") or current_time.endswith("20") or current_time.endswith("35") or current_time.endswith("50"):
                url = 'https://weather.tmd.go.th/kkn.php'
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                image_url = soup.find('img', id='radimg')['src']
                full_image_url = 'https://weather.tmd.go.th' + image_url.strip('.')
                response = requests.get(full_image_url)
                with open('rain_image.gif', 'wb') as f:
                    f.write(response.content)
                img_gif = Image.open("rain_image.gif")
                img_gif.convert("RGB").save("rain_image.jpg")
                image_path = 'rain_image.jpg'
                line_notify_token1 = ""
                line_notify_token2 = ""
                detect_rain(image_path, line_notify_token1, line_notify_token2, db_config)
                time.sleep(900)
            else:
                time.sleep(1)

if __name__ == "__main__":
    download_and_detect()
