import tensorflow as tf


def build_cnn(img_in, num_actions, scope, reuse=False):
    with tf.variable_scope(scope, reuse=reuse):
        out = img_in
        with tf.variable_scope("convnet"):
            # original architecture
            out = conv2d_norm_relu(out, filters=32, kernel_size=7, strides=2, activation=tf.nn.relu)
            out = conv2d_norm_relu(out, filters=64, kernel_size=5, strides=2, activation=tf.nn.relu)
            out = conv2d_norm_relu(out, filters=64, kernel_size=3, strides=1, activation=tf.nn.relu)
        out = tf.layers.flatten(out)
        with tf.variable_scope("action_value"):
            out = tf.layers.dense(out, units=512, activation=tf.nn.relu)
            out = tf.layers.dense(out, units=num_actions, activation=None)
    return out


def build_mlp(obs_in, num_actions, scope, reuse=False, hidden_units=10):
    with tf.variable_scope(scope, reuse=reuse):
        fc1 = tf.layers.dense(obs_in, hidden_units, tf.nn.relu)
        return tf.layers.dense(fc1, num_actions)


def conv2d_norm_relu(inputs, filters, kernel_size, strides, activation):
    """
    The procedure of "convolution -> batch normalization -> relu".
    :param inputs: the input tensor
    :param filters: the number of filters
    :param kernel_size: the size of convolution kernel
    :param stride: the stride of convolution
    :return: the output tensor
    """
    conv = tf.layers.conv2d(inputs, filters, kernel_size, strides, activation=activation)
    bn = tf.layers.batch_normalization(conv, 3)
    return tf.nn.relu(bn)