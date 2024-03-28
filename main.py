import json
import math
import sys
from enum import Enum

import cv2
import face_recognition
import numpy as np
from loguru import logger

from database import FacesDatabase

# video start of x & y
FACES_FOLDER = "assets/faces"
start_x = 165
start_y = 320
factor = 0.5

# Mode picture start of x & y
mp_x = 1365
mp_y = 70
mp_w = 492
mp_h = 938

# student picture start of x & y
st_x = 1460
st_y = 180
st_w = 300
st_h = 400

bg_image = cv2.imread("assets/background.png")

ACCEPT_COUNTER = 2
RESET_COUNTER = 4
ATTENDANCE_TIME_DELTA = 300  # 300 seconds = 5 minutes (5 * 60)


class CurrentMode(Enum):
    """
    Different modes of the application
    """
    Waiting = "Waiting"
    Found = "Found"
    Unknown = "Unknown"
    Marked = "Marked"
    AlreadyMarked = "AlreadyMarked"


mode_images = {}
mode_images["Waiting"] = cv2.imread(f"assets/fillers/{CurrentMode.Waiting.value}.png")
mode_images["Found"] = cv2.imread(f"assets/fillers/{CurrentMode.Found.value}.png")
mode_images["Unknown"] = cv2.imread(f"assets/fillers/{CurrentMode.Unknown.value}.png")
mode_images["Marked"] = cv2.imread(f"assets/fillers/{CurrentMode.Marked.value}.png")
mode_images["AlreadyMarked"] = cv2.imread(f"assets/fillers/{CurrentMode.AlreadyMarked.value}.png")


# current_mode = 'Waiting'
# logger.disable("__main__")
# logger.add(sys.stdout, format="<yellow>{time}</yellow> <level>{message}</level>")


def face_confidence(face_distance, face_match_threshold=0.6):
    face_range = 1.0 - face_match_threshold
    linear_val = (1.0 - face_distance) / (face_range * 2.0)

    if face_distance > face_match_threshold:
        return str(round(linear_val * 100, 2)) + "%"
    else:
        value = (
            linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))
        ) * 100
        return str(round(value, 2)) + "%"


