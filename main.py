from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'xyzsdfg'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'user-system'

mysql = MySQL(app)

# Home Route
@app.route('/')
def home():
    return render_template("index.html")

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s AND password = %s', (email, password,))
        user = cursor.fetchone()

        if user:
            session['loggedin'] = True
            session['userid'] = user['userid']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            
            # Redirect based on role
            if session['role'] == 'recruiter':
                return redirect(url_for('recruiter_dashboard'))
            else:
                return redirect(url_for('resume_template'))
        else:
            message = 'Incorrect email or password!'

    return render_template('login.html', message=message)

# Logout Route
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Clear the session to log the user out
    session.clear()

    # Flash a message to indicate successful logout (optional)
    flash("You have been logged out.", "success")

    # Redirect to the login page after logout
    return redirect(url_for('login'))

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and all(k in request.form for k in ('name', 'password', 'email', 'role')):
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            message = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not userName or not password or not email:
            message = 'Please fill out the form!'
        else:
            try:
                cursor.execute('INSERT INTO user (name, email, password, role) VALUES (%s, %s, %s, %s)', (userName, email, password, role))
                mysql.connection.commit()
                flash("Registered successfully!", "success")
                return redirect(url_for('login'))
            except MySQLdb.IntegrityError as e:
                message = f'Registration failed: {str(e)}'
    elif request.method == 'POST':
        message = 'Please fill out the form!'

    return render_template('register.html', message=message)

# Recruiter Dashboard Route
@app.route('/recruiter_dashboard')
def recruiter_dashboard():
    if 'loggedin' in session and session.get('role') == 'recruiter':
        return render_template("recuiter.html")
    else:
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

# Resume Template Routes
@app.route('/resume_1')
def resume_1():
    return render_template("resume_1.html")

@app.route('/resume_2')
def resume_2():
    return render_template("resume_2.html")

@app.route('/resume_template')
def resume_template():
    return render_template("resume_template.html")

@app.route('/post-job')
def post_job():
    return render_template('post_job.html')

@app.route('/create_job', methods=['GET', 'POST'])
def create_job():
    if 'loggedin' in session and session['role'] == 'recruiter':
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            location = request.form['location']
            salary = request.form['salary']
            recruiter_id = session['userid']

            cursor = mysql.connection.cursor()
            cursor.execute(
                'INSERT INTO jobs (recruiter_id, title, description, location, salary) VALUES (%s, %s, %s, %s, %s)',
                (recruiter_id, title, description, location, salary)
            )
            mysql.connection.commit()

            flash("Job posted successfully!", "success")
            return redirect(url_for('recruiter_dashboard'))  # ✅ Redirect after post
        return render_template('post_job.html')
    else:
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))




# Route to view recruiter's jobs
@app.route('/my_jobs')
def my_jobs():
    if 'loggedin' in session and session['role'] == 'recruiter':
        recruiter_id = session['userid']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM jobs WHERE recruiter_id = %s ORDER BY date_posted DESC', (recruiter_id,))
        jobs = cursor.fetchall()
        return render_template("my_jobs.html", jobs=jobs)
    else:
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

@app.route('/manage-jobs')
def manage_jobs():
    # Check if the user is logged in
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # If recruiter, show jobs they posted
        if session.get('role') == 'recruiter':
            recruiter_id = session['userid']
            cursor.execute('SELECT * FROM jobs WHERE recruiter_id = %s ORDER BY date_posted DESC', (recruiter_id,))
            jobs = cursor.fetchall()
            return render_template("manage_jobs.html", jobs=jobs, role='recruiter')

        # If user, show all job posts (or customize as needed)
        elif session.get('role') == 'user':
            cursor.execute('SELECT * FROM jobs ORDER BY date_posted DESC')
            jobs = cursor.fetchall()
            return render_template("manage_jobs.html", jobs=jobs, role='user')

        # Unknown role
        else:
            flash("Access denied: Invalid user role.", "error")
            return redirect(url_for('login'))

    else:
        # User is not logged in
        flash("Please log in to access this page.", "error")
        return redirect(url_for('login'))
    
@app.route('/apply/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    if 'loggedin' in session and session['role'] == 'user':
        user_id = session['userid']

        # Insert application record
        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO applications (user_id, job_id) VALUES (%s, %s)',
            (user_id, job_id)
        )
        mysql.connection.commit()
        flash('Successfully applied for the job!', 'success')
        return redirect(url_for('manage_jobs'))
    else:
        flash('You must be logged in as a user to apply.', 'error')
        return redirect(url_for('login'))





# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
