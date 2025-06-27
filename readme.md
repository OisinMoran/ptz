# PTZ Object Tracking Camera
A Pan Tilt Zoom object tracking camera that can update what it's tracking on the fly. Using a combination of the lightweight YOLO 11 model, and even-lighter-weight tradional CV, it gets over 20 FPS tracking on 480 x 320 video.

The best way to view and ✨ _interact_ ✨ with this (when it's on) is at [REDACTED]. Just let me know when you want me to turn it on and I'll give you the wonderful, surprisingly short URL. You can even select what type of thing you'd like to track!

## POV: your pirate gums have begun to bleed and I am tempting you with an orange // Results

![ezgif-1274c64c35e02c](https://github.com/user-attachments/assets/b6482efa-af75-43d2-b8a4-9d8669c886cb)

![image](https://github.com/user-attachments/assets/ab39047e-4f78-4d3d-9d61-f30fef2d1984)




## Hardware Components

Picture | Name | Cost
 :---: | :---: | ---:
<img src="https://github.com/user-attachments/assets/19d8fc6a-68e6-48ef-8493-6c3ed5bb928b" height="200"/> | Raspberry Pi 5 (8GB) | €106.01
<img src="https://github.com/user-attachments/assets/f40b19b7-f171-4143-a284-3847a370efdf" height="200"/> | Raspberry Pi Camera Module 3 | €40.06
<img src="https://github.com/user-attachments/assets/0cf76f95-c985-4026-a988-389821d0286a" height="200"/> | Waveshare 2-DOF Pan-Tilt Hat | €31.48
<img src="https://github.com/user-attachments/assets/b2acb193-53cb-4041-b7d9-5f29ec14194b" height="200"/> | 27W Power Supply | €13.79
<img src="https://github.com/user-attachments/assets/4f6c7cc5-b368-41d4-b284-1d35e877e050" height="200"/> | Orange | Had already, ate after
<img src="https://github.com/user-attachments/assets/db655853-39bc-4fdb-8daf-22e2ed0dd206" height="200"/> | Cholula Hot Sauce Bottle | Had already, still good
&nbsp;  | Total | €191.34

## Hardware Build Process:
1. Get camera working with Raspberry Pi
2. Assemble PT hat (magnetized screwdrivers are possibly _the_ most overlooked invention)
3. Combine PT hat with camera, camera with Raspberry Pi, _then_ PT hat with Raspberry Pi
4. Add Blutack before you knock it over or it becomes to powerful and knocks itself over

![image](https://github.com/user-attachments/assets/aa2a43aa-ed25-4385-8f89-7ec7e1e1e417)


## Software Process
1. Got some simple oldschool CV working initially to get digital zoom and tracking working without servo movement
2. Used this simple and speedy setup to get the servos working with a simple proportional controller
3. Got YOLO working on its own
4. Integrated YOLO into the tracking
5.  a
37. Tuning, tweaking, experimenting
38. Set up streaming site using Flask & ngrok


## Final Architecture & Specs
- 20 FPS tracking on 480 x 320 video
- Streaming via a flask app
- digital zoom (with some pan too)


further improvements
- ssd, cooler, coral
- separate threads for each process
- higher res, 
- modularize code and neaten
- add commandeer option to site (remote controls for camera)
- push model more (quantization, other optimizations)
- 
