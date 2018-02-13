import cv2
import config
import numpy as np


class LaneDetector:

    def __init__(self, upper_threshold: int=200,
                 lower_threshold: int=100,
                 max_angle: int=np.pi/3,
                 hough_threshold: int=16):
        """
        Create a reward detector
        :param upper_threshold: the upper threshold for the Canny edge detector
        :param lower_threshold: the lower threshold for the Canny edge detector
        :param max_angle: lines have larger angles will be ignored
        :param hough_threshold: the threshold for the Hough line detector
        """
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold
        self.max_angle = max_angle
        self.hough_threshold = hough_threshold

    def detect(self, image: np.ndarray,
               draw_hough_line: bool=True,
               draw_mean_line: bool=True,
               draw_center_line: bool=True) -> tuple:
        """
        Detect the center line on the road and return reward score.
        :param image: the input image
        :param draw_hough_line: whether drawing lines detected by Hough
        :param draw_mean_line: whether drawing lines classified
        :param draw_center_line: whether drawing the center line
        :return: (the reward score, the marked image)
        """
        height, width, _ = image.shape
        # Convert image to gray scale
        gray_img = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # Canny edge detection
        edge_img = cv2.Canny(gray_img, self.lower_threshold, self.upper_threshold)
        # Hough line detection
        lines_rho_theta = cv2.HoughLines(edge_img, 1, np.pi / 180, self.hough_threshold)
        # Return max score when there is no line
        if lines_rho_theta is None:
            return 1.0, image
        # Convert line representation
        lines_rho_theta = lines_rho_theta[:, 0, :]
        lefts = []
        rights = []
        for rho, theta in lines_rho_theta:
            # Remove lines with big theta
            if np.abs(np.pi/2 - theta) < np.pi/2 - self.max_angle:
                continue
            if theta == 0:      # Vertical line
                x0 = x1 = rho
            else:               # Diagonal line
                x0 = int(rho / np.cos(theta))
                y0 = int(rho / np.sin(theta))
                x1 = int((y0 - height) * np.tan(theta))
            # Classify lines
            l, r = self.neighbor_mean(gray_img, x0, x1)
            if l < r:
                lefts.append([x0, x1])
            elif l > r:
                rights.append([x0, x1])
            # Draw hough line
            if draw_hough_line:
                cv2.line(image, (x0, 0), (x1, height), (0, 0, 255), 2)
        # Get average
        left = np.mean(lefts, axis=0).astype(np.int32) if len(lefts) > 0 else [0, 0]
        right = np.mean(rights, axis=0).astype(np.int32) if len(rights) > 0 else [width, width]
        left_top, left_bottom = left
        right_top, right_bottom = right
        top = int((left_top + right_top) / 2)
        bottom = int((left_bottom + right_bottom) / 2)
        # Draw lines
        if draw_mean_line:
            cv2.line(image, (left_top, 0), (left_bottom, height), (0, 255, 0), 2)
            cv2.line(image, (right_top, 0), (right_bottom, height), (0, 255, 0), 2)
        if draw_center_line:
            cv2.line(image, (top, 0), (bottom, height), (255, 0, 0), 2)
        return self.reward_function(height, width, top, bottom), image

    @staticmethod
    def reward_function(height: int, width: int, top: int, bottom: int) -> float:
        """
        The reward function for reinforcement learning: R(d,theta) = cos(theta)-d
        where d is the distance to the center of the road, and the theta is the
        angle between the image and the center line on the road. The center line
        is represented by two points [0,top] and [height,bottom].
        :param height: the height of the input image
        :param width: the width of the input image
        :param top: the top of [0,top]
        :param bottom: the bottom of [height,bottom]
        :return: the reward score
        """
        d = np.abs(width / 2 - top) / width
        theta = np.arctan(np.abs(top - bottom) / height)
        return np.cos(theta) - d

    @staticmethod
    def neighbor_mean(image: np.ndarray, top: int, bottom: int, distance: int=1) -> tuple:
        """
        Get mean values of neighbors (left neighbors and right neighbors) of a line
        represented by two points [0,top] and [height,bottom].
        :param image: the input image
        :param top: the top of [0,top]
        :param bottom: the bottom of [height,bottom]
        :param distance: the distance to neighbors
        :return: (the mean values of left neighbors, the mean value of right neighbors)
        """
        # Get points on line
        height = image.shape[0]
        width = image.shape[1]
        y = np.arange(0, height, 1)
        ratio = y / height
        x = (top*(1-ratio) + bottom*ratio).astype(np.int32)
        # Shift from line
        left_x = x - distance
        right_x = x + distance
        # Range check
        left_mask = np.logical_and(left_x >= 0, left_x < width)
        left_x = left_x[left_mask]
        left_y = y[left_mask]
        right_mask = np.logical_and(right_x >= 0, right_x < width)
        right_x = right_x[right_mask]
        right_y = y[right_mask]
        # Sample pixels from two regions
        left_pixel = image[left_y, left_x]
        right_pixel = image[right_y, right_x]
        # Get average of pixels
        left_mean = np.mean(left_pixel)
        right_mean = np.mean(right_pixel)
        return left_mean, right_mean


# Test routine
if __name__ == '__main__':
    detector = LaneDetector()
    stream = cv2.VideoCapture(config.URL_STREAM)
    while True:
        _, raw = stream.read()
        cv2.imshow('RewardDetector', detector.detect(raw[-50:, :])[1])
        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
