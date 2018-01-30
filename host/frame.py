import cv2
import asset
import numpy as np


class FrameFactory:

    # Internal configuration

    DIRECTION_BAR_WIDTH = 20
    DIRECTION_BAR_HEIGHT = 100
    DIRECTION_BAR_MARGIN = 10
    DIRECTION_BAR_PADDING = 20
    DIRECTION_ICONS = [asset.ICON_LEFT_ARROW, asset.ICON_UP_ARROW, asset.ICON_RIGHT_ARROW]

    SENSOR_SIZE = 50
    SENSOR_PADDING = 20
    SENSOR_MARGIN = 20
    SENSOR_ICONS = [asset.ICON_INFRARED_SENSOR_LEFT, asset.ICON_INFRARED_SENSOR_RIGHT]

    def __init__(self, height, width, channel, sample_height, sample_width):
        self.frame = np.zeros([height, width, channel])
        self.mask = np.zeros([height, width, 1])
        self.direction = [0,0,0]
        self.sensor = [False, False]
        self.height = height
        self.width = width
        self.channel = channel
        self.sample_height = sample_height
        self.sample_width = sample_width

        # Compute sample region
        self.sample_left = 0
        self.sample_right = self.width
        self.sample_top = self.height-int(self.width/self.sample_width*self.sample_height)
        self.sample_bottom = self.height

    def set_frame(self, image):
        """
        Set video frame
        :param image: video frame
        """
        self.frame = image
        self.mask = np.zeros([image.shape[0], image.shape[1], 1])

    def set_salient(self, mask):
        """
        Set salient map of sampled region
        :param mask: salient map
        """
        self.mask = mask

    def set_direction(self, direction):
        """
        Set probabilities of three directions
        :param direction: probabilities
        """
        self.direction = direction

    def render(self):
        # Draw sensor
        sensor_top = self.SENSOR_PADDING
        sensor_bottom = sensor_top + self.SENSOR_SIZE
        for i in range(len(self.sensor)):
            sensor_right = self.width-self.SENSOR_PADDING-(self.SENSOR_MARGIN+self.SENSOR_SIZE)*i
            sensor_left = sensor_right-self.SENSOR_SIZE
            icon = cv2.imread(self.SENSOR_ICONS[-1-i])
            self.frame = self.draw_image(self.frame, icon, sensor_left, sensor_top, sensor_right, sensor_bottom)
        # Draw directions
        bar_overlay = self.frame.copy()
        icon_top = self.DIRECTION_BAR_PADDING
        icon_bottom = self.DIRECTION_BAR_PADDING+self.DIRECTION_BAR_WIDTH
        bar_botton = icon_bottom+self.DIRECTION_BAR_PADDING + self.DIRECTION_BAR_HEIGHT
        for i in range(len(self.direction)):
            # Draw background rectangle
            bar_left = self.DIRECTION_BAR_PADDING+(self.DIRECTION_BAR_WIDTH+self.DIRECTION_BAR_MARGIN)*i
            bar_right = bar_left+self.DIRECTION_BAR_WIDTH
            bar_top = icon_bottom + self.DIRECTION_BAR_PADDING
            bar_overlay = cv2.rectangle(bar_overlay, (bar_left,bar_top), (bar_right,bar_botton), (255,255,255), -1)
        self.frame = cv2.addWeighted(self.frame, 0.5, bar_overlay, 0.5, 0)
        for i in range(len(self.direction)):
            # Draw foreground rectangle
            bar_left = self.DIRECTION_BAR_PADDING+(self.DIRECTION_BAR_WIDTH+self.DIRECTION_BAR_MARGIN)*i
            bar_right = bar_left+self.DIRECTION_BAR_WIDTH
            bar_top = bar_botton-int(self.DIRECTION_BAR_HEIGHT*self.direction[i])
            self.frame = cv2.rectangle(self.frame, (bar_left,bar_top), (bar_right,bar_botton), (255,255,255), -1)
            # Draw icon
            icon = cv2.imread(self.DIRECTION_ICONS[i])
            self.frame = self.draw_image(self.frame, icon, bar_left, icon_top, bar_right, icon_bottom)
        # Draw sample area
        self.frame = cv2.rectangle(self.frame, (self.sample_left,self.sample_top), (self.sample_right-1,self.sample_bottom-1), (255,255,255))
        # Draw salient map
        min_weight = np.min(self.mask)
        max_weight = np.max(self.mask)
        mask_normed = (self.mask-min_weight)/(max_weight-min_weight)
        mask_scaled = cv2.resize(mask_normed, (self.sample_right-self.sample_left, self.sample_bottom-self.sample_top))
        mask_full = np.zeros([self.height, self.width, 1])
        mask_full[self.sample_top:self.sample_bottom, self.sample_left:self.sample_right, 0] = mask_scaled
        mask_color = np.array([0, 255, 0]).reshape([1, 1, 3])
        self.frame = self.frame * (1-mask_full) + mask_color * mask_full
        return self.frame.astype(np.uint8)

    def sample(self):
        """
        Sample for neural network from frame.
        :return: Sampled image
        """
        clip = self.frame[self.sample_top:self.sample_bottom, self.sample_left:self.sample_right, :]
        return cv2.resize(clip, (self.sample_width, self.sample_height))

    @staticmethod
    def draw_image(src, img, left, top, right, bottom, threshold=10):
        """
        Draw a image into another image, the dark area will be reduced.
        :param src: the image draw object to
        :param img: the image draw object from
        :param left: the left position of draw area
        :param top: the top position of draw area
        :param right: the right position of draw area
        :param bottom: the bottom position of draw area
        :param threshold: threshold for reducing
        :return: new image
        """
        # Resize image
        resize_width = right - left
        resize_height = bottom - top
        img = cv2.resize(img, (resize_width, resize_height))
        # Put img to src
        rows, cols, _ = img.shape
        roi = img[0:rows, 0:cols]
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        src_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
        img_fg = cv2.bitwise_and(img, img, mask=mask)
        dst = cv2.add(src_bg, img_fg)
        src[top:bottom, left:right] = dst
        return src
