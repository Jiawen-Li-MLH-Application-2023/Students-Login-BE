import pymysql
import os
import uuid


class StudentsResource:

    def __init__(self):
        pass

    @staticmethod
    def _get_connection():
        # user = "admin"
        # password = "1234567890"
        # h = "e6156.coxz1yzswsen.us-east-1.rds.amazonaws.com"
        usr=os.environ.get("DBUSER")
        pw = os.environ.get("DBPW")
        h = os.environ.get("DBHOST")
        conn = pymysql.connect(
            user = usr,
            password = pw,
            host = h,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn

    @staticmethod
    def insert_student(uni, email, password, last_name, first_name, middle_name):
        if not (uni and email and last_name and first_name):
            return False
        conn = StudentsResource._get_connection()
        cur = conn.cursor()

        if middle_name == "":
            sql = """
            INSERT INTO students_login_db.students(uni, last_name, first_name, email, password, status) 
            values (%s, %s, %s, %s, %s, %s);
            """
            cur.execute(sql, args=(uni, last_name, first_name, email, password, "Pending"))
        else:
            sql = """
            INSERT INTO students_login_db.students(uni, last_name, first_name, middle_name, email, password, status) 
            values (%s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(sql, args=(uni, last_name, first_name, middle_name, email, password, "Pending"))
        result = cur.rowcount
        return True if result == 1 else False

    def update_account(uni, email, password):
        if not uni:
            return False
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        sql = """UPDATE students_login_db.students SET uni=%s, password=%s WHERE email=%s"""
        cur.execute(sql, args=(uni, password, email))

        sql_check = "SELECT * FROM students_login_db.students WHERE uni=%s"
        check_res = cur.execute(sql_check, args=uni)
        if cur.fetchone():
            return True
        else:
            return False

    @staticmethod
    def get_by_uni_email(uni="", email=""):
        # check if uni and email are both empty
        if uni == "" and email == "":
            return None
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        if email == "" and uni != "N/A":
            sql = "SELECT * FROM students_login_db.students WHERE uni=%s"
            res = cur.execute(sql, args=uni)
        else:
            sql = "SELECT * FROM students_login_db.students WHERE email=%s"
            res = cur.execute(sql, args=email)
        result = cur.fetchone()

        return result

    @staticmethod
    def delete_by_email(email):
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        sql = "DELETE FROM students_login_db.students WHERE email=%s"
        res = cur.execute(sql, args=email)
        if cur.rowcount == 1:
            return True
        else:
            # Nothing deleted
            return False

    @staticmethod
    def student_is_pending(uni):
        # check if uni and email are correct and student is in pending status
        if not uni:
            return False
        sql = "SELECT status FROM students_login_db.students WHERE uni=%s"
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        res = cur.execute(sql, args=uni)
        result = cur.fetchone()
        return True if result['status'] != 'Verified' else False

    @staticmethod
    def update_student_status(uni, email):
        if not uni or not email:
            return False
        sql = "UPDATE students_login_db.students SET status = 'Verified' WHERE uni=%s and email=%s"
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        res = cur.execute(sql, args=(uni, email))
        result = cur.rowcount
        return True if result == 1 else False

    @staticmethod
    def update_profile(uni, timezone, major, gender, msg):
        if not uni:
            return False
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        sql = """INSERT INTO students_login_db.students_profile(uni, timezone, major, gender, personal_message)
                VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE timezone=%s, major=%s, gender=%s, personal_message=%s"""
        cur.execute(sql, args=(uni, timezone, major, gender, msg, timezone, major, gender, msg))

        sql_check = "SELECT * FROM students_login_db.students_profile WHERE uni=%s"
        check_res = cur.execute(sql_check, args=uni)
        if cur.fetchone():
            return True
        else:
            return False

    @staticmethod
    def get_profile(uni):
        sql = "SELECT * FROM students_login_db.students_profile WHERE uni=%s"
        conn = StudentsResource._get_connection()
        cur = conn.cursor()
        res = cur.execute(sql, args=uni)
        result = cur.fetchone()
        return result
