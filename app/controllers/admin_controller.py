from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from app.models.student import Student
from app.models.notification import Notification, ActivityLog
from app.algorithms.decision_tree import classify_student, get_classification_reasons
from app.algorithms.quicksort import rank_students, quicksort_students
from app.services.notification_service import notify, log_activity
from app.services.auth_service import hash_password, send_classification_email
import json

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    students = Student.query.all()
    for s in students:
        s.classification = classify_student(s.gpa, s.attendance, s.failures, s.trend)

    total      = len(students)
    advanced   = sum(1 for s in students if s.classification == 'Advanced')
    average    = sum(1 for s in students if s.classification == 'Average')
    at_risk    = sum(1 for s in students if s.classification == 'At-Risk')
    avg_gpa    = round(sum(s.gpa for s in students) / total, 2) if total else 0
    avg_attend = round(sum(s.attendance for s in students) / total, 1) if total else 0

    recent_logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return render_template('admin/dashboard.html',
        students=students, total=total,
        advanced=advanced, average=average, at_risk=at_risk,
        avg_gpa=avg_gpa, avg_attend=avg_attend,
        recent_logs=recent_logs, notif_count=notifs)


# ── Student CRUD ──────────────────────────────────────────────────────────────

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    q      = request.args.get('q', '').strip()
    filter_class = request.args.get('classification', '')

    query = Student.query
    if q:
        query = query.filter(
            db.or_(
                Student.full_name.ilike(f'%{q}%'),
                Student.student_id.ilike(f'%{q}%'),
            )
        )
    all_students = query.all()
    for s in all_students:
        s.classification = classify_student(s.gpa, s.attendance, s.failures, s.trend)

    if filter_class:
        all_students = [s for s in all_students if s.classification == filter_class]

    ranked = rank_students(all_students)
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/students.html',
        ranked=ranked, q=q, filter_class=filter_class, notif_count=notifs)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        full_name  = request.form.get('full_name', '').strip()
        email      = request.form.get('email', '').strip().lower()
        course     = request.form.get('course', '').strip()
        year_level = int(request.form.get('year_level', 1))
        gpa        = float(request.form.get('gpa', 1.0))
        attendance = float(request.form.get('attendance', 100.0))
        failures   = int(request.form.get('failures', 0))
        trend      = request.form.get('trend', 'stable')

        # Subject scores
        subjects = ['Math', 'English', 'Science', 'Filipino', 'MAPEH', 'TLE', 'Values', 'Research']
        scores = {}
        for subj in subjects:
            val = request.form.get(f'score_{subj}', '').strip()
            if val:
                try:
                    scores[subj] = float(val)
                except ValueError:
                    pass

        if Student.query.filter_by(student_id=student_id).first():
            flash('Student ID already exists.', 'danger')
            return render_template('admin/add_student.html')

        classification = classify_student(gpa, attendance, failures, trend)

        student = Student(
            student_id=student_id, full_name=full_name,
            email=email, course=course, year_level=year_level,
            gpa=gpa, attendance=attendance, failures=failures,
            trend=trend, classification=classification,
        )
        student.set_subject_scores(scores)

        # Create linked user account if email given
        if email and not User.query.filter_by(email=email).first():
            user = User(
                email=email, full_name=full_name,
                password_hash=hash_password(student_id),  # default password = student ID
                role='student', is_verified=True,
            )
            db.session.add(user)
            db.session.flush()
            student.user_id = user.id

        db.session.add(student)
        db.session.commit()

        log_activity(current_user.id, 'ADD_STUDENT', f'{student_id} — {full_name}')
        flash(f'Student {full_name} added successfully.', 'success')
        return redirect(url_for('admin.students'))

    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/add_student.html', notif_count=notifs)


