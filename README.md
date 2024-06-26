# Student Attendance System

### Create a virutal environment

```bash
python3  -m venv ml
```

### Activate the virtual environment

```bash
source ml/bin/activate
```

### Install the following libraries

```bash
pip install face_recognition
pip install opencv-python
pip install loguru
pip install opencv-python
pip install "fastapi[all]"
pip install "uvicorn[standard]"
pip install python-multipart
pip install sqlalchemy
pip install jinja2
pip install imutils
pip install pytz
```

### Main program

Use the following command to run the main program to recognize the students face and mark the attendance

```bash
python main.py
```

### Web Frontend

Use the following command to run the website.

```bash
uvicorn api:app --reload --reload-include="*.html" --reload-include="*.css" --reload-include="*.js"
```
### ⚠️ Limitation
The face_recognition API was trained on a predominately western population. This means that accuracy may vary across different ethnic groups.
