import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import logging

from . import models, schemas
from .database import SessionLocal, engine

# --- 1. SETUP STORAGE ---
UPLOAD_DIR = "uploaded_files"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    print(f"✅ Created physical storage folder: {UPLOAD_DIR} - main.py:18")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables automatically
models.Base.metadata.create_all(bind=engine)

# Ensure profile_pic columns exist (safe sqlite migration)
def ensure_profile_columns():
    try:
        with engine.connect() as conn:
            # Faculty table
            col_info = conn.execute(text("PRAGMA table_info('faculty')")).fetchall()
            cols = [c[1] for c in col_info]
            if 'profile_pic' not in cols:
                conn.execute(text("ALTER TABLE faculty ADD COLUMN profile_pic TEXT"))
                logger.info("Added 'profile_pic' column to faculty table.")

            # Students table
            col_info = conn.execute(text("PRAGMA table_info('students')")).fetchall()
            cols = [c[1] for c in col_info]
            if 'profile_pic' not in cols:
                conn.execute(text("ALTER TABLE students ADD COLUMN profile_pic TEXT"))
                logger.info("Added 'profile_pic' column to students table.")
    except Exception as e:
        logger.error(f"Failed to ensure profile_pic columns: {e}")

ensure_profile_columns()

# --- 2. INITIALIZE THE APP ---
app = FastAPI()

# --- 3. MOUNT STATIC FILES ---
# This allows students to access files via http://localhost:8000/static/filename.pdf
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Session Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PYDANTIC MODEL FOR MARKS SYNC ---
class MarkSyncRequest(BaseModel):
    student_roll_no: str
    course_code: str
    cia1_marks: float
    cia1_retest: float
    cia2_marks: float
    cia2_retest: float
    subject_attendance: float


# --- ADMIN MODELS FOR MANAGEMENT ---
class AdminUserCreateRequest(BaseModel):
    id: str
    name: str
    role: str  # 'Student' or 'Faculty'
    password: str
    year: Optional[int] = None
    semester: Optional[int] = None
    designation: Optional[str] = None
    doj: Optional[str] = None

class AdminEnrollmentRequest(BaseModel):
    student_roll_no: str
    course_code: str

# --- AUTHENTICATION ---
@app.post("/login", response_model=schemas.Token)
def login(login_data: schemas.LoginData, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == login_data.username).first()
    if not user or user.password != login_data.password:
         raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": user.id, "token_type": "bearer", "role": user.role, "user_id": user.id}

# --- ADMIN: USER & COURSE MANAGEMENT ---

@app.post("/admin/create-user")
def admin_create_user(data: AdminUserCreateRequest, db: Session = Depends(get_db)):
    try:
        if db.query(models.User).filter(models.User.id == data.id).first():
            raise HTTPException(status_code=400, detail="User ID already exists")

        # Create User credential
        new_user = models.User(id=data.id, role=data.role, password=data.password)
        db.add(new_user)
        db.flush()

        # Create profile depending on role
        if data.role == "Student":
            profile = models.Student(
                roll_no=data.id,
                name=data.name,
                year=int(data.year) if data.year is not None else 1,
                semester=int(data.semester) if data.semester is not None else 1,
                cgpa=0.0,
                attendance_percentage=0.0
            )
            db.add(profile)
        elif data.role == "Faculty":
            profile = models.Faculty(
                staff_no=data.id,
                name=data.name,
                designation=data.designation or "Assistant Professor",
                doj=data.doj or "01.01.2024"
            )
            db.add(profile)
        else:
            raise HTTPException(status_code=400, detail="Invalid role")

        db.commit()
        return {"message": f"{data.role} created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/courses")
def add_course(course: schemas.CourseCreate, db: Session = Depends(get_db)):
    try:
        if db.query(models.Course).filter(models.Course.code == course.code).first():
            raise HTTPException(status_code=400, detail="Course code already exists")
        db_course = models.Course(**course.dict())
        db.add(db_course)
        db.commit()
        return db_course
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Add course error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin/courses/{course_code}")
def delete_course(course_code: str, db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.code == course_code).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"message": "Course removed"}


