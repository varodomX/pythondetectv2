

# ส่งเป็นรูปเต็มๆ 

from bs4 import BeautifulSoup
import requests
import cv2
import numpy as np
from PIL import Image
import time
from datetime import datetime, timedelta

def send_line_notify_with_cropped_image(message, token, cropped_image):
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': 'Bearer ' + token}
    data = {'message': message}
    files = {'imageFile': ('image.jpg', cropped_image, 'image/jpeg')}
    requests.post(url, headers=headers, data=data, files=files)

def detect_rain(image_path, line_notify_token1, line_notify_token2):
    img = cv2.imread(image_path)
    if img is None:
        print("ไม่สามารถอ่านภาพไฟล์ได้")
        return

    # ข้อมูลของจุดที่ต้องการตรวจจับ
    points_to_detect = [
        (436, 392, 25, "อำเภอเมือง"),
        (330, 370, 18, "อำเภอชุมแพ"),
        (400, 457, 18, "พล")
    ]

    for center_x, center_y, radius, name in points_to_detect:
        # สร้าง mask วงกลม
        mask = np.zeros(img.shape[:2], dtype="uint8")
        cv2.circle(mask, (center_x, center_y), radius, 255, -1)

        # ครอปภาพด้วย mask วงกลม
        masked_img = cv2.bitwise_and(img, img, mask=mask)
        hsv = cv2.cvtColor(masked_img, cv2.COLOR_BGR2HSV)
        lower_red_hsv = np.array([0, 100, 100])
        upper_red_hsv = np.array([22, 255, 255])
        mask_red_hsv = cv2.inRange(hsv, lower_red_hsv, upper_red_hsv)
        contours_red, _ = cv2.findContours(mask_red_hsv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        red_area = sum(cv2.contourArea(cnt) for cnt in contours_red)

        print(f"พื้นที่ของฝนสีแดงที่ {name}: {red_area} Pixel")

        if red_area > 4:
            # หากระบุพื้นที่สีแดงมากกว่า 4 pixel ให้คำนวณพื้นที่และส่งข้อมูล
            message = f"พบฝนที่ {name}!\nพื้นที่ของฝนสีแดง: {red_area} Pixel\nในรัศมีวงกลม"

            # ครอปภาพเฉพาะส่วนที่มีฝน
            cropped_img = masked_img

            # บันทึกภาพที่ถูกครอปเฉพาะส่วนที่มีฝน
            cv2.imwrite(f'rain_detected_{name}.jpg', cropped_img)

            # เตรียมภาพที่จะส่งผ่าน Line Notify
            _, encoded_image = cv2.imencode('.jpg', cropped_img)
            cropped_image = encoded_image.tobytes()

            # ส่งข้อความพร้อมภาพผ่าน Line Notify
            send_line_notify_with_cropped_image(message, line_notify_token1, cropped_image)
            send_line_notify_with_cropped_image(message, line_notify_token2, cropped_image)
        else:
            # หากไม่พบฝน ให้บันทึกภาพทั้งหมด
            cv2.imwrite(f'no_rain_detected_{name}.jpg', masked_img)



# ฟังก์ชันสำหรับดาวน์โหลดภาพและตรวจสอบฝนทุก 15 นาที
def download_and_detect():
    while True:
        input("กด Enter เพื่อเริ่มต้นดาวน์โหลดและตรวจสอบฝนทุก 15 นาที:")
        while True:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            if current_time.endswith("36") or current_time.endswith("20") or current_time.endswith("35") or current_time.endswith("50"):
                # อัปเดต URL ตามที่จำเป็น
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
                line_notify_token1 = "hPbe5LyrLS9kaPhgBnA8HQb7X5UX685qy84lmKCR6k6"
                line_notify_token2 = "Dn8iDbL9nDNiiO6BlQjOwjJRYhJpANCZxTIHKf02ydT"
                detect_rain(image_path, line_notify_token1, line_notify_token2)
                time.sleep(900)  # รอ 15 นาที
            else:
                time.sleep(1)  # รอ 1 วินาที

if __name__ == "__main__":
    download_and_detect()
