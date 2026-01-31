from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True) # Staff_No or Roll_No or 'admin'
    role = Column(String) # Student, Faculty, HOD, Admin
    password = Column(String) 

    faculty = relationship("Faculty", back_populates="user", uselist=False)
    student = relationship("Student", back_populates="user", uselist=False)

class Faculty(Base):
    __tablename__ = "faculty"
    staff_no = Column(String, ForeignKey("users.id"), primary_key=True)
    name = Column(String)
    designation = Column(String)
    doj = Column(String)
    profile_pic = Column(String, nullable=True)

    user = relationship("User", back_populates="faculty")

class Student(Base):
    __tablename__ = "students"
    roll_no = Column(String, ForeignKey("users.id"), primary_key=True)
    name = Column(String)
    year = Column(Integer)
    semester = Column(Integer)
    cgpa = Column(Float)
    attendance_percentage = Column(Float) # Overall Attendance
    profile_pic = Column(String, nullable=True)

    user = relationship("User", back_populates="student")
    academic_data = relationship("AcademicData", back_populates="student")

class Course(Base):
    __tablename__ = "courses"
    code = Column(String, primary_key=True, index=True)
    title = Column(String)
    semester = Column(Integer)
    credits = Column(Integer)
    category = Column(String, nullable=True) 

    academic_data = relationship("AcademicData", back_populates="course")
    materials = relationship("Material", back_populates="course")

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    type = Column(String) # "Global" or "Subject"
    course_code = Column(String, ForeignKey("courses.code"), nullable=True)
    posted_by = Column(String) 

class AcademicData(Base):
    """
    Updated to handle CIA marks out of 60, Retests, and Subject Attendance.
    """
    __tablename__ = "academic_data"

    id = Column(Integer, primary_key=True, index=True)
    student_roll_no = Column(String, ForeignKey("students.roll_no"))
    course_code = Column(String, ForeignKey("courses.code"))
    
    # CIA 1 & Retest (Scale: 60)
    cia1_marks = Column(Float, default=0.0)
    cia1_retest = Column(Float, default=0.0) 

    # CIA 2 & Retest (Scale: 60)
    cia2_marks = Column(Float, default=0.0)
    cia2_retest = Column(Float, default=0.0)

    # Subject-Specific Attendance (Syncs from Faculty Section A page)
    subject_attendance = Column(Float, default=0.0)

    innovative_assignment_marks = Column(Float, default=0.0) # Assignment field
    status = Column(String, default="Pursuing") 

    student = relationship("Student", back_populates="academic_data")
    course = relationship("Course", back_populates="academic_data")

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String, ForeignKey("courses.code"))
    type = Column(String) # "Lecture Notes", "Question Bank", "Assignment"
    title = Column(String)
    file_link = Column(String)
    posted_by = Column(String) 

    course = relationship("Course", back_populates="materials")