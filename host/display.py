import cv2
import asset
import config
import numpy as np
from reward import RewardDetector


class DisplayEngine:

    # Internal configuration

    DIRECTION_WIDTH = 20
    DIRECTION_HEIGHT = 100
    DIRECTION_MARGIN = 10
    DIRECTION_PADDING = 20
    DIRECTION_ICONS = [
        asset.ICON_LEFT_ARROW,
        asset.ICON_UP_ARROW,
        asset.ICON_RIGHT_ARROW
    ]

    def __init__(self, height: int, width: int, channel: int,
                 watch_height: int, watch_width: int, detect_height: int):
        """
        Create a display engine.
        :param height: the height of the frame
        :param width: the width of the frame
        :param channel: the channel of the frame
        :param watch_height: the height of the watch region
        :param watch_width: the width of the watch region
        :param detect_height: the height of the detect region
        """
        self.frame_img = np.zeros([height, width, channel])
        self.direction = [0,0,0]
        self.height = height
        self.width = width
        self.channel = channel
        # Watch region
        self.watch_height = watch_height
        self.watch_width = watch_width
        self.watch_left = 0
        self.watch_right = self.width
        self.watch_top = self.height - int(self.width / self.watch_width * self.watch_height)
        self.watch_bottom = self.height
        self.mask = None
        # Detect region
        self.detect_height = detect_height
        self.detected = None

    def set_frame(self, image: np.ndarray):
        """
        Set current video frame
        :param image: current video frame
        """
        height, width, channel = image.shape
        assert height == self.height
        assert width == self.width
        assert channel == self.channel
        # Reset frame
        self.frame_img = image
        # Clear mask
        self.mask = None
        # Clear detected
        self.detected = None

    def set_salient(self, mask: np.ndarray):
        """
        Feed the salient map of current sampled region back
        :param mask: current salient map
        """
        height, width = mask.shape
        assert height == self.watch_height
        assert width == self.watch_width
        self.mask = mask

    def set_detected(self, detected: np.ndarray):
        """
        Feed the detection result back.
        :param detected: detection result
        """
        height, width, _ = detected.shape
        assert height == self.detect_height
        assert width == self.width
        self.detected = detected

    def set_direction(self, direction: list):
        """
        Feed probabilities of three directions back.
        :param direction: probabilities
        """
        assert len(direction) == 3
        assert np.sum(direction) == 1
        self.direction = direction

    def render(self, draw_salient: bool=True, draw_direction=True, draw_watch=True, draw_detected=True):
        """
        Render a frame for display.
        :param draw_salient: whether draw the salient map
        :param draw_direction: whether draw direction probabilities
        :param draw_watch: whether draw the watch region
        :param draw_detected: whether draw the detect region
        :return: the rendered image
        """
        output_img = self.frame_img.copy()
        # Draw detected area
        if draw_detected and self.detected is not None:
            output_img[-self.detect_height:,:] = self.detected
        # Draw directions
        if draw_direction:
            bar_overlay = output_img.copy()
            icon_top = self.DIRECTION_PADDING
            icon_bottom = self.DIRECTION_PADDING + self.DIRECTION_WIDTH
            bar_bottom = icon_bottom+self.DIRECTION_PADDING + self.DIRECTION_HEIGHT
            for i in range(len(self.direction)):
                # Draw background rectangle
                bar_left = self.DIRECTION_PADDING + (self.DIRECTION_WIDTH + self.DIRECTION_MARGIN) * i
                bar_right = bar_left+self.DIRECTION_WIDTH
                bar_top = icon_bottom + self.DIRECTION_PADDING
                bar_overlay = cv2.rectangle(bar_overlay, (bar_left,bar_top), (bar_right,bar_bottom), (255,255,255), -1)
            output_img = cv2.addWeighted(output_img, 0.5, bar_overlay, 0.5, 0)
            for i in range(len(self.direction)):
                # Draw foreground rectangle
                bar_left = self.DIRECTION_PADDING + (self.DIRECTION_WIDTH + self.DIRECTION_MARGIN) * i
                bar_right = bar_left+self.DIRECTION_WIDTH
                bar_top = bar_bottom-int(self.DIRECTION_HEIGHT * self.direction[i])
                output_img = cv2.rectangle(output_img, (bar_left, bar_top), (bar_right, bar_bottom), (255, 255, 255), -1)
                # Draw icon
                icon = cv2.imread(self.DIRECTION_ICONS[i])
                output_img = self.draw_image(output_img, icon, bar_left, icon_top, bar_right, icon_bottom)
        # Draw watch area
        if draw_watch:
            output_img = cv2.rectangle(output_img, (self.watch_left, self.watch_top), (self.watch_right - 1, self.watch_bottom - 1), (255, 255, 255))
        # Draw salient map
        if draw_salient and self.mask is not None:
            min_weight = np.min(self.mask)
            max_weight = np.max(self.mask)
            if np.abs(max_weight-min_weight) > 0:
                mask_normed = (self.mask-min_weight)/(max_weight-min_weight)
                mask_scaled = cv2.resize(mask_normed, (self.watch_right - self.watch_left, self.watch_bottom - self.watch_top))
                mask_full = np.zeros([self.height, self.width, 1])
                mask_full[self.watch_top:self.watch_bottom, self.watch_left:self.watch_right, 0] = mask_scaled
                mask_color = np.array([0, 255, 0]).reshape([1, 1, 3])
                output_img = output_img * (1 - mask_full) + mask_color * mask_full
        return output_img.astype(np.uint8)

    def watch_sample(self) -> np.ndarray:
        """
        Sample for neural network.
        :return: the sampled image
        """
        clip = self.frame_img[self.watch_top:self.watch_bottom, self.watch_left:self.watch_right, :]
        return cv2.resize(clip, (self.watch_width, self.watch_height))

    def detect_sample(self) -> np.ndarray:
        """
        Sample for reward detector.
        :return: the sampled image
        """
        return self.frame_img[-self.detect_height:,:].copy()

    @staticmethod
    def draw_image(src: np.ndarray, img: np.ndarray,
                   left: int, top: int, right: int, bottom: int, threshold: int=10) -> np.ndarray:
        """
        Draw a image into another image, the dark area will be reduced.
        :param src: the image draw object to
        :param img: the image draw object from
        :param left: the left position of draw area
        :param top: the top position of draw area
        :param right: the right position of draw area
        :param bottom: the bottom position of draw area
        :param threshold: the threshold for reducing
        :return: the new image
        """
        # Resize image
        resize_width = right - left
        resize_height = bottom - top
        img = cv2.resize(img, (resize_width, resize_height))
        # Put img to src
        rows, cols, _ = img.shape
        roi = src[top:bottom, left:right]
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        src_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
        img_fg = cv2.bitwise_and(img, img, mask=mask)
        dst = cv2.add(src_bg, img_fg)
        src[top:bottom, left:right] = dst
        return src


# Test routine
if __name__ == '__main__':
    engine = DisplayEngine(config.FRAME_HEIGHT,
                           config.FRAME_WIDTH,
                           config.FRAME_CHANNEL, 20, 100, 50)
    detector = RewardDetector()
    stream = cv2.VideoCapture(config.URL_STREAM)
    while True:
        _, raw = stream.read()
        engine.set_frame(raw)
        engine.set_direction([0.2,0.5,0.3])
        watch = engine.watch_sample()
        engine.set_salient(np.random.randn(watch.shape[0], watch.shape[1]))
        detect = engine.detect_sample()
        _, detcted = detector.detect(detect)
        engine.set_detected(detcted)
        cv2.imshow('DisplayEngine', engine.render())
        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
