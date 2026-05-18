CREATE DATABASE IF NOT EXISTS spa_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE spa_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash CHAR(64) NOT NULL,
    role ENUM('admin', 'faculty', 'student') NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    department VARCHAR(80) NOT NULL,
    prn VARCHAR(40) NOT NULL UNIQUE,
    user_id INT NOT NULL UNIQUE,
    marks DECIMAL(5,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_students_marks CHECK (marks BETWEEN 0 AND 100),
    CONSTRAINT fk_students_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS student_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject VARCHAR(100) NOT NULL,
    marks DECIMAL(5,2) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_student_marks_range CHECK (marks BETWEEN 0 AND 100),
    CONSTRAINT uq_student_subject UNIQUE (student_id, subject),
    CONSTRAINT fk_student_marks_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_student_marks_subject
        FOREIGN KEY (subject) REFERENCES subjects(name)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS faculty_subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_faculty_subject UNIQUE (faculty_id, subject_name),
    CONSTRAINT fk_faculty_subjects_faculty
        FOREIGN KEY (faculty_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_faculty_subjects_subject
        FOREIGN KEY (subject_name) REFERENCES subjects(name)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(80) NOT NULL,
    details TEXT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO users(username, password_hash, role)
VALUES
('admin', SHA2('adminpass', 256), 'admin')
ON DUPLICATE KEY UPDATE username = VALUES(username);

DROP VIEW IF EXISTS vw_student_performance;
DROP VIEW IF EXISTS vw_student_gpa;
DROP VIEW IF EXISTS vw_faculty_subject_access;
DROP VIEW IF EXISTS v_analytics_summary;
DROP VIEW IF EXISTS v_audit_recent;
DROP VIEW IF EXISTS v_student_portal;

CREATE OR REPLACE VIEW v_student_portal AS
SELECT
    s.id AS student_id,
    s.prn,
    s.name,
    s.department,
    sm.subject,
    sm.marks
FROM students s
LEFT JOIN student_marks sm ON sm.student_id = s.id;

CREATE OR REPLACE VIEW v_analytics_summary AS
SELECT
    COUNT(DISTINCT s.id) AS total_students,
    ROUND(AVG(sm.marks), 2) AS average_marks,
    MAX(sm.marks) AS highest_marks,
    MIN(sm.marks) AS lowest_marks,
    SUM(CASE WHEN sm.marks >= 90 THEN 1 ELSE 0 END) AS grade_a_count,
    SUM(CASE WHEN sm.marks >= 75 AND sm.marks < 90 THEN 1 ELSE 0 END) AS grade_b_count,
    SUM(CASE WHEN sm.marks >= 60 AND sm.marks < 75 THEN 1 ELSE 0 END) AS grade_c_count,
    SUM(CASE WHEN sm.marks >= 40 AND sm.marks < 60 THEN 1 ELSE 0 END) AS grade_d_count,
    SUM(CASE WHEN sm.marks < 40 THEN 1 ELSE 0 END) AS grade_f_count
FROM students s
LEFT JOIN student_marks sm ON sm.student_id = s.id;

CREATE OR REPLACE VIEW v_audit_recent AS
SELECT
    a.id,
    COALESCE(u.username, 'SYSTEM') AS username,
    a.action,
    a.details,
    a.timestamp
FROM audit_log a
LEFT JOIN users u ON u.id = a.user_id
ORDER BY a.timestamp DESC;

CREATE USER IF NOT EXISTS 'spa_admin'@'localhost' IDENTIFIED BY 'admin123';
CREATE USER IF NOT EXISTS 'spa_faculty'@'localhost' IDENTIFIED BY 'faculty123';
CREATE USER IF NOT EXISTS 'spa_student'@'localhost' IDENTIFIED BY 'student123';

GRANT ALL PRIVILEGES ON spa_db.* TO 'spa_admin'@'localhost';
GRANT SELECT, INSERT, UPDATE ON spa_db.* TO 'spa_faculty'@'localhost';
GRANT SELECT ON spa_db.* TO 'spa_student'@'localhost';

FLUSH PRIVILEGES;
