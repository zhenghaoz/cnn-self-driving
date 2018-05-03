import cv2

image_dir = '../photo/'
video_dir = '../video/'

data_file = '../dataset.dat'
model_file = '../model/driver.ckpt'

url_github = 'https://github.com/ZhangZhenghao/GrandRaspberryAuto'
url_stream = 'http://192.168.1.1:8080/?action=stream'

host = '192.168.1.1'

video_fourcc = cv2.VideoWriter_fourcc(*'XVID')

stream_height = 240
stream_width = 320
stream_fps = 30
stream_channel = 3

observation_height = 60
observation_width = 160
observation_channel = 3

move_speed = 40
turn_speed = 50
