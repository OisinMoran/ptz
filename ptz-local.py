import time
import RPi.GPIO as GPIO
from PCA9685 import PCA9685
from picamera2 import Picamera2
from libcamera import controls
import cv2
import numpy as np
import copy

from ultralytics import YOLO
import threading
import random


# Load the YOLO11 model
model = YOLO("yolo11n.pt")

# Global variable for class
TRACKED_CLASS = 49  # default to "orange"
TRACKED_CLASS = 39  # default to "bottle"

# PAN (0-180) ~ CENTRED 90
PAN_MIN, PAN_MAX = 10, 170
# TIL (30-100) ~ CENTRED 90
TIL_MIN, TIL_MAX = 20, 100

PAN = 1
TIL = 0
PAN_CENTRE = 90
TIL_CENTRE = 90

# IMG_WIDTH, IMG_HEIGHT = 640, 480 # 300ms inf
IMG_WIDTH, IMG_HEIGHT = 480, 320  # 100ms inf
CENTRE_X, CENTRE_Y = (IMG_WIDTH - 1) // 2, (IMG_HEIGHT - 1) // 2


# Camera setup
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (IMG_WIDTH, IMG_HEIGHT)},
    controls={
        # "FrameDurationLimits": (66_666, 66_666),  # ~15 FPS
        # "FrameDurationLimits": (33_333, 33_333),  # ~30 FPS
        "FrameDurationLimits": (16_666, 16_666),  # ~60 FPS
        "AfMode": controls.AfModeEnum.Continuous,
        "AfSpeed": controls.AfSpeedEnum.Fast,
        "AfWindows": [(CENTRE_X - 100, CENTRE_Y - 100, 200, 200)],
    },
)
picam2.configure(config)
picam2.start()


def zoom_at(img, zoom=1, angle=0, coord=None):
    cy, cx = [(i - 1) // 2 for i in img.shape[:-1]] if coord is None else coord[::-1]
    rot_mat = cv2.getRotationMatrix2D((cx, cy), angle, zoom)
    result = cv2.warpAffine(img, rot_mat, img.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result


def angle_to_pulse(angle, min_us=500, max_us=2500):
    pulse = min_us + (max_us - min_us) * (angle / 180)
    return int(pulse)


tracker = None
tracker_active = False

# Servo set up
pwm = PCA9685()
pwm.setPWMFreq(50)

# Centre
pwm.setRotationAngle(PAN, PAN_CENTRE)
pwm.setRotationAngle(TIL, TIL_CENTRE)

current_pan = PAN_CENTRE
current_tilt = TIL_CENTRE

# PID Controller Constants
Kp_x, Kp_y = 0.05, -0.08
Ki_x, Ki_y = 0.001, -0.001
Kd_x, Kd_y = 0.005, 0.005

int_x, int_y = 0, 0
prev_x_err, prev_y_err = 0, 0

x_tol, y_tol = 20, 20

last_time = time.time()

frame_count = 0
# inference for 480x320 is ~100ms or 10/s
# frame rate 60 FPS
DETECT_EVERY = 6

ORANGE = 49
BOTTLE = 39

prev_zoom = 1

model_success, tracker_success = False, False

while True:
    # CAPTURE
    frame = picam2.capture_array("main")
    if frame_count % DETECT_EVERY == 0:
        # DETECT YOLO
        results = model.predict(
            frame,
            imgsz=(IMG_WIDTH, IMG_HEIGHT),
            conf=0.2,
            classes=[TRACKED_CLASS],
            verbose=False,
        )
        result = results[0] if isinstance(results, list) else results
        boxes = result.boxes
        cls_ids = boxes.cls
        xywh = boxes.xywh
        xyxy = boxes.xyxy
        if len(cls_ids) > 0:
            model_success = True
            centroid_x, centroid_y, w, h = [int(x) for x in boxes.xywh[0]]
            x_1, y_1, x_2, y_2 = [int(x) for x in boxes.xyxy[0]]

            # Start more light-weight tracker
            bbox = (x_1, y_1, w, h)
            # tracker = cv2.TrackerKCF_create()
            tracker = cv2.TrackerCSRT_create()
            tracker.init(frame, bbox)
            tracker_active = True
        else:
            model_success = False
            int_x, int_y = 0, 0

    elif tracker_active:
        # DETECT LIGHTWEIGHT
        pre_tracker = time.time()
        tracker_success, bbox = tracker.update(frame)
        print("TRACKER TIME: ", time.time() - pre_tracker)
        if tracker_success:
            x, y, w, h = [int(v) for v in bbox]
            centroid_x = x + w // 2
            centroid_y = y + h // 2
            x_1, y_1, x_2, y_2 = x, y, x + w, y + h
        else:
            tracker_active = False
            int_x, int_y = 0, 0

    if model_success or tracker_success:
        # ANNOTATE
        _ = cv2.rectangle(frame, (x_1, y_1), (x_2, y_2), (30, 100, 170), 2)

        # ZOOM
        zoom = 0.8 * prev_zoom + 0.2 * min(
            max(0.4 * min(IMG_WIDTH / w, IMG_HEIGHT / h), 1), 10
        )
        frame = zoom_at(frame, zoom=zoom, coord=[centroid_x, centroid_y])
        _ = cv2.putText(
            frame,
            f"Zoom: {zoom:.1f}",
            (10, 30),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(255, 0, 0),
            thickness=1,
        )

        # PID
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        x_err = CENTRE_X - centroid_x
        y_err = CENTRE_Y - centroid_y

        int_x = 0.9 * int_x + x_err * dt
        int_y = 0.9 * int_y + y_err * dt

        d_x = x_err - prev_x_err
        d_y = y_err - prev_y_err

        prev_x_err, prev_y_err = x_err, y_err

        print("dt: ", dt)
        print("X: ", x_err, int_x, d_x)
        print("Y: ", y_err, int_y, d_y)

        if abs(x_err) > x_tol:
            target_pan = current_pan + (Kp_x * x_err) + (Ki_x * int_x) + (Kd_x * d_x)
            current_pan = max(min(target_pan, PAN_MAX), PAN_MIN)
            # pwm.setRotationAngle(PAN, current_pan)
            pwm.setServoPulse(PAN, angle_to_pulse(current_pan))
        if abs(y_err) > y_tol:
            target_tilt = current_tilt + (Kp_y * y_err) + (Ki_y * int_y) + (Kd_y * d_y)
            current_tilt = max(min(target_tilt, TIL_MAX), TIL_MIN)
            # pwm.setRotationAngle(TIL, current_tilt)
            pwm.setServoPulse(
                TIL, angle_to_pulse(current_tilt, min_us=800, max_us=2200)
            )
    frame_count += 1

    # Display
    cv2.imshow("Camera", frame)
    # cv2.imshow("Camera", annotated_frame)
    if cv2.waitKey(1) == ord("q"):
        break
