{
    "hotReload":
    {
        "clientId": "0001",
        "34:56:fe:a3:99:de":
        {
            "source": "rtsp://192.168.129.40:9000/live",
            "source": "file:////home/mitmexico/Downloads/obama_entrevista.mp4",
            "services": [
                            {
		            "whiteList": {
		                "enabled": true,
                                "dbName": "/home/mitmexico/faceRecognition/input_data/whitelist_db/db_whitelist_34:56:fe:a3:99:de.dat",
		                "endpoint": "http://127.0.0.1:8000/posts/blackAndWhite"
		                }
		            },
		            {
		            "blackList": {
		                "enabled": true,
                                "dbName": "/home/mitmexico/faceRecognition/input_data/whitelist_db/db_blacklist_34:56:fe:a3:99:de.dat",
		                "endpoint": "http://127.0.0.1:8000/posts/blackAndWhite"
		                }
		            },
		            {
		            "ageAndGender": {
		                "enabled": false,
		                "endpoint": "http://127.0.0.1:8000/posts/ageGender"
		                }
		            }
                        ]
        }
    }
}
