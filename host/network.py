import tensorflow as tf


class PilotNet:

    INPUT_HEIGHT = 66
    INPUT_WIDTH = 200
    INPUT_CHANNEL = 3

    def __init__(self):
        self.input = tf.placeholder(tf.float32, shape=[None,self.INPUT_HEIGHT,self.INPUT_WIDTH,self.INPUT_CHANNEL])

        norm = tf.layers.batch_normalization(self.input, 1)
        conv1 = tf.layers.conv2d(norm, 24, 5, 2)
        conv2 = tf.layers.conv2d(conv1, 36, 5, 2)
        conv3 = tf.layers.conv2d(conv2, 48, 5, 2)
        conv4 = tf.layers.conv2d(conv3, 64, 3)
        conv5 = tf.layers.conv2d(conv4, 64, 3)
        flat = tf.layers.flatten(conv5)
        fc1 = tf.layers.dense(flat, 1164)
        fc2 = tf.layers.dense(fc1, 100)
        fc3 = tf.layers.dense(fc2, 50)
        fc4 = tf.layers.dense(fc3, 10)
        self.output = tf.layers.dense(fc4, 3)
        self.action = tf.nn.softmax(self.output)

    def train(self):
        pass

    def sample(self, sess, image):
        return sess.run(self.action, {self.input: [image]})[0]


