from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from concurrent.futures import ThreadPoolExecutor
import atexit

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithm_app.main import main_flask_async as process_query_algorithm

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myuser:mysecretpassword@localhost:5432/mydb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'signin'
login_manager.login_message_category = 'info'

executor = ThreadPoolExecutor(max_workers=2)


# --- Models ---

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class SearchQuery(db.Model):
    __tablename__ = 'search_query'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('public.user.id'), nullable=False)
    keywords = db.Column(db.String, nullable=False)
    country = db.Column(db.String)
    status = db.Column(db.String, default='submitted')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    whitelist_words = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<SearchQuery {self.id} by User {self.user_id}>'


class SearchResult(db.Model):
    __tablename__ = 'search_result'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    query_id = db.Column(db.Integer, db.ForeignKey('public.search_query.id'), nullable=False)
    website_url = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    country = db.Column(db.String, nullable=True)
    is_exported = db.Column(db.Boolean, nullable=True, default=False)
    scraped_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    def __repr__(self):
        return f'<SearchResult {self.id} for Query {self.query_id}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Forms ---

class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')


class SignInForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class QueryForm(FlaskForm):
    keywords = StringField('Keywords', validators=[DataRequired()])
    country = SelectField('Country', choices=[
        ('GB', 'United Kingdom'),
        ('PT', 'Portugal'),
        ('ES', 'Spain')
    ], validators=[DataRequired()])
    whitelist_words = StringField('Whitelist Words (comma-separated)', validators=[DataRequired()])
    submit = SubmitField('Find')


# --- Helpers for background task ---

def run_algorithm_task(query_id):
    """
    Wrapper to call the algorithm and handle application context for database access
    if the algorithm needs it directly (though it's better if it doesn't).
    """
    with app.app_context():
        if not hasattr(db, 'session'):
            print(
                f"CRITICAL DEBUG [run_algorithm_task]: Global 'db' object in app.py does NOT have a 'session' attribute before calling algorithm!")

        try:
            process_query_algorithm(
                query_id=query_id,
                db_instance=db,
                search_result_model=SearchResult,
                search_query_model=SearchQuery
            )
        except Exception as e:
            app.logger.error(f"Error in background algorithm task for query_id {query_id}: {e}", exc_info=True)


def shutdown_executor():
    print("Shutting down ThreadPoolExecutor...")
    executor.shutdown(wait=True)
    print("ThreadPoolExecutor shut down.")


atexit.register(shutdown_executor)


# --- Routes (home, signup, signin, logout - as defined before) ---

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user sign-up."""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = SignUpForm()
    if form.validate_on_submit():
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username or email already exists. Please choose different ones.', 'danger')
            return render_template('signup.html', form=form)

        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Account created successfully! You can now sign in.', 'success')
            return redirect(url_for('signin'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')

    return render_template('signup.html', form=form)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """Handles user sign-in."""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = SignInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('signin.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Logs the user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/download_result/<int:query_id>')
@login_required
def download_result(query_id):
    search_query_item = db.session.get(SearchQuery, query_id)

    if not search_query_item:
        flash('Search query not found.', 'danger')
        return redirect(url_for('query'))

    if search_query_item.user_id != current_user.id:
        flash('You are not authorized to download this file.', 'danger')
        return redirect(url_for('query'))

    if search_query_item.status != 'completed':
        flash('The analysis for this query is not yet completed or has failed.', 'warning')
        return redirect(url_for('query'))

    search_result_item = SearchResult.query.filter_by(query_id=query_id).order_by(SearchResult.id.desc()).first()

    if not search_result_item or not search_result_item.website_url:
        flash('Result file path not found for this query.', 'danger')
        return redirect(url_for('query'))

    file_path = search_result_item.website_url

    if not os.path.exists(file_path):
        flash(f'Error: File not found on server at path: {file_path}. Please contact support.', 'danger')
        app.logger.error(f"File not found for download. Query ID: {query_id}, Path: {file_path}")
        return redirect(url_for('query'))

    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
    except Exception as e:
        app.logger.error(f"Error sending file for query_id {query_id}: {e}", exc_info=True)
        flash('An error occurred while trying to download the file.', 'danger')
        return redirect(url_for('query'))


@app.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    form = QueryForm()
    if form.validate_on_submit():
        new_query = SearchQuery(
            user_id=current_user.id,
            keywords=form.keywords.data,
            country=form.country.data,
            whitelist_words=form.whitelist_words.data,
            status='submitted'
        )
        db.session.add(new_query)
        try:
            db.session.commit()
            query_id_for_algorithm = new_query.id
            executor.submit(run_algorithm_task, query_id_for_algorithm)
            flash(f'Query saved (ID: {query_id_for_algorithm}) and processing started!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while saving query: {e}', 'danger')
            app.logger.error(f"Error during query submission: {e}", exc_info=True)
        return redirect(url_for('query'))

    queries_list = SearchQuery.query.filter_by(user_id=current_user.id).order_by(SearchQuery.created_at.desc()).all()
    return render_template('query.html', form=form, queries=queries_list)


@app.route('/')
def home():
    """Renders the home page."""
    return render_template('index.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
