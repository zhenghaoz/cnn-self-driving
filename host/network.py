import tensorflow as tf
import numpy as np


class PilotNet:

    IMG_HEIGHT = 62
    IMG_WIDTH = 197
    IMG_CHANNEL = 3

    def __init__(self):

        # Placeholders
        self.input_images = tf.placeholder(tf.float32, [None, self.IMG_HEIGHT, self.IMG_WIDTH, self.IMG_CHANNEL])
        self.input_directions = tf.placeholder(tf.int32, [None])

        # Architecture
        conv1 = tf.layers.conv2d(self.input_images, 24, 5, 2)
        conv2 = tf.layers.conv2d(conv1, 36, 5, 2)
        conv3 = tf.layers.conv2d(conv2, 48, 5, 2)
        conv4 = tf.layers.conv2d(conv3, 64, 3)
        conv5 = tf.layers.conv2d(conv4, 64, 3)
        flat = tf.layers.flatten(conv5)
        fc1 = tf.layers.dense(flat, 1164)
        fc2 = tf.layers.dense(fc1, 100)
        fc3 = tf.layers.dense(fc2, 50)
        self.output_logits = tf.layers.dense(fc3, 3)
        self.output_directions = tf.nn.softmax(self.output_logits)

        # Visualization
        feature_map5 = tf.reduce_mean(conv5, 3, keep_dims=True)
        feature_map5_scaled = tf.layers.conv2d_transpose(feature_map5, 1, 3, kernel_initializer=tf.ones_initializer(), trainable=False)
        feature_map4 = tf.reduce_mean(conv4, 3, keep_dims=True) * feature_map5_scaled
        feature_map4_scaled = tf.layers.conv2d_transpose(feature_map4, 1, 3, kernel_initializer=tf.ones_initializer(), trainable=False)
        feature_map3 = tf.reduce_mean(conv3, 3, keep_dims=True) * feature_map4_scaled
        feature_map3_scaled = tf.layers.conv2d_transpose(feature_map3, 1, 5, 2, kernel_initializer=tf.ones_initializer(), trainable=False)
        feature_map2 = tf.reduce_mean(conv2, 3, keep_dims=True) * feature_map3_scaled
        feature_map2_scaled = tf.layers.conv2d_transpose(feature_map2, 1, 5, 2, kernel_initializer=tf.ones_initializer(), trainable=False)
        feature_map1 = tf.reduce_mean(conv1, 3, keep_dims=True) * feature_map2_scaled
        self.output_masks = tf.layers.conv2d_transpose(feature_map1, 1, 5, 2, kernel_initializer=tf.ones_initializer(), trainable=False)

    def train(self):
        pass

    def predict(self, sess, image):
        """
        Predict direction according road image.
        :param sess: computation session
        :param image: road image
        :return: predicted direction, salient map
        """
        directions, masks = sess.run([self.output_directions, self.output_masks], {self.input_images: [image]})
        return directions[0], masks[0]


