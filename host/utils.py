import cv2
import numpy as np


def frame_processor(image, model, sess, thickness=2, dir_pred=False, scope=False):
    height, width, _ = image.shape
    # Draw monitor scope
    monitor_left = 0
    monitor_right = width
    monitor_top = height - int(width / model.INPUT_WIDTH * model.INPUT_HEIGHT)
    monitor_bottom = height
    if scope:
        cv2.rectangle(image,
                      (monitor_left+thickness,monitor_top+thickness),
                      (monitor_right-thickness,monitor_bottom-thickness),
                      (255,255,255), thickness)
    # Sample and feed
    sample = image[monitor_top:monitor_bottom,monitor_left:monitor_right]
    sample = cv2.resize(sample, (model.INPUT_WIDTH,model.INPUT_HEIGHT))
    direction = model.sample(sess, sample)
    # Draw direction
    if dir_pred:
        direction_left = 20
        direction_top = 20
        direction_right = 100
        direction_bottom = 100
        direction_width = direction_right - direction_left
        direction_height = direction_bottom - direction_top
        direction_bar_height = direction_height * direction
        direction_bar_width = int(direction_width / 5)
        for i in range(len(direction_bar_height)):
            cv2.rectangle(image,
                          (direction_left+direction_bar_width*(2*i), direction_top),
                          (direction_left+direction_bar_width*(2*i+1), direction_bottom),
                          (255, 255, 255), thickness)
            cv2.rectangle(image,
                          (direction_left+direction_bar_width*(2*i), direction_bottom-int(direction_bar_height[i])),
                          (direction_left+direction_bar_width*(2*i+1), direction_bottom),
                          (255,255,255), -1)
    return image, direction