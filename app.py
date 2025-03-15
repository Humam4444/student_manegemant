from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///examination.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQL_SCHEMA_FILE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_schema.sql')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'instructor' or 'student'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    stage = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    grades = db.relationship('Grade', backref='student', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stage = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    semester = db.Column(db.Integer, nullable=False)  # 1 or 2
    units = db.Column(db.Integer, nullable=False)  # between 2-8
    grades = db.relationship('Grade', backref='course', lazy=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    coursework = db.Column(db.Integer, nullable=False, default=0)  # 0-50
    final_exam = db.Column(db.Integer, nullable=False, default=0)  # 0-50
    decision_marks = db.Column(db.Integer, nullable=False, default=0)  # 0-10
    academic_year = db.Column(db.String(20), nullable=False)
    
    @property
    def total(self):
        return self.coursework + self.final_exam + self.decision_marks
    
    @property
    def grade_status(self):
        if self.total < 50:
            return "راسب"
        return "ناجح"
    
    @property
    def grade_evaluation(self):
        total = self.total
        if total < 50:
            return "ضعيف"
        elif total < 60:
            return "مقبول"
        elif total < 70:
            return "متوسط"
        elif total < 80:
            return "جيد"
        elif total < 90:
            return "جيد جدا"
        else:
            return "امتياز"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.user_type == user_type:
            login_user(user)
            if user.user_type == 'instructor':
                return redirect(url_for('instructor_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('خطأ في اسم المستخدم أو كلمة المرور أو نوع المستخدم', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/instructor/dashboard')
@login_required
def instructor_dashboard():
    if current_user.user_type != 'instructor':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    stages = [1, 2, 3, 4]
    return render_template('instructor_dashboard.html', stages=stages)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.user_type != 'student':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('لم يتم العثور على بيانات الطالب', 'danger')
        return redirect(url_for('login'))
    
    stages = [1, 2, 3, 4]
    semesters = [1, 2]
    
    all_grades = {}
    for stage in stages:
        all_grades[stage] = {}
        for semester in semesters:
            courses = Course.query.filter_by(stage=stage, semester=semester).all()
            grades = []
            for course in courses:
                grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
                if grade:
                    grades.append({
                        'course': course,
                        'grade': grade
                    })
            all_grades[stage][semester] = grades
    
    return render_template('student_dashboard.html', all_grades=all_grades, stages=stages, semesters=semesters)

@app.route('/get_students_by_stage_semester', methods=['POST'])
@login_required
def get_students_by_stage_semester():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # تعديل: جلب جميع الطلاب بدلاً من تصفية حسب المرحلة
    students = Student.query.order_by(Student.student_id).all()
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'grades': []
        }
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if not grade:
                # Create empty grade if not exists
                grade = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    coursework=0,
                    final_exam=0,
                    decision_marks=0,
                    academic_year=f"{datetime.now().year-1}/{datetime.now().year}"
                )
                db.session.add(grade)
                db.session.commit()
            
            student_data['grades'].append({
                'grade_id': grade.id,
                'course_id': course.id,
                'course_name': course.name,
                'coursework': grade.coursework,
                'final_exam': grade.final_exam,
                'decision_marks': grade.decision_marks,
                'units': course.units,
                'total': grade.total,
                'evaluation': grade.grade_evaluation
            })
        
        result.append(student_data)
    
    return jsonify(result)

@app.route('/search_student', methods=['POST'])
@login_required
def search_student():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    search_term = request.form.get('search_term')
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    
    if not search_term or not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # استعلام للطلاب الذين يبدأ اسمهم بكلمة البحث (أولوية أولى)
    students_starting_with = db.session.query(Student, User).join(User, Student.user_id == User.id).filter(
        (User.name.like(f'{search_term}%') | Student.student_id.like(f'{search_term}%'))
    ).order_by(Student.student_id).all()
    
    # استعلام للطلاب الذين يحتوي اسمهم على كلمة البحث في أي مكان آخر (أولوية ثانية)
    students_containing = db.session.query(Student, User).join(User, Student.user_id == User.id).filter(
        (User.name.like(f'%{search_term}%') & ~User.name.like(f'{search_term}%')) | 
        (Student.student_id.like(f'%{search_term}%') & ~Student.student_id.like(f'{search_term}%'))
    ).order_by(Student.student_id).all()
    
    # دمج النتائج مع الحفاظ على الأولوية
    all_students = students_starting_with + students_containing
    
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student, user in all_students:
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'grades': []
        }
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                student_data['grades'].append({
                    'grade_id': grade.id,
                    'course_id': course.id,
                    'course_name': course.name,
                    'coursework': grade.coursework,
                    'final_exam': grade.final_exam,
                    'decision_marks': grade.decision_marks,
                    'units': course.units,
                    'total': grade.total,
                    'evaluation': grade.grade_evaluation
                })
        
        result.append(student_data)
    
    return jsonify(result)

