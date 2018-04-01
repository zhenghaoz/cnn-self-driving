import numpy as np
import tensorflow as tf
import math
import os.path
import pickle
from dataset import DataFile



class Policy:

    def __init__(self, model_file, data_file, memory_size=3):
        # Load policy model
        self.policy = Network()
        self.policy.load(model_file)
        # Create memory
        self.memory = []
        self.memory_ptr = 0
        self.memory_permission = True
        self.memory_size = memory_size
        self.memory_file = DataFile(data_file)

    def get_action(self, camera_frame, left_sensor, right_sensor, memory_mode):
        actions, salients = self.policy.predict([camera_frame])
        # Recover memory mode
        if not memory_mode:
            self.memory_permission = True
        # Save memory to file
        if self.memory_permission and memory_mode and left_sensor != right_sensor:
            self.memory_permission = False
            print('Fuck')
            mem_len = len(self.memory)
            if left_sensor:
                mem_actions = [1] * mem_len
            else:
                mem_actions = [0] * mem_len
            self.memory_file.append(self.memory, mem_actions)
        # Save to memory
        if self.memory_permission and memory_mode:
            if len(self.memory) < self.memory_size:
                self.memory.append(camera_frame)
            else:
                self.memory[self.memory_ptr] = camera_frame
            self.memory_ptr = (self.memory_ptr + 1) % self.memory_size
        # Self-driving
        return np.argmax(actions[0]), actions[0], salients[0,:,:,0]


class Network:

    # Model configuration

    INPUT_HEIGHT = 62
    INPUT_WIDTH = 198
    INPUT_CHANNEL = 3

    def __init__(self, learning_rate=0.1):
        """
        Create a PilotNet.
        :param learning_rate: learning rate for Adam optimizer
        """
        # Placeholders
        self.input_image = tf.placeholder(tf.float32, [None, self.INPUT_HEIGHT, self.INPUT_WIDTH, self.INPUT_CHANNEL])
        self.input_label = tf.placeholder(tf.int64, [None])
        # Convolution neural network
        conv1 = self.conv2d_norm_relu(self.input_image, 24, 5, 2)
        conv2 = self.conv2d_norm_relu(conv1, 36, 5, 2)
        conv3 = self.conv2d_norm_relu(conv2, 48, 5, 2)
        conv4 = self.conv2d_norm_relu(conv3, 64, 3)
        conv5 = self.conv2d_norm_relu(conv4, 64, 3)
        flat = tf.layers.flatten(conv5)
        fc1 = tf.layers.dense(flat, 1164, activation=tf.nn.relu)
        dropout1 = tf.layers.dropout(fc1, 0.5)
        fc2 = tf.layers.dense(dropout1, 100, activation=tf.nn.relu)
        dropout2 = tf.layers.dropout(fc2, 0.5)
        logits = tf.layers.dense(dropout2, 3)
        self.output_softmax = tf.nn.softmax(logits)
        self.output_label = tf.argmax(self.output_softmax, 1)
        self.output_acc = tf.reduce_mean(tf.cast(tf.equal(self.output_label, self.input_label), tf.float32))
        # Visual backpropagation
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
        # Loss and train step
        self.loss = tf.losses.softmax_cross_entropy(tf.one_hot(self.input_label, 3), logits)
        optimizer = tf.train.AdamOptimizer(learning_rate)
        self.train_step = optimizer.minimize(self.loss)
        # Create session
        self.sess = tf.Session()
        self.initialize()

    def initialize(self):
        self.sess.run(tf.global_variables_initializer())

    def fit(self, train_image: np.ndarray, train_label: np.ndarray,
            val_image: np.ndarray, val_label: np.ndarray, batch_size=100, print_iters=100, iters=1000, report_func=None) -> dict:
        """
        Fit model.
        :param train_image: images of training data set
        :param train_label: labels of training data set
        :param val_image: images of validation data set
        :param val_label: labels of validation data set
        :param batch_size: training batch size
        :param print_iters: print cost value every n iters
        :param iters: training iterations in each epoch
        :return: training history
        """
        history = {
            'loss': [],
            'train_acc': [],
            'val_acc': []
        }
        for i in range(iters):
            # Generate batch
            batch_index = np.random.choice(len(train_image), batch_size)
            batch_image = train_image[batch_index]
            batch_label = train_label[batch_index]
            # Train model
            loss, _ = self.sess.run([self.loss, self.train_step], {
                self.input_image: batch_image,
                self.input_label: batch_label
            })
            history['loss'].append(loss)
            # Print loss
            if (i + 1) % print_iters == 0:
                print('iter %d/%d, loss = %f' % (i+1, iters, loss))
                # Calculate accuracy
                train_acc = self.check_accuracy(train_image, train_label)
                val_acc = self.check_accuracy(val_image, val_label)
                history['train_acc'].append(train_acc)
                history['val_acc'].append(val_acc)
                # Call report function
                if report_func:
                    report_func(i, history)
        return history

    def predict(self, image) -> tuple:
        """
        Predict direction according road image.
        :param sess: computation session
        :param image: road image
        :return: predicted direction, salient map
        """
        directions, masks = self.sess.run([self.output_softmax, self.output_masks], {self.input_image: image})
        return directions, masks

    def check_accuracy(self, image: np.ndarray, label: np.ndarray, batch_size=100) -> float:
        """
        Check accuracy of data set (image, label).
        :param image: images of data set
        :param label: labels of data set
        :return: accuracy on data set
        """
        num_total = len(image)
        num_batch = int(math.ceil(num_total / batch_size))
        batch_accs = []
        batch_weight = []
        for i in range(num_batch):
            batch_images = image[i*batch_size:(i+1)*batch_size]
            batch_labels = label[i*batch_size:(i+1)*batch_size]
            batch_acc = self.sess.run(self.output_acc, {
                self.input_image: batch_images,
                self.input_label: batch_labels
            })
            batch_accs.append(batch_acc)
            batch_weight.append(len(batch_images))
        return np.average(batch_accs, weights=batch_weight)

    def save(self, filename):
        """
        Save parameters to files.
        :param filename: file name
        """
        saver = tf.train.Saver()
        saver.save(self.sess, filename)

    def load(self, filename):
        """
        Load parameters from files.
        :param filename: file name
        """
        saver = tf.train.Saver()
        saver.restore(self.sess, filename)

    @staticmethod
    def conv2d_norm_relu(inputs, filters, kernel_size, stride=1):
        """
        The procedure of "convolution -> batch normalization -> relu".
        :param inputs: the input tensor
        :param filters: the number of filters
        :param kernel_size: the size of convolution kernel
        :param stride: the stride of convolution
        :return: the output tensor
        """
        conv = tf.layers.conv2d(inputs, filters, kernel_size, stride)
        bn = tf.layers.batch_normalization(conv, 3)
        return tf.nn.relu(bn)

if __name__ == '__main__':
    import cv2
    file = DataFile('../data/20180220074817667425.data')
    for ob in file.data['observation']:
        cv2.imshow('A', ob)
        cv2.waitKey(0)
