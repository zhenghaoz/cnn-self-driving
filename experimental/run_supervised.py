#!/usr/bin/env python

import pickle

import numpy as np
import tensorflow as tf

from env import Env
from net import build_cnn, build_mlp


class NeuralNetwork:

    def __init__(self, obs_dim, num_actions):
        """
        Create a neural network with a single hidden layer.
        :param obs_dim: the dimension of observations
        :param num_actions: the number of discrete actions
        """
        # Placeholder
        self.sy_obs = tf.placeholder(tf.float32, shape=[None] + list(obs_dim))
        self.sy_act = tf.placeholder(tf.int32, shape=[None])
        # Network
        if len(obs_dim) == 1:
            self.sy_logit = build_mlp(self.sy_obs, num_actions, "mlp")
        elif len(obs_dim) == 3:
            self.sy_logit = build_cnn(self.sy_obs, num_actions, "cnn")
        else:
            raise ValueError("Unsupported observation dimension " + obs_dim)
        self.sy_softmax = tf.nn.softmax(self.sy_logit, 1)
        self.sy_out = tf.argmax(self.sy_logit, 1)
        # Train step
        self.sy_loss = tf.losses.softmax_cross_entropy(tf.one_hot(self.sy_act, num_actions), self.sy_logit, reduction=tf.losses.Reduction.MEAN)
        train_optimizer = tf.train.AdamOptimizer()
        self.train_step = train_optimizer.minimize(self.sy_loss)
        # Initialize
        self.sess = tf.Session()
        self.sess.run(tf.global_variables_initializer())

    def fit(self, observations, actions, iter, batch_size=1000, print_iter=100):
        """
        Train the neural network.
        :param observations: observations for training
        :param actions: actions for training
        :param iter: the number of training iterations
        :param batch_size: the size of training batch
        :param print_iter: when to print loss
        :return: the history of loss
        """
        train_size = len(observations)
        loss_hist = []
        observations = np.asarray(observations)
        actions = np.asarray(actions)
        for i in range(iter):
            batch_index = np.random.choice(np.arange(0, train_size), batch_size)
            batch_obs = observations[batch_index]
            batch_acts = actions[batch_index]
            batch_loss, _ = self.sess.run([self.sy_loss, self.train_step], {
                self.sy_obs: batch_obs,
                self.sy_act: batch_acts
            })
            loss_hist.append(batch_loss)
            if i % print_iter == 0:
                print('iter %d/%d, loss %f' % (i, iter, batch_loss))
        return loss_hist

    def predict(self, observations):
        """
        Predict actions of observations.
        :param observations: observations for predicting
        :return: actions
        """
        return self.sess.run([self.sy_out, self.sy_softmax], {
            self.sy_obs: observations
        })

    def load(self, filename):
        saver = tf.train.Saver()
        saver.restore(self.sess, filename)

    def save(self, filename):
        """
        Save model
        :param filename: filename for model
        """
        saver = tf.train.Saver()
        saver.save(self.sess, filename)


def read_data(data_file):
    with open(data_file, 'rb') as file:
        data = pickle.load(file)
        observations = np.asarray(data['observation'])
        actions = np.asarray(data['action'])
        assert len(observations) == len(actions)
        return observations, actions


def main():
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max_timesteps", type=int, default=1000)
    parser.add_argument('--num_rollouts', type=int, default=20, help='Number of expert roll outs')
    parser.add_argument('--batch_size', type=int, default=100)
    parser.add_argument('--n_iter', type=int, default=1000)
    parser.add_argument('--pre_train', '-p', type=str)
    parser.add_argument('--output', '-o', type=str)
    parser.add_argument('--shake_avoid', '-sa', action='store_true')
    args = parser.parse_args()

    # Create environment
    max_steps = args.max_timesteps
    env = Env('Image')

    # Setup data set
    observations, actions = read_data('dataset_sim.dat')

    # Create neural network
    net = NeuralNetwork(env.observation_space.shape, env.action_space.n)

    if args.pre_train:
        net.load(args.pre_train)

    # Fit expert data
    net.fit(observations, actions, args.n_iter, args.batch_size)

    # Save model
    if args.output:
        net.save(args.output)

    returns_policy = []
    actions = []
    env.connect()
    for i in range(args.num_rollouts):
        obs, info = env.reset(with_info=True)
        done = False
        total_reward = 0.
        steps = 0
        while not done:
            a, b = net.predict([obs])
            action_policy = a[0]
            if args.shake_avoid and len(actions) >= 2 and actions[-1] + actions[-2] == 1:
                action_policy = 2
            actions.append(action_policy)
            obs, r, done, info = env.step(action_policy)
            total_reward += r
            steps += 1
            if steps >= max_steps:
                break
        returns_policy.append(total_reward)
    env.close()
    print()

    # Print performance
    print('returns', returns_policy)
    print('mean return', np.mean(returns_policy))
    print('std of return', np.std(returns_policy))


if __name__ == '__main__':
    main()
