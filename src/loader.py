import glob
import os
import os.path

import cv2
import numpy as np
import pandas as pd
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from sklearn.preprocessing import LabelEncoder


class DataLoader:

    def __init__(self, path, test_size=0.3, mirror=False):
        # Save old work directory
        owd = os.getcwd()
        # Extract file list
        file_list = []
        os.chdir(path)
        for mkv_file in glob.glob("*.mkv"):
            file, _ = mkv_file.split('.')
            csv_file = file + '.csv'
            if os.path.isfile(csv_file):
                file_list.append(file)
        # Load data
        images = []
        labels = np.array([])
        for file in file_list:
            csv_file = file + '.csv'
            mkv_file = file + '.mkv'
            print('Loading data from (%s, %s)' % (mkv_file, csv_file))
            # Read csv
            csv = pd.read_csv(csv_file)
            labels = np.append(labels, csv['Action'])
            # Read video
            video = cv2.VideoCapture(mkv_file)
            ret = True
            while ret:
                ret, frame = video.read()
                if ret:
                    images.append(frame)
        images = np.asarray(images)
        assert np.shape(labels)[0] == np.shape(images)[0]
        # Data augmentation
        if mirror:
            mirror_images = np.flip(images, 2)
            mirror_labels = np.zeros_like(labels)
            num_total = len(labels)
            for i in range(num_total):
                # Mirror actions
                if labels[i] == Qt.Key_W:
                    mirror_labels[i] = Qt.Key_W
                elif labels[i] == Qt.Key_A:
                    mirror_labels[i] = Qt.Key_D
                elif labels[i] == Qt.Key_D:
                    mirror_labels[i] = Qt.Key_A
                if (i+1) % 100 == 0:
                    print('Data augmentation %f%%' % ((i+1)/num_total*100))
            print('Data augmentation completed')
            labels = np.concatenate([labels, mirror_labels])
            images = np.concatenate([images, mirror_images])
        # Label encode
        encoder = LabelEncoder()
        labels = encoder.fit_transform(labels)
        # Train test split
        num_total = labels.shape[0]
        num_test = int(num_total * test_size)
        index = np.random.permutation(num_total)
        test_index, train_index = index[:num_test], index[num_test:]
        self.train_images = images[train_index]
        self.train_labels = labels[train_index]
        self.test_images = images[test_index]
        self.test_labels = labels[test_index]
        # Restore work directory
        os.chdir(owd)


if __name__ == '__main__':
    loader = DataLoader('video', mirror=True)
    print('Train images shape:', np.shape(loader.train_images))
    print('Train labels shape:', np.shape(loader.train_labels))
    print('Test images shape', np.shape(loader.test_images))
    print('Test labels shape', np.shape(loader.test_labels))
