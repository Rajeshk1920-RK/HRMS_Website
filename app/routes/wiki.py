"""Wiki category, page and view routes (moved verbatim from app.py)."""
import os

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

from app.config import WIKI_CAT_FOLDER
from app.extensions import db

wiki_bp = Blueprint('wiki', __name__)


# ------ Wiki Category Management --------------------
@wiki_bp.route('/admin/wiki_categories', methods=['GET', 'POST'])
def admin_wiki_categories():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        category = request.form['category'].strip()
        img_file = request.files.get('cat_img')
        img_filename = None
        if img_file and img_file.filename:
            filename = secure_filename(img_file.filename)
            img_file.save(os.path.join(WIKI_CAT_FOLDER, filename))
            img_filename = filename
        db.add_wiki_category(category, img_filename)
        flash(f'Wiki category "{category}" added.', 'success')
        return redirect(url_for('wiki.admin_wiki_categories', msg=f'"{category}" saved'))
    cats = db.get_wiki_categories()
    msg = request.args.get('msg')
    return render_template('wiki/admin_wiki_category.html', cats=cats, msg=msg)

@wiki_bp.route('/admin/edit_wiki_category/<int:cat_id>', methods=['POST'])
def edit_wiki_category(cat_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    new_cat = request.form['new_category'].strip()
    img_file = request.files.get('new_cat_img')
    img_filename = None
    if img_file and img_file.filename:
        filename = secure_filename(img_file.filename)
        img_file.save(os.path.join(WIKI_CAT_FOLDER, filename))
        img_filename = filename
    db.update_wiki_category(cat_id, new_cat, img_filename)
    flash(f'Category updated to "{new_cat}"', 'success')
    return redirect(url_for('wiki.admin_wiki_categories'))

@wiki_bp.route('/admin/delete_wiki_category/<int:cat_id>')
def delete_wiki_category(cat_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    db.delete_wiki_category(cat_id)
    flash('Wiki category deleted', 'success')
    return redirect(url_for('wiki.admin_wiki_categories'))


# ------ Wiki Pages Management -----------------------
@wiki_bp.route('/admin/add_wiki', methods=['GET', 'POST'])
def add_wiki():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        category_id = request.form['category_id']
        title       = request.form['title'].strip()
        descr       = request.form['descr']
        db.add_wiki_page(category_id, title, descr)
        flash(f'Wiki "{title}" added.', 'success')
        return redirect(url_for('wiki.view_wikis'))
    categories = db.get_wiki_categories()
    return render_template('wiki/add_wiki.html', categories=categories)

@wiki_bp.route('/admin/view_wikis')
def view_wikis():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    wikis = db.get_wiki_pages()
    return render_template('wiki/view_wikis.html', wikis=wikis)

@wiki_bp.route('/admin/edit_wiki/<int:wiki_id>', methods=['GET', 'POST'])
def edit_wiki(wiki_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    page = db.get_wiki_page(wiki_id)
    if not page:
        flash('Wiki not found.', 'error')
        return redirect(url_for('wiki.view_wikis'))
    if request.method == 'POST':
        category_id = request.form['category_id']
        title       = request.form['title'].strip()
        descr       = request.form['descr']
        db.update_wiki_page(wiki_id, category_id, title, descr)
        flash(f'Wiki "{title}" updated.', 'success')
        return redirect(url_for('wiki.view_wikis'))
    categories = db.get_wiki_categories()
    return render_template('wiki/edit_wiki.html', page=page, categories=categories)

@wiki_bp.route('/admin/delete_wiki/<int:wiki_id>')
def delete_wiki(wiki_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    db.soft_delete_wiki_page(wiki_id)
    flash('Wiki deleted', 'success')
    return redirect(url_for('wiki.view_wikis'))

# ------ Employee: list all Wikis ----------------
@wiki_bp.route('/employee/wiki')
def employee_wiki_list():
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))
    wikis = db.get_wiki_pages()
    return render_template('wiki/wiki_list.html', wikis=wikis)

# ------ Employee: view a single Wiki ------------
@wiki_bp.route('/employee/wiki/<int:wiki_id>')
def wiki_detail(wiki_id):
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))
    page = db.get_wiki_page(wiki_id)
    if not page:
        flash('Wiki not found.', 'error')
        return redirect(url_for('wiki.employee_wiki_list'))
    # record the view
    db.add_wiki_view(wiki_id, session['user_id'])
    return render_template('wiki/wiki_detail.html', page=page)

# ------ Admin: view Wiki Views -----------------
@wiki_bp.route('/admin/wiki_views')
def admin_wiki_views():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    # read filter params
    start = request.args.get('start_date', default=None)
    end   = request.args.get('end_date',   default=None)
    wiki  = request.args.get('wiki_id',    type=int)

    # fetch data
    counts = db.get_wiki_view_counts(start, end)
    views  = db.get_wiki_views_filtered(start, end, wiki)
    pages  = db.get_wiki_pages()  # for the filter dropdown

    return render_template(
        'wiki/view_wiki_views.html',
        counts=counts,
        views=views,
        pages=pages,
        filter_start=start,
        filter_end=end,
        filter_wiki=wiki
    )
