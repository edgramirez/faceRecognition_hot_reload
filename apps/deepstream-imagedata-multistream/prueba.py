import lib.json_methods as jsm
import time
import threading


camera_id = '12312412'
gender = 'hombre'
age_mean = 34
data = {
                        "clientId": "AT&T",
                        "cameraId": camera_id+"_ageGender",
                        "gender": gender,
                        "age": age_mean,
                        "epocTime": time.time()
    }
key = "camera_"+camera_id+"_ageAndGender"

#jsm.send_json(sv.header, data, 'POST', sv.urls[key])
for item in range(800):
    header = {'Accept': '*/*', 'Content-type': 'application/json; charset=utf-8', 'Connection': 'keep-alive', 'Keep-alive': 'timeout=5'}
    x = threading.Thread(target=jsm.send_json, args=(header, data, 'POST', "http://3.209.238.76:8888/posts/ageGender",))
    x.start()


