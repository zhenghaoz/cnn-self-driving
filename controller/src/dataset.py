import os
import os.path
import pickle

import numpy as np


class DataFile:

    def __init__(self, data_file):
        self.data_file = data_file
        # Create file if not existed
        if not os.path.exists(data_file):
            data = {'observation': [], 'action': []}
            with open(data_file, 'wb') as file:
                pickle.dump(data, file)
        # Load data
        with open(self.data_file, 'rb') as file:
            self.data = pickle.load(file)

    def append(self, observation, action):
        self.data['action'] += action
        self.data['observation'] += observation
        with open(self.data_file, 'wb') as file:
            pickle.dump(self.data, file)

    def remove(self, index):
        assert 0 <= index <= len(self.data["observation"])
        del self.data["observation"][index]
        del self.data["action"][index]
        with open(self.data_file, 'wb') as file:
            pickle.dump(self.data, file)

    def gen_train_set(self, test_size=0.3, mirror=True, random_seed=0):
        observations = np.asarray(self.data['observation'])
        actions = np.asarray(self.data['action'])
        assert len(observations) == len(actions)
        # Data augmentation
        if mirror:
            mirror_observations = np.flip(observations, 2)
            mirror_actions = np.zeros_like(actions)
            num_total = len(actions)
            for i in range(num_total):
                # Mirror actions
                if actions[i] == 2:
                    mirror_actions[i] = 2
                elif actions[i] == 0:
                    mirror_actions[i] = 1
                elif actions[i] == 1:
                    mirror_actions[i] = 0
            actions = np.concatenate([actions, mirror_actions])
            observations = np.concatenate([observations, mirror_observations])
        # Train misc split
        num_total = actions.shape[0]
        num_test = int(num_total * test_size)
        np.random.seed(random_seed)
        index = np.random.permutation(num_total)
        test_index, train_index = index[:num_test], index[num_test:]
        return observations[train_index], actions[train_index], observations[test_index], actions[test_index]
