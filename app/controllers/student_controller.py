from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.student import Student
from app.models.notification import Notification
from app.algorithms.decision_tree import classify_student, get_classification_reasons
from app.algorithms.quicksort import rank_students
from app.algorithms.dijkstra import get_pathway, get_course_description, ALL_COURSES, TRACK_STARTS
from app.services.notification_service import log_activity

student_bp = Blueprint('student', __name__)


def _get_student():
    return Student.query.filter_by(user_id=current_user.id).first()


def _notif_count():
    return Notification.query.filter_by(
        user_id=current_user.id, is_read=False).count()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@student_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))

    student = _get_student()
    if not student:
        flash('No student record linked to your account. Contact your admin.', 'warning')
        return render_template('student/no_record.html', notif_count=0)

    classification = classify_student(
        student.gpa, student.attendance, student.failures, student.trend)
    student.classification = classification
    db.session.commit()

    reasons  = get_classification_reasons(
        student.gpa, student.attendance, student.failures, student.trend)
    pathways = get_pathway(student.get_interests()) if student.get_interests() else {}
    scores   = student.get_subject_scores()

    # Rank among all students
    all_students = Student.query.all()
    for s in all_students:
        s.classification = classify_student(s.gpa, s.attendance, s.failures, s.trend)
    ranked = rank_students(all_students)
    my_rank = next((r for r, s in ranked if s.id == student.id), None)

    return render_template('student/dashboard.html',
        student=student, classification=classification,
        reasons=reasons, pathways=pathways, scores=scores,
        my_rank=my_rank, total_students=len(all_students),
        notif_count=_notif_count())


# ── Profile ───────────────────────────────────────────────────────────────────

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))

    student = _get_student()
    if not student:
        flash('No student record found.', 'warning')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        selected_interests = request.form.getlist('interests')
        student.set_interests(selected_interests)
        db.session.commit()
        log_activity(current_user.id, 'UPDATE_INTERESTS',
                     f'Interests: {", ".join(selected_interests)}')
        flash('Interests updated! Your pathway has been recalculated.', 'success')
        return redirect(url_for('student.profile'))

    all_interests = ['STEM', 'Business', 'Arts']
    current_interests = student.get_interests()
    scores = student.get_subject_scores()
    return render_template('student/profile.html',
        student=student, all_interests=all_interests,
        current_interests=current_interests, scores=scores,
        notif_count=_notif_count())


# ── Pathway ───────────────────────────────────────────────────────────────────

@student_bp.route('/pathway')
@login_required
def pathway():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))

    student = _get_student()
    if not student:
        return redirect(url_for('student.dashboard'))

    interests = student.get_interests()
    pathways  = get_pathway(interests) if interests else get_pathway(['STEM', 'Business', 'Arts'])
    course_descriptions = {c: get_course_description(c) for c in ALL_COURSES}

    return render_template('student/pathway.html',
        student=student, pathways=pathways,
        course_descriptions=course_descriptions,
        track_starts=TRACK_STARTS,
        notif_count=_notif_count())


# ── Rankings (read-only for students) ────────────────────────────────────────

@student_bp.route('/rankings')
@login_required
def rankings():
    if current_user.is_admin():
        return redirect(url_for('admin.rankings'))

    student = _get_student()
    all_students = Student.query.all()
    for s in all_students:
        s.classification = classify_student(s.gpa, s.attendance, s.failures, s.trend)
    ranked = rank_students(all_students)

    return render_template('student/rankings.html',
        ranked=ranked, my_student=student,
        notif_count=_notif_count())


# ── Notifications ─────────────────────────────────────────────────────────────

@student_bp.route('/notifications')
@login_required
def notifications():
    notifs_list = Notification.query.filter_by(
        user_id=current_user.id).order_by(
        Notification.created_at.desc()).all()
    for n in notifs_list:
        n.is_read = True
    db.session.commit()
    return render_template('student/notifications.html',
        notifs_list=notifs_list, notif_count=0)