@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        student.full_name  = request.form.get('full_name', student.full_name).strip()
        student.email      = request.form.get('email', student.email).strip().lower()
        student.course     = request.form.get('course', '').strip()
        student.year_level = int(request.form.get('year_level', 1))
        student.gpa        = float(request.form.get('gpa', student.gpa))
        student.attendance = float(request.form.get('attendance', student.attendance))
        student.failures   = int(request.form.get('failures', student.failures))
        student.trend      = request.form.get('trend', student.trend)

        subjects = ['Math', 'English', 'Science', 'Filipino', 'MAPEH', 'TLE', 'Values', 'Research']
        scores = student.get_subject_scores()
        for subj in subjects:
            val = request.form.get(f'score_{subj}', '').strip()
            if val:
                try:
                    scores[subj] = float(val)
                except ValueError:
                    pass
        student.set_subject_scores(scores)

        old_class = student.classification
        student.classification = classify_student(
            student.gpa, student.attendance, student.failures, student.trend)

        db.session.commit()

        # Notify student if classification changed
        if old_class != student.classification and student.user_id:
            notify(student.user_id,
                   f'Your classification has been updated to: {student.classification}',
                   'info')
            try:
                send_classification_email(
                    student.email, student.full_name,
                    student.classification, student.gpa)
            except Exception as e:
                print(f'[SAPCPOS] Classification email error: {e}')

        log_activity(current_user.id, 'EDIT_STUDENT',
                     f'{student.student_id} — {student.full_name}')
        flash('Student record updated.', 'success')
        return redirect(url_for('admin.students'))

    scores = student.get_subject_scores()
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/edit_student.html',
                           student=student, scores=scores, notif_count=notifs)


@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    name = student.full_name
    sid  = student.student_id
    if student.user_id:
        user = User.query.get(student.user_id)
        if user:
            db.session.delete(user)
    db.session.delete(student)
    db.session.commit()
    log_activity(current_user.id, 'DELETE_STUDENT', f'{sid} — {name}')
    flash(f'Student {name} deleted.', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/classify')
@login_required
@admin_required
def classify_view(student_id):
    student = Student.query.get_or_404(student_id)
    classification = classify_student(
        student.gpa, student.attendance, student.failures, student.trend)
    reasons = get_classification_reasons(
        student.gpa, student.attendance, student.failures, student.trend)
    student.classification = classification
    db.session.commit()
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/classify.html',
        student=student, classification=classification,
        reasons=reasons, notif_count=notifs)


# ── Rankings ──────────────────────────────────────────────────────────────────

@admin_bp.route('/rankings')
@login_required
@admin_required
def rankings():
    students = Student.query.all()
    for s in students:
        s.classification = classify_student(s.gpa, s.attendance, s.failures, s.trend)
    ranked = rank_students(students)
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/rankings.html', ranked=ranked, notif_count=notifs)


# ── Analytics ─────────────────────────────────────────────────────────────────

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    students = Student.query.all()
    for s in students:
        s.classification = classify_student(s.gpa, s.attendance, s.failures, s.trend)

    # Classification distribution
    dist = {'Advanced': 0, 'Average': 0, 'At-Risk': 0}
    for s in students:
        dist[s.classification] = dist.get(s.classification, 0) + 1

    # Trend distribution
    trend_dist = {'improving': 0, 'stable': 0, 'declining': 0}
    for s in students:
        trend_dist[s.trend] = trend_dist.get(s.trend, 0) + 1

    # Scatter data: attendance vs GPA
    scatter = [{'x': s.attendance, 'y': s.gpa,
                'label': s.full_name, 'class': s.classification}
               for s in students]

    # GPA histogram buckets
    buckets = {'1.0-1.5': 0, '1.5-2.0': 0, '2.0-2.5': 0,
               '2.5-3.0': 0, '3.0+': 0}
    for s in students:
        if s.gpa <= 1.5:   buckets['1.0-1.5'] += 1
        elif s.gpa <= 2.0: buckets['1.5-2.0'] += 1
        elif s.gpa <= 2.5: buckets['2.0-2.5'] += 1
        elif s.gpa <= 3.0: buckets['2.5-3.0'] += 1
        else:              buckets['3.0+'] += 1

    total = len(students)
    avg_gpa = round(sum(s.gpa for s in students) / total, 2) if total else 0
    avg_att = round(sum(s.attendance for s in students) / total, 1) if total else 0

    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/analytics.html',
        students=students, dist=dist, trend_dist=trend_dist,
        scatter=json.dumps(scatter), buckets=json.dumps(buckets),
        total=total, avg_gpa=avg_gpa, avg_att=avg_att, notif_count=notifs)


# ── Activity Logs ─────────────────────────────────────────────────────────────

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    logs_q = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False)
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('admin/logs.html', logs=logs_q, notif_count=notifs)


# ── Notifications ─────────────────────────────────────────────────────────────

@admin_bp.route('/notifications')
@login_required
@admin_required
def notifications():
    notifs_list = Notification.query.filter_by(
        user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Mark all read
    for n in notifs_list:
        n.is_read = True
    db.session.commit()
    return render_template('admin/notifications.html',
        notifs_list=notifs_list, notif_count=0)
