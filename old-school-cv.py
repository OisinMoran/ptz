import time
import RPi.GPIO as GPIO
from PCA9685 import PCA9685
from picamera2 import Picamera2
from libcamera import controls
import cv2
import numpy as np
import copy

# PAN (0-180) ~ CENTRED 90
PAN_MIN, PAN_MAX = 10, 170
# TIL (30-80) ~ CENTRED 80
TIL_MIN, TIL_MAX = 30, 80

PAN = 1
TIL = 0
PAN_CENTRE = 90
TIL_CENTRE = 80

IMG_WIDTH, IMG_HEIGHT = 640, 480
CENTRE_X, CENTRE_Y = (IMG_WIDTH - 1) // 2, (IMG_HEIGHT - 1) // 2

# Servo set up
pwm = PCA9685()
pwm.setPWMFreq(50)
# Centre
pwm.setRotationAngle(PAN, PAN_CENTRE)
pwm.setRotationAngle(TIL, TIL_CENTRE)

current_pan = PAN_CENTRE
current_tilt = TIL_CENTRE

# Camera setup
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (IMG_WIDTH, IMG_HEIGHT)},
    controls={
        "FrameDurationLimits": (50000, 50000),  # 20 FPS
        "AfMode": controls.AfModeEnum.Continuous,
        "AfSpeed": controls.AfSpeedEnum.Fast,
        "AfWindows": [(CENTRE_X - 100, CENTRE_Y - 100, 200, 200)],
    },
)
picam2.configure(config)
picam2.set_controls({})
picam2.start()


def zoom_at(img, zoom=1, angle=0, coord=None):
    cy, cx = [(i - 1) // 2 for i in img.shape[:-1]] if coord is None else coord[::-1]
    rot_mat = cv2.getRotationMatrix2D((cx, cy), angle, zoom)
    result = cv2.warpAffine(img, rot_mat, img.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result


# prop constants
p_x, p_y = 0.02, -0.02
x_tol, y_tol = 0.5, 0.5

while True:
    frame = picam2.capture_array()
    b = frame[..., 0]
    g = frame[..., 1]
    r = frame[..., 2]
    pen_b = np.where(40 <= b, 255, 0) & np.where(b <= 160, 255, 0)
    pen_g = np.where(60 <= g, 255, 0)
    pen_r = np.where(0 <= r, 255, 0) & np.where(r <= 30, 255, 0)
    pen = pen_b & pen_g & pen_r
    # Dilate, open/close etc.
    kernel = np.ones((5, 5), np.uint8)
    opening = cv2.morphologyEx(pen.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    kernel = np.ones((10, 10), np.uint8)
    opening = cv2.morphologyEx(opening, cv2.MORPH_DILATE, kernel)
    # connected components
    output = cv2.connectedComponentsWithStats(opening, 8, cv2.CV_32S)
    numLabels, labels, stats, centroids = output
    biggest_area, biggest_comp = -1, -1
    biggest_stat = -1, -1, -1, -1
    b_x, b_y, b_w, b_h = -1, -1, -1, -1
    x, y, w, h = 1, 1, 1, 1
    for i in range(1, numLabels):
        # extract the connected component statistics for the current
        # label
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        if area > biggest_area:
            biggest_area = area
            biggest_comp = i
            b_x, b_y, b_w, b_h = x, y, w, h
    _ = cv2.rectangle(frame, (b_x, b_y), (b_x + b_w, b_y + b_h), (0, 255, 0), 1)
    zoom = min(max(0.2 * min(IMG_WIDTH / w, IMG_HEIGHT / h), 1), 10)
    zoomed_frame = zoom_at(frame, zoom=zoom)  # , coord=centroids[biggest_comp])
    _ = cv2.putText(
        zoomed_frame,
        f"Zoom: {zoom:.1f}",
        (10, 30),
        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
        fontScale=0.5,
        color=(255, 0, 0),
        thickness=1,
    )
    centroid_x, centroid_y = centroids[biggest_comp]
    x_err = CENTRE_X - centroid_x
    y_err = CENTRE_Y - centroid_y
    print(x_err, y_err)
    if abs(x_err) > x_tol:
        current_pan = max(min(current_pan + p_x * x_err, PAN_MAX), PAN_MIN)
        pwm.setRotationAngle(PAN, current_pan)
    if abs(y_err) > y_tol:
        current_tilt = max(min(current_tilt + p_y * y_err, TIL_MAX), TIL_MIN)
        pwm.setRotationAngle(TIL, current_tilt)
    cv2.imshow("Frame", zoomed_frame)
    if cv2.waitKey(1) == ord("q"):
        break

# cd ~/lg-master/Pan-Tilt_HAT_code/RaspberryPi/Servo_Driver/python
