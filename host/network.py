import cv2
import numpy as np
import tensorflow as tf


class PilotNet:

    # Model configuration

    INPUT_HEIGHT = 62
    INPUT_WIDTH = 197
    INPUT_CHANNEL = 3

    def __init__(self, learning_rate=0.1):
        # Placeholders
        self.input_images = tf.placeholder(tf.float32, [None, self.INPUT_HEIGHT, self.INPUT_WIDTH, self.INPUT_CHANNEL])
        self.input_directions = tf.placeholder(tf.int32, [None])
        # Architecture
        conv1 = tf.layers.conv2d(self.input_images, 24, 5, 2, activation=tf.nn.relu)
        conv2 = tf.layers.conv2d(conv1, 36, 5, 2, activation=tf.nn.relu)
        conv3 = tf.layers.conv2d(conv2, 48, 5, 2, activation=tf.nn.relu)
        conv4 = tf.layers.conv2d(conv3, 64, 3, activation=tf.nn.relu)
        conv5 = tf.layers.conv2d(conv4, 64, 3, activation=tf.nn.relu)
        flat = tf.layers.flatten(conv5)
        fc1 = tf.layers.dense(flat, 1164, activation=tf.nn.relu)
        fc2 = tf.layers.dense(fc1, 100, activation=tf.nn.relu)
        fc3 = tf.layers.dense(fc2, 50, activation=tf.nn.relu)
        self.output_logits = tf.layers.dense(fc3, 3)
        self.output_softmax = tf.nn.softmax(self.output_logits)
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
        # Cost
        self.loss = tf.losses.softmax_cross_entropy(tf.one_hot(self.input_directions, 3), self.output_logits)
        optimizer = tf.train.AdadeltaOptimizer(learning_rate)
        self.train_step = optimizer.minimize(self.loss)
        # Create session
        self.sess = tf.Session()
        self.sess.run(tf.global_variables_initializer())

    def fit(self, image: np.ndarray, label: np.ndarray, eppch=30):
        for i in range(eppch):
            loss, _ = self.sess.run([self.loss, self.train_step], {
                self.input_images: image,
                self.input_directions: label
            })
            # Calculate accuracy
            softmax = self.predict(image)[0]
            action = np.argmax(softmax, 0)
            acc = np.mean(action == label)
            print("training loss: %f, training accuracy: %f" % (loss, acc))

    def predict(self, image: np.ndarray) -> tuple:
        """
        Predict direction according road image.
        :param sess: computation session
        :param image: road image
        :return: predicted direction, salient map
        """
        directions, masks = self.sess.run([self.output_softmax, self.output_masks], {self.input_images: image})
        return directions, masks

    def save(self, filename):
        """
        Save parameters to files
        :param filename: file name
        """
        pass

    def load(self, filename):
        """
        Load parameters from files
        :param filename: file name
        """
        pass


if __name__ == "__main__":
    # Load 'data'
    L = cv2.imread('data/L.png')
    R = cv2.imread('data/R.png')
    U = cv2.imread('data/U.png')
    X = np.stack([L, R, U], 0)
    y = np.asarray([0, 1, 2])
    net = PilotNet()
    net.fit(X, y)

