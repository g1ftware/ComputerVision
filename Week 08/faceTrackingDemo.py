import os
import argparse
import numpy as np
import cv2
import matplotlib.pyplot as plt
from goodFeaturesToTrackFromFace import detect as ShiTomasi_detect
from skimage.transform import SimilarityTransform
from skimage.measure import ransac
import matplotlib.animation as animation


if os.path.isdir('/coursedata123'):
    course_data_dir = '/coursedata1235'
elif os.path.isdir('../data'):
    course_data_dir = '../data'
else:
    # Specify course_data_dir on your machine
    course_data_dir = '/notebooks/compvis2024/'

print('The data directory is %s' % course_data_dir)
data_dir = os.path.join(course_data_dir, 'exercise-08')
print('Data stored in %s' % data_dir)

def faceTracker(input_file):
    #
    # This demo illustrates an application of Lucas-Kanade optical flow
    #
    # Steps:
    #   1) detect face region using pretrained haarcascade classifiers
    #   2) detect good features to track from face region using Shi-Tomasi corner detector
    #   3) track the points using the Lucas-Kanade optical flow
    #

    # setup a video capture from file (webcam also possible, for that see OpenCV docs)
    # Choose the source video
    cap = cv2.VideoCapture(data_dir+'/'+ input_file)

    # read the first frame from the video file and convert to grayscale
    ret, frame = cap.read() 
    old_frame = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # detect points to track, take a look at goodFeaturesToTrackFromFace.py
    bboxPoints, points = ShiTomasi_detect(gray, data_dir)

    # create a mask image for drawing the trails of the tracked points
    mask = np.zeros_like(old_frame)

    # display the video and track the points
    oldPoints = points
    trackingAlive = True

    frames = []
    while cap.isOpened():

        # get the next frame
        ret, frame = cap.read()
        if not ret:
            break

        # esc breaks the loop, also wait 30ms between every frame
        k = cv2.waitKey(30) & 0xff
        if k == 27:
            break

        # convert to grayscale
        gray_new = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # params for Lucas-Kanade optical flow
        winSize = 31#9
        maxLevel = 4#1
        maxCount = 4#2

        if trackingAlive == True:
            # track the points (note that some points may be lost)
            points, isFound, err = cv2.calcOpticalFlowPyrLK(gray, gray_new, 
                                                oldPoints, None, winSize = (winSize, winSize), maxLevel = maxLevel, 
                                                criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, maxCount, 0.03))

            visiblePoints = points[isFound==1]
            oldInliers = oldPoints[isFound==1]

            # need at least three points (otherwise ransac raises error and tracks are lost)
            if visiblePoints.shape[0] > 2:

                # estimate the geometric transformation between the old points and 
                # the new points and eliminate outliers
                tform, inliers = ransac((oldInliers, visiblePoints), SimilarityTransform, min_samples=2,
                                   residual_threshold=2, max_trials=200)

                H1to2p = tform.params
                visiblePoints = visiblePoints[inliers, :]
                oldInliers = oldInliers[inliers, :]

                # apply the transformation to the bounding box points
                bboxPoints_homog = np.hstack((bboxPoints, np.ones((bboxPoints.shape[0], 1))))
                bboxPoints_new = np.dot(H1to2p, bboxPoints_homog.T)
                bboxPoints_new = bboxPoints_new[:2,:] / bboxPoints_new[2,:]
                bboxPoints_new = bboxPoints_new.T
                bboxPoints = bboxPoints_new

                bboxPoints_new = bboxPoints_new.astype(int)
                bboxPoints_new = bboxPoints_new.reshape((-1, 1, 2))

                # insert a bounding box around the object being tracked
                cv2.polylines(frame, [bboxPoints_new], True, (0, 255, 255), 3)

                # display tracked points
                for i, (new, old) in enumerate(zip(visiblePoints, oldInliers)):
                    a, b = new.ravel()
                    c, d = old.ravel()
                    mask = cv2.line(mask, (int(a), int(b)),(int(c), int(d)), (255,255,255), 2)
                    frame = cv2.circle(frame, (int(a), int(b)), 2, (255, 255, 255), -1)

                # visualize tracks
                mask = 0.7 * mask
                oldPoints = visiblePoints.reshape(-1, 1, 2)
                gray = gray_new.copy()

                # display the number of tracked points
                cv2.putText(frame, 'Number of tracked points: ' + str(visiblePoints.shape[0]), (20,30), 0, 1.1, (255,255,255))
                frame = cv2.add(frame, np.uint8(mask))
                frame = plt.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), animated=True)
                frames.append([frame])
            else:
                trackingAlive = False

    # close everything
    cap.release()
    return(frames)