@app.route('/update_grade', methods=['POST'])
@login_required
def update_grade():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    grade_id = request.form.get('grade_id')
    coursework = request.form.get('coursework')
    final_exam = request.form.get('final_exam')
    decision_marks = request.form.get('decision_marks')
    
    if not grade_id or not coursework or not final_exam or not decision_marks:
        return jsonify({'error': 'Missing parameters'}), 400
    
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'error': 'Grade not found'}), 404
    
    # Validate input values
    try:
        coursework_val = int(coursework)
        final_exam_val = int(final_exam)
        decision_marks_val = int(decision_marks)
        
        if not (0 <= coursework_val <= 50 and 0 <= final_exam_val <= 50 and 0 <= decision_marks_val <= 10):
            return jsonify({'error': 'Invalid grade values'}), 400
        
        grade.coursework = coursework_val
        grade.final_exam = final_exam_val
        grade.decision_marks = decision_marks_val
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'total': grade.total,
            'evaluation': grade.grade_evaluation
        })
    except ValueError:
        return jsonify({'error': 'Invalid input values'}), 400

@app.route('/instructor/reports')
@login_required
def instructor_reports():
    if current_user.user_type != 'instructor':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    stages = [1, 2, 3, 4]
    semesters = [1, 2]
    
    return render_template('instructor_reports.html', stages=stages, semesters=semesters)

@app.route('/get_all_students', methods=['POST'])
@login_required
def get_all_students():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    report_type = request.form.get('report_type', 'all')  # 'all', 'top10', 'failed', 'passed'
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # جلب جميع الطلاب
    students = Student.query.all()
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        
        # جلب درجات الطالب للمواد المحددة
        student_grades = []
        total_points = 0
        total_units = 0
        passed_courses = 0
        failed_courses = 0
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                student_grades.append({
                    'grade_id': grade.id,
                    'course_id': course.id,
                    'course_name': course.name,
                    'coursework': grade.coursework,
                    'final_exam': grade.final_exam,
                    'decision_marks': grade.decision_marks,
                    'units': course.units,
                    'total': grade.total,
                    'evaluation': grade.grade_evaluation
                })
                
                # حساب المعدل المرجح بالوحدات
                total_points += grade.total * course.units
                total_units += course.units
                
                if grade.total >= 50:
                    passed_courses += 1
                else:
                    failed_courses += 1
        
        # إذا لم يكن للطالب درجات في هذه المرحلة والفصل، تخطي
        if not student_grades:
            continue
        
        # حساب المعدل
        average = total_points / total_units if total_units > 0 else 0
        
        # تحديد التقييم العام
        overall_evaluation = ''
        if average < 50:
            overall_evaluation = 'ضعيف'
        elif average < 60:
            overall_evaluation = 'مقبول'
        elif average < 70:
            overall_evaluation = 'متوسط'
        elif average < 80:
            overall_evaluation = 'جيد'
        elif average < 90:
            overall_evaluation = 'جيد جدا'
        else:
            overall_evaluation = 'امتياز'
        
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'stage': student.stage,
            'grades': student_grades,
            'average': average,
            'passed_courses': passed_courses,
            'failed_courses': failed_courses,
            'total_courses': len(student_grades),
            'evaluation': overall_evaluation
        }
        
        result.append(student_data)
    
    # ترتيب الطلاب حسب الاسم (أبجدياً)
    result.sort(key=lambda x: x['name'])
    
    # تصفية النتائج حسب نوع التقرير
    if report_type == 'top10':
        # في حالة العشرة الأوائل، نقوم أولاً بالترتيب حسب المعدل ثم نأخذ أول 10 طلاب
        result.sort(key=lambda x: x['average'], reverse=True)
        result = result[:10]
    elif report_type == 'failed':
        result = [s for s in result if s['failed_courses'] > 0]  # الطلاب الراسبين
    elif report_type == 'passed':
        result = [s for s in result if s['failed_courses'] == 0]  # الطلاب الناجحين
    
    return jsonify(result)

