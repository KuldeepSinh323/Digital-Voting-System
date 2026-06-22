from flask import Flask, render_template, request, make_response, g, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from redis import Redis
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os
import socket
import random
import json
import logging

option_a = os.getenv('OPTION_A', "India")
option_b = os.getenv('OPTION_B', "USA")
hostname = socket.gethostname()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.context_processor
def inject_user_role():
    return {
        'user_role': current_user.role if current_user.is_authenticated else 'guest'
    }

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

db_initialized = False

class User(UserMixin):
    def __init__(self, id, username, role='user'):
        self.id = id
        self.username = username
        self.role = role
    
    def is_admin(self):
        return self.role == 'admin'

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(user['id'], user['username'], user.get('role', 'user'))
    return None

def get_db():
    if not hasattr(g, 'db'):
        g.db = psycopg2.connect("host=db dbname=postgres user=postgres password=postgres")
    return g.db

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id VARCHAR(255) NOT NULL UNIQUE,
            vote VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS voting_options (
            id SERIAL PRIMARY KEY,
            option_a VARCHAR(255) NOT NULL,
            option_b VARCHAR(255) NOT NULL,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT FALSE
        )
    ''')
    try:
        cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
    try:
        cur.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
    cur.close()

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis

@app.before_request
def ensure_db_initialized():
    global db_initialized
    if not db_initialized:
        init_db()
        db_initialized = True

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('hello'))
    return render_template('home.html', user_role='guest')

@app.route('/about')
def about():
    return render_template('about.html', user_role=current_user.role if current_user.is_authenticated else 'guest')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_role=current_user.role)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('hello'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (form.username.data,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user['password_hash'], form.password.data):
            user_obj = User(user['id'], user['username'])
            login_user(user_obj)
            return redirect(url_for('hello'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (form.username.data, generate_password_hash(form.password.data)))
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Username already exists')
        cur.close()
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/results')
@login_required
@admin_required
def results_page():
    conn = get_db()
    cur = conn.cursor()
    
    # Get current active voting options
    cur.execute("SELECT option_a, option_b FROM voting_options WHERE is_active = TRUE LIMIT 1")
    active_option = cur.fetchone()
    
    if active_option:
        current_option_a = active_option[0]
        current_option_b = active_option[1]
    else:
        # Fallback to default options
        current_option_a = option_a
        current_option_b = option_b
    
    cur.execute("SELECT COUNT(*) FROM votes WHERE vote = 'a'")
    option_a_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM votes WHERE vote = 'b'")
    option_b_count = cur.fetchone()[0]
    cur.close()
    return render_template('results.html', 
                         option_a=current_option_a, 
                         option_b=current_option_b,
                         option_a_count=option_a_count, 
                         option_b_count=option_b_count, 
                         user_role=current_user.role)

@app.route('/user-management')
@login_required
@admin_required
def user_management():
    return render_template('user_management.html')

@app.route('/api/users')
@login_required
@admin_required
def get_users():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, role, created_at, last_login FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close()
    users_list = []
    for user in users:
        user_dict = dict(user)
        if user_dict['created_at']:
            user_dict['created_at'] = user_dict['created_at'].isoformat()
        if user_dict['last_login']:
            user_dict['last_login'] = user_dict['last_login'].isoformat()
        users_list.append(user_dict)
    return jsonify(users_list)

@app.route('/api/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password():
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')
    
    if not user_id or not new_password:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                    (generate_password_hash(new_password), user_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/update-user-role', methods=['POST'])
@login_required
@admin_required
def update_user_role():
    data = request.get_json()
    user_id = data.get('user_id')
    role = data.get('role')
    
    if not user_id or role not in ['user', 'admin']:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'User role updated successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/delete-user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID required'}), 400
    
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/vote_details')
@login_required
def vote_details():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT v.id, v.vote, v.timestamp FROM votes v ORDER BY v.timestamp DESC")
    votes = cur.fetchall()
    cur.close()
    return jsonify(votes)

@app.route('/voting-creation')
@login_required
@admin_required
def voting_creation():
    return render_template('voting_creation.html')

@app.route('/api/voting-options')
@login_required
@admin_required
def get_voting_options():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, option_a, option_b, created_by, created_at, is_active FROM voting_options ORDER BY created_at DESC")
    options = cur.fetchall()
    cur.close()
    options_list = []
    for option in options:
        option_dict = dict(option)
        if option_dict['created_at']:
            option_dict['created_at'] = option_dict['created_at'].isoformat()
        options_list.append(option_dict)
    return jsonify(options_list)

@app.route('/api/create-voting-option', methods=['POST'])
@login_required
@admin_required
def create_voting_option():
    data = request.get_json()
    option_a = data.get('option_a')
    option_b = data.get('option_b')
    
    if not option_a or not option_b:
        return jsonify({'success': False, 'message': 'Both options are required'}), 400
    
    if len(option_a.strip()) == 0 or len(option_b.strip()) == 0:
        return jsonify({'success': False, 'message': 'Options cannot be empty'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        # First, set all existing options to inactive
        cur.execute("UPDATE voting_options SET is_active = FALSE")
        
        # Then create the new active option
        cur.execute("INSERT INTO voting_options (option_a, option_b, created_by, is_active) VALUES (%s, %s, %s, TRUE)", 
                   (option_a.strip(), option_b.strip(), current_user.id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Voting option created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/activate-voting-option', methods=['POST'])
@login_required
@admin_required
def activate_voting_option():
    data = request.get_json()
    option_id = data.get('option_id')
    
    if not option_id:
        return jsonify({'success': False, 'message': 'Option ID required'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        # Set all options to inactive first
        cur.execute("UPDATE voting_options SET is_active = FALSE")
        # Then activate the selected option
        cur.execute("UPDATE voting_options SET is_active = TRUE WHERE id = %s", (option_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Voting option activated successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/delete-voting-option', methods=['POST'])
@login_required
@admin_required
def delete_voting_option():
    data = request.get_json()
    option_id = data.get('option_id')
    
    if not option_id:
        return jsonify({'success': False, 'message': 'Option ID required'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM voting_options WHERE id = %s", (option_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Voting option deleted successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/current-voting-option')
def get_current_voting_option():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT option_a, option_b FROM voting_options WHERE is_active = TRUE LIMIT 1")
    active_option = cur.fetchone()
    cur.close()
    
    if active_option:
        return jsonify({'option_a': active_option['option_a'], 'option_b': active_option['option_b']})
    else:
        # Return default options if no active option is set
        return jsonify({'option_a': option_a, 'option_b': option_b})

@app.route('/api/results')
@login_required
@admin_required
def api_results():
    conn = get_db()
    cur = conn.cursor()
    
    # Get current active voting options
    cur.execute("SELECT option_a, option_b FROM voting_options WHERE is_active = TRUE LIMIT 1")
    active_option = cur.fetchone()
    
    if active_option:
        a_label = active_option[0]
        b_label = active_option[1]
    else:
        # Fallback to default options
        a_label = option_a
        b_label = option_b
    
    cur.execute("SELECT COUNT(*) FROM votes WHERE vote = 'a'")
    a_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM votes WHERE vote = 'b'")
    b_count = cur.fetchone()[0]
    total = a_count + b_count
    a_percent = (a_count / total * 100) if total > 0 else 0
    b_percent = (b_count / total * 100) if total > 0 else 0
    cur.close()
    return jsonify({
        'a_label': a_label,
        'b_label': b_label,
        'a_count': a_count,
        'b_count': b_count,
        'a_percent': a_percent,
        'b_percent': b_percent
    })

@app.route("/vote", methods=['POST','GET'])
@login_required
def hello():
    voter_id = str(current_user.id)

    vote = None

    if request.method == 'POST':
        vote = request.form['vote']
        app.logger.info('Received vote for %s', vote)
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM votes WHERE id = %s", (voter_id,))
        if cur.fetchone():
            cur.execute("UPDATE votes SET vote = %s WHERE id = %s", (vote, voter_id))
        else:
            cur.execute("INSERT INTO votes (id, vote) VALUES (%s, %s)", (voter_id, vote))
        conn.commit()
        cur.close()

    # Get current active voting options
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT option_a, option_b FROM voting_options WHERE is_active = TRUE LIMIT 1")
    active_option = cur.fetchone()
    cur.close()
    
    if active_option:
        current_option_a = active_option['option_a']
        current_option_b = active_option['option_b']
    else:
        # Fallback to default options
        current_option_a = option_a
        current_option_b = option_b

    resp = make_response(render_template(
        'index.html',
        option_a=current_option_a,
        option_b=current_option_b,
        hostname=hostname,
        vote=vote,
        username=current_user.username,
        user_role=current_user.role
    ))
    return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