@app.post("/admin/enroll")
def enroll_student(data: AdminEnrollmentRequest, db: Session = Depends(get_db)):
    try:
        student = db.query(models.Student).filter(models.Student.roll_no == data.student_roll_no).first()
        course = db.query(models.Course).filter(models.Course.code == data.course_code).first()
        if not student or not course:
            raise HTTPException(status_code=404, detail="Student or Course not found")

        existing = db.query(models.AcademicData).filter(
            models.AcademicData.student_roll_no == data.student_roll_no,
            models.AcademicData.course_code == data.course_code
        ).first()
        if existing:
            return {"message": "Student already enrolled in this course"}

        enrollment = models.AcademicData(
            student_roll_no=data.student_roll_no,
            course_code=data.course_code,
            status="Pursuing",
            cia1_marks=0.0,
            cia1_retest=0.0,
            cia2_marks=0.0,
            cia2_retest=0.0,
            subject_attendance=0.0
        )
        db.add(enrollment)
        db.commit()
        return {"message": "Student enrolled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Enrollment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- FACULTY: MARKS & ATTENDANCE MANAGEMENT ---

@app.get("/marks/section")
def get_section_marks(course_code: str, db: Session = Depends(get_db)):
    try:
        results = db.query(
            models.Student.name,
            models.AcademicData.student_roll_no.label("roll_no"),
            models.AcademicData.cia1_marks,
            models.AcademicData.cia1_retest,
            models.AcademicData.cia2_marks,
            models.AcademicData.cia2_retest,
            models.AcademicData.subject_attendance
        ).join(
            models.AcademicData, models.Student.roll_no == models.AcademicData.student_roll_no
        ).filter(models.AcademicData.course_code == course_code).all()
        
        formatted_results = []
        for row in results:
            formatted_results.append({
                "name": row.name,
                "roll_no": row.roll_no,
                "cia1_marks": row.cia1_marks or 0.0,
                "cia1_retest": row.cia1_retest or 0.0,
                "cia2_marks": row.cia2_marks or 0.0,
                "cia2_retest": row.cia2_retest or 0.0,
                "subject_attendance": row.subject_attendance or 0.0
            })
        return formatted_results
    except Exception as e:
        logger.error(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Database processing error")
@app.post("/marks/sync")
def sync_marks(data: MarkSyncRequest, db: Session = Depends(get_db)):
    try:
        record = db.query(models.AcademicData).filter(
            models.AcademicData.student_roll_no == data.student_roll_no,
            models.AcademicData.course_code == data.course_code
        ).first()

        if not record:
            raise HTTPException(status_code=404, detail="Enrollment record not found")

        record.cia1_marks = data.cia1_marks
        record.cia1_retest = data.cia1_retest
        record.cia2_marks = data.cia2_marks
        record.cia2_retest = data.cia2_retest
        record.subject_attendance = data.subject_attendance

        db.commit()
        return {"message": "Sync successful"}
    except Exception as e:
        db.rollback()
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- STUDENT: ACADEMIC PORTAL ---
@app.get("/marks/cia")
def get_student_marks(student_id: str, db: Session = Depends(get_db)):
    marks = db.query(models.AcademicData).filter(models.AcademicData.student_roll_no == student_id).all()
    return [
        {
            "subject": m.course_code,
            "cia1": m.cia1_marks or 0,
            "cia1_retest": m.cia1_retest or 0,
            "cia2": m.cia2_marks or 0,
            "cia2_retest": m.cia2_retest or 0,
            "subject_attendance": m.subject_attendance or 0,
            "total": (m.cia1_marks or 0) + (m.cia2_marks or 0)
        } for m in marks
    ]

# --- MATERIALS MANAGEMENT (UPLOAD & DELETE) ---

@app.post("/materials")
async def upload_material(
    course_code: str = Form(...),
    type: str = Form(...),
    title: str = Form(...),
    posted_by: str = Form(...),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Support either a direct file upload OR an external URL (e.g., YouTube link)
        if url:
            file_url = url
        elif file:
            file_location = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_url = f"http://localhost:8000/static/{file.filename}"
        else:
            raise HTTPException(status_code=400, detail="Either file or url must be provided")

        db_material = models.Material(
            course_code=course_code,
            type=type,
            title=title,
            file_link=file_url,
            posted_by=posted_by
        )
        db.add(db_material)
        db.commit()
        db.refresh(db_material)
        return db_material
    except HTTPException:
        # Re-raise intended HTTP errors
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

@app.delete("/materials/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db)):
    # 1. Find the material entry
    db_material = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # 2. Delete physical file only if it's a locally stored static file
        if '/static/' in (db_material.file_link or ''):
            filename = db_material.file_link.split("/")[-1]
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted physical file: {file_path} - main.py:190")

        # 3. Remove from database
        db.delete(db_material)
        db.commit()
        return {"message": "File and database record deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/materials/{course_code}")
def get_course_materials(course_code: str, db: Session = Depends(get_db)):
    return db.query(models.Material).filter(models.Material.course_code == course_code).all()

# --- ANNOUNCEMENTS ---

@app.post("/announcements")
def create_announcement(announcement: schemas.AnnouncementCreate, db: Session = Depends(get_db)):
    try:
        # Verify the poster exists and permissions for Faculty-targeted announcements
        poster = db.query(models.User).filter(models.User.id == announcement.posted_by).first()
        if not poster:
            raise HTTPException(status_code=404, detail="Posting user not found")

        # Only Admins can post announcements targeted to Faculty
        if (announcement.type or "").lower() == "faculty" and poster.role != "Admin":
            logger.warning(f"Unauthorized attempt by {poster.id} to post Faculty announcement")
            raise HTTPException(status_code=403, detail="Only Admins can post announcements targeted to Faculty")

        db_announcement = models.Announcement(
            title=announcement.title,
            content=announcement.content,
            type=announcement.type,
            posted_by=announcement.posted_by,
            course_code=announcement.course_code
        )
        db.add(db_announcement)
        db.commit()
        db.refresh(db_announcement)
        return db_announcement
    except HTTPException:
        # Re-raise HTTP errors we intentionally raised
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create announcement error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/announcements")
def get_announcements(type: Optional[str] = None, course_code: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Announcement)
    if type:
        query = query.filter(models.Announcement.type == type)
    if course_code:
        query = query.filter(
            (models.Announcement.course_code == course_code) | 
            (models.Announcement.course_code == "Global")
        )
    return query.order_by(models.Announcement.id.desc()).all()

# --- PROFILES & COURSES ---

@app.get("/faculty/{staff_no}", response_model=schemas.Faculty)
def get_faculty(staff_no: str, db: Session = Depends(get_db)):
    faculty = db.query(models.Faculty).filter(models.Faculty.staff_no == staff_no).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty


@app.post("/faculty/{staff_no}/photo")
async def upload_faculty_photo(staff_no: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    faculty = db.query(models.Faculty).filter(models.Faculty.staff_no == staff_no).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    try:
        import time
        filename_root, file_ext = os.path.splitext(file.filename)
        safe_staff = staff_no.replace(' ', '_')
        filename = f"faculty_{safe_staff}_{int(time.time())}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Remove old file if present
        if faculty.profile_pic:
            try:
                old_name = os.path.basename(faculty.profile_pic)
                old_path = os.path.join(UPLOAD_DIR, old_name)
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = f"http://localhost:8000/static/{filename}"
        faculty.profile_pic = file_url
        db.commit()
        db.refresh(faculty)
        return {"profile_pic": file_url}
    except Exception as e:
        db.rollback()
        logger.error(f"Faculty photo upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload photo")

@app.get("/student/{roll_no}", response_model=schemas.Student)
def get_student(roll_no: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.roll_no == roll_no).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.post("/student/{roll_no}/photo")
async def upload_student_photo(roll_no: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.roll_no == roll_no).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    try:
        import time
        filename_root, file_ext = os.path.splitext(file.filename)
        safe_roll = roll_no.replace(' ', '_')
        filename = f"student_{safe_roll}_{int(time.time())}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Remove old file if present
        if student.profile_pic:
            try:
                old_name = os.path.basename(student.profile_pic)
                old_path = os.path.join(UPLOAD_DIR, old_name)
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = f"http://localhost:8000/static/{filename}"
        student.profile_pic = file_url
        db.commit()
        db.refresh(student)
        return {"profile_pic": file_url}
    except Exception as e:
        db.rollback()
        logger.error(f"Student photo upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload photo")

@app.get("/courses", response_model=List[schemas.Course])
def get_courses(semester: Optional[int] = None, db: Session = Depends(get_db)):
    if semester:
        return db.query(models.Course).filter(models.Course.semester == semester).all()
    return db.query(models.Course).all()


# --- TOPPERS (RANKINGS) ---
@app.get("/toppers/department", response_model=List[schemas.Student])
def get_department_toppers(limit: int = 3, db: Session = Depends(get_db)):
    """Return top `limit` students department-wide by CGPA."""
    try:
        students = db.query(models.Student).order_by(models.Student.cgpa.desc()).limit(limit).all()
        return students
    except Exception as e:
        logger.error(f"Error fetching department toppers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch department toppers")


@app.get("/toppers/class", response_model=List[schemas.Student])
def get_class_toppers(year: Optional[int] = None, semester: Optional[int] = None, limit: int = 3, db: Session = Depends(get_db)):
    """Return top `limit` students for a given class (year and/or semester) by CGPA."""
    try:
        query = db.query(models.Student)
        if year is not None:
            query = query.filter(models.Student.year == year)
        if semester is not None:
            query = query.filter(models.Student.semester == semester)
        students = query.order_by(models.Student.cgpa.desc()).limit(limit).all()
        return students
    except Exception as e:
        logger.error(f"Error fetching class toppers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch class toppers")