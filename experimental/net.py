import tensorflow as tf


def build_cnn(img_in, num_actions, scope, reuse=False):
    with tf.variable_scope(scope, reuse=reuse):
        out = img_in
        with tf.variable_scope("convnet"):
            # original architecture
            out = tf.layers.conv2d(out, filters=32, kernel_size=8, strides=4, activation=tf.nn.relu)
            out = tf.layers.conv2d(out, filters=64, kernel_size=4, strides=2, activation=tf.nn.relu)
            out = tf.layers.conv2d(out, filters=64, kernel_size=3, strides=1, activation=tf.nn.relu)
        out = tf.layers.flatten(out)
        with tf.variable_scope("action_value"):
            out = tf.layers.dense(out, units=512, activation=tf.nn.relu)
            out = tf.layers.dense(out, units=num_actions, activation=None)
    return out


def build_mlp(obs_in, num_actions, scope, reuse=False, hidden_units=10):
    with tf.variable_scope(scope, reuse=reuse):
        fc1 = tf.layers.dense(obs_in, hidden_units, tf.nn.relu)
        return tf.layers.dense(fc1, num_actions)
