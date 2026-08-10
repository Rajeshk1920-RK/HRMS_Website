"""Careers / job-posting routes (moved verbatim from app.py).

These routes use raw SQL through get_db_connection(), same as before.
"""
import os

from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

from app.config import UPLOAD_FOLDER
from app.extensions import get_db_connection

careers_bp = Blueprint('careers', __name__)


@careers_bp.route('/admin/add_job', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        jobtitle = request.form['jobtitle']
        exp = request.form['exp']
        sal = request.form['sal']
        location = request.form['location']
        desc = request.form['desc']
        file = request.files['banner']
        filename = ''

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO TblCareers (JobTitle, Exp, Sal, Location, Description, BannerImg) VALUES (%s, %s, %s, %s, %s, %s)',
                     (jobtitle, exp, sal, location, desc, filename))
        conn.commit()
        conn.close()
        return redirect(url_for('careers.view_jobs'))
    return render_template('careers/add_job.html')

@careers_bp.route('/admin/view_jobs')
def view_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM TblCareers')
    jobs = cursor.fetchall()
    conn.close()
    return render_template('careers/view_jobs.html', jobs=jobs)

@careers_bp.route('/admin/delete_job/<int:id>')
def delete_job(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT BannerImg FROM TblCareers WHERE CareerId = %s', (id,))
    job = cursor.fetchone()

    if job and job['BannerImg']:
        img_path = os.path.join(UPLOAD_FOLDER, job['BannerImg'])
        if os.path.exists(img_path):
            os.remove(img_path)

    cursor.execute('DELETE FROM TblCareers WHERE CareerId = %s', (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('careers.view_jobs'))

@careers_bp.route('/admin/edit_job/<int:id>', methods=['GET', 'POST'])
def edit_job(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM TblCareers WHERE CareerId = %s', (id,))
    job = cursor.fetchone()

    if request.method == 'POST':
        jobtitle = request.form['jobtitle']
        exp = request.form['exp']
        sal = request.form['sal']
        location = request.form['location']
        desc = request.form['desc']
        file = request.files['banner']
        filename = job['BannerImg']

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        cursor.execute('UPDATE TblCareers SET JobTitle=%s, Exp=%s, Sal=%s, Location=%s, Description=%s, BannerImg=%s WHERE CareerId=%s',
                     (jobtitle, exp, sal, location, desc, filename, id))
        conn.commit()
        conn.close()
        return redirect(url_for('careers.view_jobs'))

    conn.close()
    return render_template('careers/edit_job.html', job=job)

@careers_bp.route('/employee/careers')
def employee_careers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM TblCareers')
    jobs = cursor.fetchall()
    conn.close()
    return render_template('careers/employee_careers.html', jobs=jobs)
