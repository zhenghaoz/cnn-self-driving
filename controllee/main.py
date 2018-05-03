import binascii
import time
from socket import *

import RPi.GPIO as GPIO

# Config

control_host = ''
control_port = 8081

# Ports

# LED ports
LED0 = 10
LED1 = 9
LED2 = 25

# Motor ports
ENA = 13    # L298 ENABLE A
ENB = 20    # L298 ENABLE B
IN1 = 19    # M1+
IN2 = 16    # M1-
IN3 = 21    # M2+
IN4 = 26    # M2-

# Infrared ray ports
IR_R = 18   # Left IR sensor
IR_L = 27   # Right IR sensor

# Initialization

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Initialize LED
GPIO.setup(LED0, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(LED1, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(LED2, GPIO.OUT, initial=GPIO.HIGH)

# Initialize motor
GPIO.setup(ENA, GPIO.OUT, initial=GPIO.LOW)
ENA_pwm=GPIO.PWM(ENA, 1000)
ENA_pwm.start(0)
ENA_pwm.ChangeDutyCycle(100)
GPIO.setup(IN1, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN2, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ENB, GPIO.OUT, initial=GPIO.LOW)
ENB_pwm=GPIO.PWM(ENB,1000)
ENB_pwm.start(0)
ENB_pwm.ChangeDutyCycle(100)
GPIO.setup(IN3, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN4, GPIO.OUT, initial=GPIO.LOW)

# Initialize IR sensor
GPIO.setup(IR_R, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(IR_L, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# Light control

def	open_main_light():
    GPIO.output(LED0, False)
    time.sleep(1)


def	close_main_light():
    GPIO.output(LED0, True)
    time.sleep(1)


def	marquee_light():
    for i in range(5):
        GPIO.output(LED0, False)
        GPIO.output(LED1, False)
        GPIO.output(LED2, False)
        time.sleep(0.5)
        GPIO.output(LED0, True)
        GPIO.output(LED1, False)
        GPIO.output(LED2, False)
        time.sleep(0.5)
        GPIO.output(LED0, False)
        GPIO.output(LED1, True)
        GPIO.output(LED2, False)
        time.sleep(0.5)
        GPIO.output(LED0, False)
        GPIO.output(LED1, False)
        GPIO.output(LED2, True)
        time.sleep(0.5)
        GPIO.output(LED0, False)
        GPIO.output(LED1, False)
        GPIO.output(LED2, False)
        time.sleep(0.5)
        GPIO.output(LED0, True)
        GPIO.output(LED1, True)
        GPIO.output(LED2, True)


# Motor control

def motor_forward():
    print('Motor: Forward')
    GPIO.output(ENA, True)
    GPIO.output(ENB, True)
    GPIO.output(IN1, True)
    GPIO.output(IN2, False)
    GPIO.output(IN3, True)
    GPIO.output(IN4, False)
    GPIO.output(LED1, False)
    GPIO.output(LED2, False)


def motor_backward():
    print('Motor: Backward')
    GPIO.output(ENA, True)
    GPIO.output(ENB, True)
    GPIO.output(IN1, False)
    GPIO.output(IN2, True)
    GPIO.output(IN3, False)
    GPIO.output(IN4, True)
    GPIO.output(LED1, True)
    GPIO.output(LED2, False)


def motor_turn_left():
    print('Motor: Turn left')
    GPIO.output(ENA, True)
    GPIO.output(ENB, True)
    GPIO.output(IN1, True)
    GPIO.output(IN2, False)
    GPIO.output(IN3, False)
    GPIO.output(IN4, True)
    GPIO.output(LED1, False)
    GPIO.output(LED2, True)


def motor_turn_right():
    print('Motor: Turn right')
    GPIO.output(ENA, True)
    GPIO.output(ENB, True)
    GPIO.output(IN1, False)
    GPIO.output(IN2, True)
    GPIO.output(IN3, True)
    GPIO.output(IN4, False)
    GPIO.output(LED1, False)
    GPIO.output(LED2, True)


def motor_stop():
    print('Motor: Stop')
    GPIO.output(ENA, False)
    GPIO.output(ENB, False)
    GPIO.output(IN1, False)
    GPIO.output(IN2, False)
    GPIO.output(IN3, False)
    GPIO.output(IN4, False)
    GPIO.output(LED1, True)
    GPIO.output(LED2, True)


def left_speed(num):
    speed = hex(eval('0x' + num))
    speed = int(speed, 16)
    print('Motor: Change speed of left motors to %d ' % speed)
    ENA_pwm.ChangeDutyCycle(speed)


def right_speed(num):
    speed = hex(eval('0x' + num))
    speed = int(speed, 16)
    print('Motor: Change speed of right motors to %d ' % speed)
    ENB_pwm.ChangeDutyCycle(speed)


# Decode

def command_decode(data):
    if data[0] == '00':
        # Motor control
        if data[1] == '01':
            motor_forward()
        elif data[1] == '02':
            motor_backward()
        elif data[1] == '03':
            motor_turn_left()
        elif data[1] == '04':
            motor_turn_right()
        elif data[1] == '00':
            motor_stop()
        else:
            print('Decode: Invalid command.')
    elif data[0] == '02':
        # Speed control
        if data[1] == '01':
            left_speed(data[2])
        elif data[1] == '02':
            right_speed(data[2])
        else:
            print('Decode: Invalid command.')
    elif data[0]== '04':
        # Light control
        if data[1]== '00':
            open_main_light()
        elif data[1]== '01':
            close_main_light()
        else:
            print('Decode: Invalid command.')
    else:
        print('Decode: Invalid command.')


def control_server():
    rec_flag = False
    i = 0
    buffer = []
    # Start server
    control_server_socket = socket(AF_INET, SOCK_STREAM)
    control_server_socket.bind((control_host, control_port))
    control_server_socket.listen(1)
    while True:
        # Waiting connection from clients
        print('Server: Waiting for connection')
        control_client_socket, client_addr = control_server_socket.accept()
        print('Server: Accept from ', client_addr)
        while True:
            # Receive command from clients
            try:
                data = control_client_socket.recv(1)
                data = binascii.b2a_hex(data)
            except:
                print("Server: Error receiving")
                break
            # Parse command
            if not data:
                break
            if not rec_flag:
                # Parse header
                if data == 'ff':
                    buffer[:] = []
                    rec_flag = True
                    i = 0
            else:
                if data == 'ff':
                    # Parse footer
                    rec_flag = 0
                    if i == 3:
                        print('Server: Receive data', str(buffer)[1:len(str(buffer)) - 1])
                        command_decode(buffer)
                    i = 0
                else:
                    # Parse payoff
                    buffer.append(data)
                    i += 1
        # Close connection
        control_client_socket.close()


if __name__ == '__main__':
    marquee_light()
    control_server()
