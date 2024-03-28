from contextlib import asynccontextmanager
import os
import pathlib
import uuid
# from datetime import datetime
from pathlib import Path
# from typing import Annotated, Optional, Union
# from uuid import UUID
# import numpy as np
import json
import face_recognition

from fastapi import FastAPI, File, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import FacesDatabase
# from database import Student
import starlette.status as status
from loguru import logger

faces_db = FacesDatabase()


###############################################################################
# life span hooks
###############################################################################
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    logger.debug("Application shutdown with database close.")
    faces_db.close_db()


# fast api instannce
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")

PICTURS_FOLDER = "./assets/faces"


###############################################################################
# Home page
###############################################################################
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )


###############################################################################
# Student listing
###############################################################################
@app.get("/students/list", response_class=HTMLResponse)
async def students_list(request: Request, msg: bool = False):
    msg_string = ""
    if msg:
        msg_string = "New user created sucessfully! \U0001F44F"

    # get all the faces from database
    students = faces_db.get_all_faces()
    return templates.TemplateResponse(
        request=request,
        name="student_list.html",
        context={
            "students": students,
            "msg": msg_string}
    )


###############################################################################
# attendance listing
###############################################################################
@app.get("/attendance/list", response_class=HTMLResponse)
async def attendance_list(request: Request):

    # get all the faces from database
    attendance_list = faces_db.get_attendance(student_face_id="")
    return templates.TemplateResponse(
        request=request,
        name="attendance_list.html",
        context={
            "attendance_list": attendance_list
        }
    )


###############################################################################
# New student registration
###############################################################################
@app.get("/students/new", response_class=HTMLResponse)
async def new_student_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="student_new.html",
        context={
            "name_value": "",
            "course_value": "",
            "error_message": "",
        }
    )


###############################################################################
# Register action for new student
###############################################################################
@app.post("/students/register", response_class=HTMLResponse)
async def register_student(request: Request,
                           name: str = Form(None),
                           course: str = Form(None),
                           profile_picture: UploadFile = File(...)):
    # student_id: str = Form(None),
    logger.debug(
        f"user registration invoked ({name},  {course}, [{profile_picture}])")

    # check student details available or not
    if name == None or course == None:
        logger.error("data is not available for name and course")
        if name == None:
            name = ""
        if course == None:
            course = ""

        return templates.TemplateResponse(
            request=request,
            name="student_new.html",
            context={
                "name_value": name,
                "course_value": course,
                "error_message": "Please provide all the required information",
            }
        )

    # check user profile picture
    if profile_picture == None or len(profile_picture.filename) == 0:
        logger.error("error: profile picutre not available.")
        return templates.TemplateResponse(
            request=request,
            name="student_new.html",
            context={
                "name_value": name,
                "course_value": course,
                "error_message": "Please select the student profile picture.",
            }
        )
    # logger.debug(len(profile_picture.filename), profile_picture.filename)
    logger.debug(f"profile picture filename: {profile_picture.filename}")
    # Save the uploaded profile picture
    face_id = save_profile_pic(profile_picture)
    image = face_id + pathlib.Path(str(profile_picture.filename)).suffix
    face_image = face_recognition.load_image_file(f"assets/faces/{image}")
    logger.debug("Image filename: ", image)
    face_encodings = face_recognition.face_encodings(face_image)[0]
    # print("face encodings:\n", face_encodings)
    new_face_id = faces_db.insert_face_details(name,
                                               course,
                                               face_id,
                                               image,
                                               json.dumps(face_encodings.tolist()))
    # print(new_face_id)

    # message to user on successfully created user
    msg_string = f"New user ({name}) created sucessfully! \U0001F44F"
    # return the listing screen
    students = faces_db.get_all_faces()
    return templates.TemplateResponse(
        request=request,
        name="student_list.html",
        context={"students": students,
                 "msg": msg_string}
    )


###############################################################################
# Save profile picture to faces folder
###############################################################################
def save_profile_pic(upload_file: UploadFile) -> str:
    # file_extension = pathlib.Path(upload_file.filename).suffix
    if not upload_file:
        return ""
    file_ext = pathlib.Path(str(upload_file.filename)).suffix
    face_id_uuid = str(uuid.uuid4()) + file_ext
    logger.debug(f"UUID {face_id_uuid}")

    file_path = Path(PICTURS_FOLDER) / face_id_uuid
    with file_path.open("wb") as buffer:
        buffer.write(upload_file.file.read())

    # finally return the uuid
    return face_id_uuid.split(".")[0]


###############################################################################
# delete student details
###############################################################################
@app.get("/students/delete/{face_id}", response_class=RedirectResponse)
async def delete_student(request: Request, face_id: str):
    student = faces_db.get_student_details(face_id)

    if student != None:
        deleted = faces_db.delete_face_details(student.face_id)
        if not deleted:
            logger.error("unable to delete the student details")
        else:
            os.remove(f"{PICTURS_FOLDER}/{student.filename}")
    redirect_url = request.url_for('students_list')
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)


###############################################################################
# delete student details
###############################################################################
@app.get("/attendance/delete/{id}", response_class=RedirectResponse)
async def delete_student(request: Request, id: int):
    deleted = faces_db.delete_attendance_details(id)
    if not deleted:
        logger.error("unable to delete the student details")
    redirect_url = request.url_for('attendance_list')
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)


################################################################################
# Demo routes
################################################################################


@app.post("/files/")
async def create_file(filea: UploadFile = File(...),
                      token: str = Form(None)):
    return {
        "file_size": filea.size,
        "filename": filea.filename,
        "content type": filea.content_type,

        "token": token,
    }