class FaceRecognition:
    db: FacesDatabase
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    process_current_frame = True
    attendance_marked = False
    current_mode = "Waiting"
    counter = 0
    students = []

    selected_name = ""
    selected_course = ""
    selected_picture = ""

    ############################################################
    # constructor
    ############################################################
    def __init__(self):
        self.db = FacesDatabase()
        self.load_students()
        # self.encode_faces()
        # sys.exit(12)

    ############################################################
    # load all students details from database
    ############################################################
    def load_students(self):
        """
        get all the students information
        """
        self.students = self.db.get_all_faces()

        for student in self.students:
            face_encoding = np.array(json.loads(student.encodings))
            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(student.name)

    ############################################################
    # convert numpy array into json string
    ############################################################
    def to_json(self, encodings: np.ndarray) -> str:
        """
        convert numpy array into json string.
        """
        return json.dumps(encodings.tolist())

    ############################################################
    # run face recognition
    ############################################################
    def run_recognition(self):
        """
        image recognition start from here
        """

        # obtain video capture device
        video_capture = cv2.VideoCapture(0)

        # check is the camera is opened or not
        if not video_capture.isOpened():
            sys.exit("Video source not opened...")

        while True:
            ret, frame = video_capture.read()

            # Displaying the camera dimensions
            width = video_capture.get(3)
            height = video_capture.get(4)
            fps = video_capture.get(5)
            logger.debug(f"Camera width x height x fps: {width} x {height} x {fps}")

            # if no frame captured, continue
            if not ret:
                continue

            # if the frame is marked for processing, then start recognition
            if self.process_current_frame:
                # create a small frame from the video capture inputer
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

                # find all the faces in the current frame
                self.face_locations = face_recognition.face_locations(rgb_small_frame)
                # find all encoding for the face available in the freame
                self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)

                # this
                self.face_names = []

                name = "Unknown"
                confidence = "Unknown"

                for face_encoding in self.face_encodings:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    logger.debug(f"Face distances: {face_distances}")
                    best_match_index = np.argmin(face_distances)

                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        confidence = face_confidence(face_distances[best_match_index])
                        found_student = self.students[best_match_index]
                        logger.debug(f'Face confidence: {confidence}')

                    self.face_names.append(f"{name}")

            # logger.debug(f'name x confidence level: {name} x {confidence}')
            self.process_current_frame = not self.process_current_frame

            logger.debug(f"Face locations: {self.face_locations}")
            logger.debug(f"Face names: {self.face_names}")

            # display annotations
            for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                self.prepare_bounds_box(frame, name, top, right, bottom, left)
                # enable this break, if you like to display only one detection
                break

            logger.debug(f"No of face locations found : {len(self.face_locations)}")

            # make the video to 640 x 480 and display it with bound box
            small_frame = cv2.resize(frame, (0, 0), fx=factor, fy=factor)
            bg_image[
                start_y: start_y + int(height * factor),
                start_x: start_x + int(width * factor),
            ] = small_frame

            # mode the application is waiting to find face in the video
            if len(self.face_locations) == 0:
                self.current_mode = CurrentMode.Waiting.value
                self.counter = 0
                self.attendance_marked = False
                bg_image[mp_y: mp_y + mp_h, mp_x: mp_x + mp_w] = mode_images[self.current_mode]

            # face found and no student information in the database
            if name == "Unknown" and len(self.face_locations) > 0:
                self.current_mode = CurrentMode.Unknown.value
                bg_image[mp_y: mp_y + mp_h, mp_x: mp_x + mp_w] = mode_images[self.current_mode]

            # face and student details found in the database
            if name != "Unknown" and len(self.face_locations) > 0:
                if self.counter == 0:
                    self.counter = 1
                else:
                    self.counter += 1

                if self.counter <= ACCEPT_COUNTER:
                    self.current_mode = CurrentMode.Found.value

                elif self.counter > ACCEPT_COUNTER and self.attendance_marked is False:
                    logger.debug("********* performing attendance insert *********")
                    timediff = self.db.get_time_diff(found_student.face_id)
                    logger.debug(f"Time diff: {timediff}")
                    if timediff == 0 or timediff > ATTENDANCE_TIME_DELTA:
                        uid = self.db.insert_attenance_details(found_student.face_id,
                                                               found_student.filename,
                                                               found_student.name,
                                                               found_student.course)
                        if len(uid) > 0:
                            logger.success("********* attendance insert SUCCESS *********")
                            self.attendance_marked = True
                        self.current_mode = CurrentMode.Marked.value
                    else:
                        logger.info("********* attendance ALREADY marked *********")
                        self.current_mode = CurrentMode.AlreadyMarked.value

                bg_image[mp_y: mp_y + mp_h, mp_x: mp_x + mp_w] = mode_images[self.current_mode]

                if self.counter <= ACCEPT_COUNTER and self.current_mode == CurrentMode.Found.value:
                    student_image = cv2.imread(f"assets/faces/{found_student.filename}")
                    logger.debug(f"Student image width:  {student_image.shape[0]}")
                    logger.debug(f"Student image height:, {student_image.shape[1]}")
                    student_small_frame = cv2.resize(student_image, (st_w, st_h))
                    bg_image[st_y: st_y + st_h, st_x: st_x + st_w] = student_small_frame
                    cv2.putText(bg_image, name, (1465, 725), cv2.FONT_HERSHEY_DUPLEX, 1, (121, 9, 238), 2)
                    cv2.putText(bg_image, found_student.course, (1465, 765),
                                cv2.FONT_HERSHEY_DUPLEX, 1, (255, 0, 0), 2)
                    cv2.putText(bg_image, found_student.course, (1465, 765),
                                cv2.FONT_HERSHEY_DUPLEX, 1, (255, 0, 0), 2)

            logger.debug(f"Counter: {self.counter}")

            logger.debug(f"Current mode: {self.current_mode}")
            if (self.current_mode == CurrentMode.AlreadyMarked.value or
                self.current_mode == CurrentMode.Found.value or
                    self.current_mode == CurrentMode.Marked.value) and self.counter > RESET_COUNTER:
                logger.debug("**************** RESTING THE COUNTER ************************")
                self.counter = 0
                self.current_mode = CurrentMode.Waiting.value
                self.attendance_marked = False
                # found_student = None
                # bg_image[mp_y: mp_y + mp_h, mp_x: mp_x + mp_w] = mode_images[self.current_mode]

            # show final background image
            cv2.imshow("Attendence System using Face Recognition", bg_image)
            # waiting for esc or q key
            key = cv2.waitKey(1000)
            if key == 27 or key == ord("q"):
                break

        # release all the resources and destroy windows
        video_capture.release()
        cv2.destroyAllWindows()

    ############################################################
    # Prepare bounds box
    ############################################################
    def prepare_bounds_box(self, frame, name, top, right, bottom, left):
        # red = (0, 0, 255)
        green = (0, 255, 0)
        # white = (255, 255, 255)
        black = (0, 0, 0)
        if name.startswith("Unknown"):
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), -1)
            cv2.putText(
                frame,
                name,
                (left + 6, bottom - 6),
                cv2.FONT_HERSHEY_DUPLEX,
                0.8,
                black,
                1,
            )
        else:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), green, -1)
            cv2.putText(
                frame,
                name,
                (left + 6, bottom - 10),
                cv2.FONT_HERSHEY_DUPLEX,
                0.8,
                black,
                2,
            )


############################################################
# main
############################################################
if __name__ == "__main__":
    fr = FaceRecognition()
    fr.run_recognition()