# Initialize the database and add initial data
def init_db():
    with app.app_context():
        # Check if database file exists
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'examination.db')
        db_exists = os.path.exists(db_path)
        
        # حذف جميع الجداول وإعادة إنشائها
        db.drop_all()
        db.create_all()
        
        # تجاوز فحص وجود مستخدمين في قاعدة البيانات
        # if User.query.count() > 0:
        #     return
            
        # If SQL schema file exists, use it to initialize the database
        if os.path.exists(app.config['SQL_SCHEMA_FILE']):
            # Connect to the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Read SQL file
            with open(app.config['SQL_SCHEMA_FILE'], 'r', encoding='utf-8') as sql_file:
                sql_script = sql_file.read()
                
            # Execute SQL script
            cursor.executescript(sql_script)
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
            
            print("Database initialized from SQL schema file.")
            return
            
        # If SQL file doesn't exist or couldn't be used, initialize with default data
        # Add instructor
        instructor = User(
            username='instructor',
            name='Dr. محمد أحمد',
            user_type='instructor'
        )
        instructor.set_password('password')
        db.session.add(instructor)
        
        # Add courses
        courses_data = [
            # Stage 1, Semester 1
            {'name': 'اساسيات برمجة', 'stage': 1, 'semester': 1, 'units': 4},
            {'name': 'مقدمة في تكنلوجيا المعلومات', 'stage': 1, 'semester': 1, 'units': 3},
            {'name': 'تصميم منطقي', 'stage': 1, 'semester': 1, 'units': 3},
            {'name': 'اقتصاد', 'stage': 1, 'semester': 1, 'units': 2},
            
            # Stage 1, Semester 2
            {'name': 'هياكل متقطعة', 'stage': 1, 'semester': 2, 'units': 3},
            {'name': 'تركيب الحاسوب', 'stage': 1, 'semester': 2, 'units': 4},
            {'name': 'حقوق الانسان', 'stage': 1, 'semester': 2, 'units': 2},
            {'name': 'ديمقراطية', 'stage': 1, 'semester': 2, 'units': 2},
            
            # Stage 2, Semester 1
            {'name': 'برمجة كيانية', 'stage': 2, 'semester': 1, 'units': 4},
            {'name': 'طرق عددية', 'stage': 2, 'semester': 1, 'units': 3},
            {'name': 'معالجات دقيقة', 'stage': 2, 'semester': 1, 'units': 3},
            {'name': 'اللغة العربية', 'stage': 2, 'semester': 1, 'units': 2},
            
            # Stage 2, Semester 2
            {'name': 'نظرية احتسابية', 'stage': 2, 'semester': 2, 'units': 3},
            {'name': 'هياكل بيانات', 'stage': 2, 'semester': 2, 'units': 4},
            {'name': 'احصاء', 'stage': 2, 'semester': 2, 'units': 3},
            {'name': 'جافا', 'stage': 2, 'semester': 2, 'units': 4},
            
            # Stage 3, Semester 1
            {'name': 'بحث ويب', 'stage': 3, 'semester': 1, 'units': 3},
            {'name': 'برمجة مواقع', 'stage': 3, 'semester': 1, 'units': 4},
            {'name': 'رسم بالحاسوب', 'stage': 3, 'semester': 1, 'units': 3},
            {'name': 'قواعد بيانات', 'stage': 3, 'semester': 1, 'units': 4},
            
            # Stage 3, Semester 2
            {'name': 'مترجمات', 'stage': 3, 'semester': 2, 'units': 3},
            {'name': 'بايثون', 'stage': 3, 'semester': 2, 'units': 4},
            {'name': 'ذكاء اصطناعي', 'stage': 3, 'semester': 2, 'units': 4},
            {'name': 'تشفير', 'stage': 3, 'semester': 2, 'units': 3},
            
            # Stage 4, Semester 1
            {'name': 'انترنيت الاشياء', 'stage': 4, 'semester': 1, 'units': 3},
            {'name': 'نظم تشغيل', 'stage': 4, 'semester': 1, 'units': 4},
            {'name': 'معالجة صور', 'stage': 4, 'semester': 1, 'units': 3},
            {'name': 'امنية حواسيب', 'stage': 4, 'semester': 1, 'units': 3},
            
            # Stage 4, Semester 2
            {'name': 'حوسبة سحابية', 'stage': 4, 'semester': 2, 'units': 3},
            {'name': 'تمييز انماط', 'stage': 4, 'semester': 2, 'units': 3},
            {'name': 'شبكات', 'stage': 4, 'semester': 2, 'units': 4},
            {'name': 'تجارة الكترونية', 'stage': 4, 'semester': 2, 'units': 3},
        ]
        
        for course_data in courses_data:
            course = Course(**course_data)
            db.session.add(course)
        
        # Add sample students
        students_data = [
            {'name': 'أحمد علي', 'username': 'ahmed', 'student_id': 'CS2023001', 'stage': 1},
            {'name': 'فاطمة محمد', 'username': 'fatima', 'student_id': 'CS2023002', 'stage': 1},
            {'name': 'علي حسين', 'username': 'ali', 'student_id': 'CS2023003', 'stage': 1},
            {'name': 'زينب عبد الله', 'username': 'zainab', 'student_id': 'CS2022001', 'stage': 2},
            {'name': 'حسن كريم', 'username': 'hassan', 'student_id': 'CS2022002', 'stage': 2},
            {'name': 'نور محمود', 'username': 'noor', 'student_id': 'CS2021001', 'stage': 3},
            {'name': 'محمد جاسم', 'username': 'mohammed', 'student_id': 'CS2021002', 'stage': 3},
            {'name': 'سارة أحمد', 'username': 'sara', 'student_id': 'CS2020001', 'stage': 4},
            {'name': 'عمر فاضل', 'username': 'omar', 'student_id': 'CS2020002', 'stage': 4},
            # إضافة 5 طلاب تجريبيين جدد
            {'name': 'مصطفى كاظم', 'username': 'mustafa', 'student_id': 'CS2023004', 'stage': 1},
            {'name': 'ياسمين عادل', 'username': 'yasmin', 'student_id': 'CS2022003', 'stage': 2},
            {'name': 'حسين علي', 'username': 'hussein', 'student_id': 'CS2021003', 'stage': 3},
            {'name': 'رنا محمد', 'username': 'rana', 'student_id': 'CS2020003', 'stage': 4},
            {'name': 'يوسف أحمد', 'username': 'yousef', 'student_id': 'CS2023005', 'stage': 1},
            # إضافة 5 طلاب تجريبيين إضافيين
            {'name': 'زيد عبد الكريم', 'username': 'zaid', 'student_id': 'CS2023006', 'stage': 1},
            {'name': 'سجى محمود', 'username': 'saja', 'student_id': 'CS2022004', 'stage': 2},
            {'name': 'عبد الله جاسم', 'username': 'abdullah', 'student_id': 'CS2021004', 'stage': 3},
            {'name': 'ليلى حسن', 'username': 'layla', 'student_id': 'CS2020004', 'stage': 4},
            {'name': 'مريم علي', 'username': 'mariam', 'student_id': 'CS2023007', 'stage': 1},
        ]
        
        for student_data in students_data:
            user = User(
                username=student_data['username'],
                name=student_data['name'],
                user_type='student'
            )
            user.set_password('password')
            db.session.add(user)
            db.session.flush()  # To get the user ID
            
            student = Student(
                user_id=user.id,
                student_id=student_data['student_id'],
                stage=student_data['stage']
            )
            db.session.add(student)
        
        db.session.commit()
        
        # Add sample grades
        students = Student.query.all()
        courses = Course.query.all()
        
        import random
        for student in students:
            for course in courses:
                if course.stage == student.stage:
                    # Only add grades for the student's current stage
                    grade = Grade(
                        student_id=student.id,
                        course_id=course.id,
                        coursework=random.randint(30, 45),
                        final_exam=random.randint(30, 45),
                        decision_marks=random.randint(0, 5),
                        academic_year=f"{datetime.now().year-1}/{datetime.now().year}"
                    )
                    db.session.add(grade)
        
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
