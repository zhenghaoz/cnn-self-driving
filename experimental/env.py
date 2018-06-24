import socket
import time
import math
import io
import cv2
from PIL import Image
import numpy as np
import struct
from gym.spaces import Discrete, Box


class Env:

    def __init__(self, observation='Image', host='127.0.0.1', port=8082, time_out=1):
        self.action_space = Discrete(3)
        self.observation = observation
        if observation == 'Image':
            self.observation_space = Box(0, 255, [60,160,3])
        elif observation == 'Distance':
            self.observation_space = Box(-float('inf'), float('inf'), [10])
        else:
            raise ValueError("Unsupported observation " + observation)
        self.action_mao = [b'\x00',b'\x01',b'\x02']
        self.address = (host, port)
        self.time_out = time_out
        self.socket = None
        self.done = True

    def connect(self):
        # Connect
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.time_out)
        self.socket.connect(self.address)

    def close(self):
        self.socket.close()

    def send_action(self, action):
        assert self.action_space.contains(action)
        self.socket.send(self.action_mao[action])

    def recv_obs(self):
        # Get is_out
        data = self.socket.recv(1)
        is_out = struct.unpack('?', data)[0]
        # Get frame
        data = self.socket.recv(4)
        observation_size = struct.unpack('I', data)[0]
        data = self.socket.recv(observation_size)
        frame = np.asarray(Image.open(io.BytesIO(data)))
        frame = frame[60:,]
        # Get distance
        data = self.socket.recv(4)
        distance_size = struct.unpack('I', data)[0]
        distance = []
        for i in range(distance_size):
            data = self.socket.recv(4)
            distance.append(struct.unpack('f', data)[0])
        return is_out, frame, np.asarray(distance)

    def step(self, action):
        self.send_action(action)
        self.done, frame, distance = self.recv_obs()
        # Calculate reward
        reward = 0.0
        if action == 2 and not self.done:
            assert len(distance) == 10
            l = distance[0]
            r = distance[9]
            reward = (2 * l * r) / (l**2 + r**2)
        if math.isnan(reward):
            reward = 0.0
        # Return (observation, reward, done, info)
        info = {'distance': distance, 'frame': frame}
        if self.observation == 'Image':
            return frame, reward, self.done, info
        elif self.observation == 'Distance':
            return distance, reward, self.done, info

    def reset(self, with_info=False):
        # Reset env
        self.socket.send(b'\xff')
        self.done, frame, distance = self.recv_obs()
        info = {'distance': distance, 'frame': frame}
        if self.observation == 'Image':
            if with_info:
                return frame, info
            return frame
        elif self.observation == 'Distance':
            if with_info:
                return distance, info
            return distance
