import sqlite3
import sys
from typing import List
from datetime import datetime
from loguru import logger
import pytz

SELECT_QUERY = "SELECT * FROM faces WHERE face_id = ?;"


class Student:
    def __init__(self, id, name, course, face_id, filename, encodings, join_date):
        self.id = id
        self.name = name
        self.course = course
        self.face_id = face_id
        self.filename = filename
        self.encodings = encodings
        self.join_date = join_date


class Attendance:
    def __init__(self, id: int, face_id: str, filename: str, name: str, course: str, attendance_time: str):
        self.id = id
        self.name = name
        self.course = course
        self.face_id = face_id
        self.filename = filename
        self.attendance_time = attendance_time


class FacesDatabase:
    """
    A class to represent a faces database.
    """
    conn: sqlite3.Connection
    db_open: bool = False

    ############################################################################
    # constructor
    ############################################################################
    # class constructor
    def __init__(self):
        """
        Constructs the faces database object.
        """
        self.open_db()
        self.create_tables()

    ############################################################################
    # print error message
    ############################################################################
    def print_error_format(self, code, error="", message=""):
        """
        Prints the SQLite error details.

        Parameters
        ----------
        code : str
            SQLite Error code
        error : str, optional
            SQLite Error name
        message: str, optional
            SQLite Error message

        Returns
        -------
        None
        """
        logger.error("--------------------- ERROR ---------------------")
        logger.error(f"Error message: {message}")
        logger.error(f"Error code   : {code}")
        logger.error(f"Error name   : {error}")
        logger.error("-------------------------------------------------")

    ############################################################################
    # print error message
    ############################################################################
    def print_error(self, e: sqlite3.OperationalError):
        self.print_error_format(
            e.sqlite_errorcode, e.sqlite_errorname, e.args[0])

    ############################################################################
    # open database file
    ############################################################################
    def open_db(self):
        """
        Open database with given database file.
        """
        try:
            self.conn = sqlite3.connect("db/faces.db")
            self.db_open = True
            logger.success("Opened database successfully.")
        except sqlite3.OperationalError as e:
            self.print_error(e)
            logger.error("exiting...")
            sys.exit()

    ############################################################################
    # close database
    ############################################################################
    def close_db(self):
        """
        Close the database.
        """
        logger.info("closing database connnection...")
        self.conn.close()
        self.db_open = False

    ############################################################################
    # check the table exists or not
    ############################################################################
    def create_tables(self):
        faces_table_ddl = """
        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY,
            name TEXT not null,
            course TEXT not null,
            face_id TEXT not null unique,
            filename TEXT not null,
            encodings TEXT not null,
            datetime INTEGER not null
        );
        """
        attendance_table_ddl = """
        CREATE TABLE IF NOT EXISTS attendance_list (
            id INTEGER PRIMARY KEY,
            face_id text not null,
            filename text not null,
            name TEXT not null,
            course TEXT not null,
            datetime INTEGER not null
        );
        """
        self.create_table_if_not_exists(faces_table_ddl)
        self.create_table_if_not_exists(attendance_table_ddl)

    ############################################################################
    # create table for given DDL
    ############################################################################
    def create_table_if_not_exists(self, create_table_query: str):
        """
        Create faces table, if not exists.
        """
        cursor = self.conn.cursor()
        # create  table
        try:
            cursor.execute(create_table_query)
            self.conn.commit()
            logger.success("FACES table created or already exists.")
        except sqlite3.OperationalError as e:
            self.print_error(e)
            self.close_db()
            logger.error("exiting...")
            sys.exit()

    ############################################################################
    # get all faces
    ############################################################################
    def get_all_faces(self) -> List[Student]:
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM faces")

        students = []
        # Fetch all rows
        for row in cursor.fetchall():
            student = Student(row[0],  # id
                              row[1],  # name
                              row[2],  # course
                              row[3],  # face id
                              row[4],  # image file name
                              row[5],  # encodings
                              datetime.fromtimestamp(row[6])  # join date
                              )
            students.append(student)

        # close the cursor
        cursor.close()
        return students

    ############################################################################
    # insert face/student details
    ############################################################################
    def insert_face_details(self, s: Student) -> str:
        """
        insert face details using student object
        """
        return self.insert_face_details(s.name,
                                        s.course,
                                        s.face_id,
                                        s.filename,
                                        s.encodings)

    ############################################################################
    # insert face/student details
    ############################################################################
    def insert_face_details(self, name: str, course: str, face_id: str, filename: str, encodings: str) -> str:
        """
        Insert face details into face table.

        Return:
        -------
        uuid : str
            String value of UUID
        """
        logger.debug("inserting data into face table...")
        cursor = self.conn.cursor()
        timestamp = datetime.now().timestamp()

        data = (name, course, face_id, filename, encodings, round(timestamp))
        logger.debug(f"Insert Data: {data}")
        insert_query = """
        INSERT INTO faces (name, course, face_id, filename, encodings, datetime) 
        values (?, ?, ?, ?, ?, ?);
        """
        try:
            cursor.execute(insert_query, data)
            cursor.close()
            self.conn.commit()
            return str(face_id)
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            self.print_error(e)
            return ""

    ############################################################################
    # insert attenance details
    ############################################################################
    def insert_attenance_details(self, face_id: str, filename: str, name: str, course: str) -> str:
        logger.debug("inserting data into face table...")
        cursor = self.conn.cursor()
        timestamp = datetime.now().timestamp()

        data = (face_id, filename, name, course, round(timestamp))
        logger.debug(f"Insert attendance data: {data}")
        insert_query = 'INSERT INTO attendance_list (face_id, filename, name, course, datetime) values (?, ?, ?, ?, ?)'

        try:
            cursor.execute(insert_query, data)
            cursor.close()
            self.conn.commit()
            return str(face_id)
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            self.print_error(e)
            return ""

    ############################################################################
    # search student by ID
    ############################################################################
    def search_by_id(self, face_id: str) -> bool:
        # Create a cursor object to interact with the database
        cursor = self.conn.cursor()

        # Execute the SQL query with the parameter
        try:
            cursor.execute(SELECT_QUERY, (face_id,))

            # Fetch the result (one row in this case)
            result = cursor.fetchone()
            cursor.close()
            if result:
                (id, name, course, fid, filename, encodings, time) = result
                # logger.debug("Result:", result)
                if fid == face_id:
                    return True
                else:
                    logger.warning("IDs are not matching.")
                    return False
            else:
                logger.warning("No matching record found.")
                return False
        except sqlite3.OperationalError as e:
            self.print_error(e)

    ############################################################################
    # get the time difference in seconds from last login
    ############################################################################
    def get_time_diff(self, face_id: str) -> int:
        # Create a cursor object to interact with the database
        cursor = self.conn.cursor()

        # Execute the SQL query with the parameter
        try:
            cursor.execute(
                """
                SELECT 
                    (unixepoch()-datetime) as timediff
                FROM attendance_list 
                    WHERE face_id = ? 
                ORDER BY 1 ASC LIMIT 1;""",
                (face_id,))
            # Fetch the result (one row in this case)
            result = cursor.fetchone()
            cursor.close()
            if result:
                (timediff,) = result
                return timediff
            else:
                return 0
        except sqlite3.OperationalError as e:
            self.print_error(e)

    ############################################################################
    # find name using face id
    ############################################################################

    def find_name_by_face_id(self, face_id: str) -> str:
        # create a cursor object to interact with the database
        cursor = self.conn.cursor()
        # execute the SQL query with the parameter
        try:
            cursor.execute(SELECT_QUERY, (face_id,))

            # fetch the result (one row in this case)
            result = cursor.fetchone()
            if result:
                (id, name, course, fid, filename, encodings, time) = result
                # logger.debug("Result:", result)
                return name
            else:
                logger.warning(
                    f"No matching record found for name by face id - {face_id}")
                return ""
        except sqlite3.OperationalError as e:
            self.print_error(e)

    ############################################################################
    # get all attendance from database and with where clause of face id
    ############################################################################
    def get_attendance(self, student_face_id: str) -> List[Attendance]:
        tz = pytz.timezone('Asia/Kuala_Lumpur')
        # create a cursor object to interact with the database
        cursor = self.conn.cursor()
        # define the SQL query to retrieve rows based on a parameter
        select_query = '''SELECT id, face_id, filename, name, course, datetime 
                          FROM attendance_list order by datetime desc'''
        if len(student_face_id) > 0:
            logger.debug("adding where clause...")
            select_query = select_query + ' where face_id = \'' + student_face_id + '\''
            logger.debug("SQL Query: " + select_query)
        attendance_list = []
        # execute the SQL query with the parameter
        try:
            cursor.execute(select_query,)
            for row in cursor.fetchall():
                (id, fid, filename, name, course, time) = row
                attd = Attendance(id, fid, filename, name, course,
                                  datetime.fromtimestamp(time, tz).strftime('%Y-%m-%d %H:%M:%S'))
                attendance_list.append(attd)
                # logger.debug("Result:", result)
        except sqlite3.OperationalError as e:
            self.print_error(e)
        return attendance_list

    ############################################################################
    # get all names from database
    ############################################################################
    def get_actual_names(self, face_ids: list) -> list:
        # create a cursor object to interact with the database
        cursor = self.conn.cursor()

        # define the SQL query to retrieve rows based on a parameter
        select_query = '''
        SELECT * FROM faces
        '''

        name_dict = {}
        # execute the SQL query with the parameter
        try:
            cursor.execute(select_query,)
            for row in cursor.fetchall():
                (id, name, course, fid, filename, encodings, time) = row
                name_dict[fid] = name
                # logger.debug("Result:", result)
        except sqlite3.OperationalError as e:
            self.print_error(e)

        names = []
        for index, id in enumerate(face_ids):
            names.append(name_dict[id])

        logger.debug(f'{name_dict}')
        return names

    ############################################################################
    # get encoding for given face/student id
    ############################################################################
    def get_encodings(self, face_id: str) -> str:
        # create a cursor object to interact with the database
        cursor = self.conn.cursor()
        # execute the SQL query with the parameter
        try:
            cursor.execute(SELECT_QUERY, (face_id,))

            # fetch the result (one row in this case)
            result = cursor.fetchone()
            if result:
                (id, name, course, fid, filename, encodings, time) = result
                # logger.debug("Result:", result)
                return encodings
            else:
                logger.error("Error: No encoding found.")
                return ""
        except sqlite3.OperationalError as e:
            self.print_error(e)

    ############################################################################
    # get student details based on id
    ############################################################################
    def get_student_details(self, face_id: str) -> Student:
        # create a cursor object to interact with the database
        cursor = self.conn.cursor()
        # execute the SQL query with the parameter
        try:
            cursor.execute(SELECT_QUERY, (face_id,))

            # fetch the result (one row in this case)
            result = cursor.fetchone()
            cursor.close()
            if result:
                (id, name, course, fid, filename, encodings, time) = result
                student = Student(id,
                                  name,
                                  course,
                                  fid,
                                  filename,
                                  encodings,
                                  time)
                # logger.debug("Result:", result)
                return student
            else:
                logger.error("Error: No student details found.")
                return None
        except sqlite3.OperationalError as e:
            self.print_error(e)

    ############################################################################
    # delete row by face id
    ############################################################################
    def delete_face_details(self, face_id: str) -> bool:
        # Create a cursor object to interact with the database
        cursor = self.conn.cursor()

        # Define the SQL query to delete rows based on a parameter
        delete_query = '''
        DELETE FROM faces 
        WHERE face_id = ?;
        '''

        try:
            # Execute the SQL query with the parameter
            cursor.execute(delete_query, (face_id,))

            # Commit the changes
            self.conn.commit()

            # Display the number of rows affected
            logger.debug(f"Rows affected: {cursor.rowcount}")

            if cursor.rowcount == 1:
                return True
            elif cursor.rowcount != 1:
                logger.error(
                    f"some error occured. actual no. of records deleted are {cursor.rowcount}")
                return False
            else:
                logger.warning("No rows deleted.")
                return False
        except sqlite3.OperationalError as e:
            self.print_error(e)

    ############################################################################
    # delete row by id in attendance list
    ############################################################################

    def delete_attendance_details(self, id: int) -> bool:
        # Create a cursor object to interact with the database
        cursor = self.conn.cursor()
        # Define the SQL query to delete rows based on a parameter
        delete_query = 'DELETE FROM attendance_list WHERE id = ?;'
        try:
            # Execute the SQL query with the parameter
            cursor.execute(delete_query, (id,))
            # Commit the changes
            self.conn.commit()
            # Display the number of rows affected
            logger.debug(f"Rows affected: {cursor.rowcount}")
            if cursor.rowcount == 1:
                return True
            elif cursor.rowcount != 1:
                logger.error(
                    f"some error occured. actual no. of records deleted are {cursor.rowcount}")
                return False
            else:
                logger.warning("No rows deleted.")
                return False
        except sqlite3.OperationalError as e:
            self.print_error(e)


if __name__ == "__main__":
    """
    Main program
    """
    db = FacesDatabase()
    db.insert_face_details(
        "swetha", "computer science", "88d3c534-e984-47af-a8ab-bec78fb12b8f", "image filename" "encodings")
    db.close_db()
