-- إنشاء قاعدة بيانات نظام إدارة الامتحانات
-- هذا الملف يحتوي على استعلامات إنشاء جداول قاعدة البيانات للمشروع

-- حذف الجداول إذا كانت موجودة مسبقاً
DROP TABLE IF EXISTS grade;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS user;

-- إنشاء جدول المستخدمين
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    name VARCHAR(100) NOT NULL,
    user_type VARCHAR(20) NOT NULL
);

-- إنشاء جدول الطلاب
CREATE TABLE student (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    student_id VARCHAR(20) NOT NULL UNIQUE,
    stage INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- إنشاء جدول المقررات الدراسية
CREATE TABLE course (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    stage INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    units INTEGER NOT NULL
);

-- إنشاء جدول الدرجات
CREATE TABLE grade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    coursework INTEGER NOT NULL DEFAULT 0,
    final_exam INTEGER NOT NULL DEFAULT 0,
    decision_marks INTEGER NOT NULL DEFAULT 0,
    academic_year VARCHAR(20) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (course_id) REFERENCES course(id)
);

-- إنشاء فهارس لتحسين الأداء
CREATE INDEX idx_student_user_id ON student(user_id);
CREATE INDEX idx_grade_student_id ON grade(student_id);
CREATE INDEX idx_grade_course_id ON grade(course_id);
CREATE INDEX idx_course_stage_semester ON course(stage, semester);

-- إضافة بيانات تجريبية - مستخدمين (مدرس وطالب)
INSERT INTO user (username, password_hash, name, user_type) VALUES 
('instructor1', 'pbkdf2:sha256:150000$KDoXoFEH$d37d747b82d7ed4631c4e4b196d5f4b584f95f0e2f3c2f3d28942e3f9e2e8c7d', 'أحمد محمد', 'instructor'),
('student1', 'pbkdf2:sha256:150000$KDoXoFEH$d37d747b82d7ed4631c4e4b196d5f4b584f95f0e2f3c2f3d28942e3f9e2e8c7d', 'علي حسن', 'student');

-- إضافة بيانات تجريبية - طلاب
INSERT INTO student (user_id, student_id, stage) VALUES 
(2, '2023001', 1);

-- إضافة بيانات تجريبية - مقررات دراسية
INSERT INTO course (name, stage, semester, units) VALUES 
('برمجة الحاسوب', 1, 1, 4),
('رياضيات متقدمة', 1, 1, 3),
('أساسيات قواعد البيانات', 1, 2, 4),
('هندسة البرمجيات', 1, 2, 3);

-- إضافة بيانات تجريبية - درجات
INSERT INTO grade (student_id, course_id, coursework, final_exam, decision_marks, academic_year) VALUES 
(1, 1, 40, 45, 5, '2023/2024'),
(1, 2, 35, 40, 3, '2023/2024'),
(1, 3, 42, 43, 4, '2023/2024'),
(1, 4, 38, 41, 2, '2023/2024');
