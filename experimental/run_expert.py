#!/usr/bin/env python
import sys

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
        return self.sess.run(self.sy_out, {
            self.sy_obs: observations
        })

    def save(self, filename):
        """
        Save model
        :param filename: filename for model
        """
        saver = tf.train.Saver()
        saver.save(self.sess, filename)


def stdout_write(text):
    """
    Print without newline.
    :param text: the string to output
    """
    sys.stdout.write(text)
    sys.stdout.flush()


def expert_policy(info, threshold=0.6):
    """
    Expert policy.
    :param info: addition information from env
    :param threshold: threshold for steering
    :return: action
    """
    if 'distance' not in info.keys():
        return 2
    distance = info['distance']
    # Get left/right sensor's value
    assert len(distance) == 10
    left_distance = distance[0]
    right_distance = distance[9]
    # Normalize distance
    sum = left_distance + right_distance
    left_distance /= sum
    right_distance /= sum
    # Expert policy
    if right_distance - left_distance > threshold:
        return 1
    elif left_distance - right_distance > threshold:
        return 0
    return 2


def main():
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--obs', type=str, default='Image')
    parser.add_argument("--max_timesteps", type=int, default=1000)
    parser.add_argument('--num_rollouts', type=int, default=20, help='Number of expert roll outs')
    parser.add_argument('--dagger', type=int, default=0, help='Epoch of DAgger training')
    parser.add_argument('--batch_size', type=int, default=100)
    parser.add_argument('--n_iter', type=int, default=1000)
    parser.add_argument('--output', '-o', type=str)
    args = parser.parse_args()

    # Create environment
    max_steps = args.max_timesteps
    env = Env(args.obs)
    stdout_write('Expert data generating ')

    # Generate expert data
    returns_expert = []
    observations = []
    actions = []
    for i in range(args.num_rollouts):
        stdout_write('.')
        obs, info = env.reset(with_info=True)
        done = False
        total_reward = 0.
        steps = 0
        while not done:
            action = expert_policy(info)
            observations.append(obs)
            actions.append(action)
            obs, r, done, info = env.step(action)
            total_reward += r
            steps += 1
            if steps >= max_steps:
                break
        returns_expert.append(total_reward)

    print()

    # Report expert data
    print('returns', returns_expert)
    print('mean return', np.mean(returns_expert))
    print('std of return', np.std(returns_expert))

    # Create neural network
    net = NeuralNetwork(env.observation_space.shape, env.action_space.n)

    # Training
    loss_hist = []
    for epoch in range(args.dagger+1):
        returns_policy = []

        # Fit expert data
        loss_hist += net.fit(observations, actions, args.n_iter, args.batch_size)

        if epoch == args.dagger:
            stdout_write('Policy testing ')
        else:
            stdout_write('DAgger data generating (epoch %d/%d)' % (epoch+1, args.dagger))

        # Generate DAgger data
        for i in range(args.num_rollouts):
            stdout_write('.')
            obs, info = env.reset(with_info=True)
            done = False
            total_reward = 0.
            steps = 0
            while not done:
                # Generate actions by expert
                if epoch < args.dagger:
                    action_expert = expert_policy(info)
                    actions.append(action_expert)
                    observations.append(obs)
                # Generate observations by policy
                action_policy = net.predict([obs])[0]
                obs, r, done, info = env.step(action_policy)
                total_reward += r
                steps += 1
                if steps >= max_steps:
                    break
            returns_policy.append(total_reward)
        print()

        # Print performance
        print('returns', returns_policy)
        print('mean return', np.mean(returns_policy))
        print('std of return', np.std(returns_policy))

    # Save model
    if args.output:
        net.save(args.output)


if __name__ == '__main__':
    main()
