from flask import Flask, render_template, url_for, redirect, request, session
from authlib.integrations.flask_client import OAuth
import os
import uuid
import yaml
from flask_mysqldb import MySQL
from flask import flash, get_flashed_messages

from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = os.urandom(24)
oauth = OAuth(app)

db = yaml.safe_load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['images_folder'] = db['images_folder']
app.config['resume_folder'] = db['resume_folder']
app.config['upload_folder'] = db['resume_folder']
mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student/')
def student():
    GOOGLE_CLIENT_ID = '191059943943-0mmksrcae41bh7ok1krrgvdk7thu7nlh.apps.googleusercontent.com'
    GOOGLE_CLIENT_SECRET = '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'

    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    redirect_uri = url_for('google_auth_student', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/google/auth/student/')
def google_auth_student():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token, nonce=None)
    email = user.get('email')
    name = user.get('name', 'Unknown')


    opportunities = get_opportunities()
    session['email'] = email
    session['name'] = name
    return render_template('students/dashboard.html', email=email, name=name, opportunities=opportunities)



@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    name = session.get('name')
    opportunities = get_opportunities()
    return render_template('students/dashboard.html', email=email, name=name)


@app.route('/opportunities')
def opportunities():
    opportunities = get_opportunities()
    return render_template('students/opportunities.html', opportunities=opportunities)


def get_opportunities():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Opportunity")
    opportunities = cur.fetchall()
    # print(opportunities)
    cur.close()
    return opportunities


@app.route('/logout',methods=['GET', 'POST'])
def logout():
    # Clear the session
    session.clear()
    return render_template('index.html')


@app.route('/apply', methods=['POST'])
def apply():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM Student WHERE Student_Email_Id = %s", (email,))
    user_profile = cur.fetchone()
    cur.close()

    if not user_profile:
        # Redirect to the profile creation page if the user doesn't have a profile
        return render_template('students/create_profile.html',title='Create Profile',user_profile={},footer="Create Profile")


    opportunity_id = request.form.get('opportunity_id')
    return render_template('students/apply_form.html', opportunity_id=opportunity_id)



@app.route('/apply_opportunity', methods=['POST'])
def apply_opportunity():
    opportunity_id = request.form.get('opportunity_id')
    name = request.form.get('name')
    branch = request.form.get('branch')
    resume = request.files.get('resume')

    # Save the resume file if needed
    if resume:
        resume_filename = f"{uuid.uuid4().hex}_{resume.filename}"
        # resume.save(os.path.join('uploads', resume_filename))
        # print(f"Resume saved: {resume_filename}")

    # Display a success message
    flash("Form submitted successfully!", "success")
    email = session.get('email')
    user_name = session.get('name')
    messages = get_flashed_messages(with_categories=True)
    opportunities = get_opportunities()
    return render_template('students/dashboard.html', email=email, name=user_name, opportunities=opportunities)


@app.route('/student_profile',methods=['GET'])
def student_profile():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM Student WHERE Student_Email_Id = %s", (email,))
    user_profile = cur.fetchone()
    cur.close()

    if not user_profile:
        # Redirect to the profile creation page if the user doesn't have a profile
        return render_template('students/create_profile.html',title='Create Profile',user_profile={},footer="Create Profile")

    return render_template('students/profile.html', email=email, user_profile=user_profile)



@app.route('/create_profile', methods=['GET', 'POST'])
def create_profile():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')

    if request.method == 'POST':
        # Get form data
        firstName = request.form.get('firstName')
        middleName = request.form.get('middleName')
        lastName = request.form.get('lastName')
        department = request.form.get('department')
        gender = request.form.get('gender')
        currentYear = request.form.get('currentYear')
        minors = request.form.get('minors')
        contactNumber = request.form.get('contactNumber')
        activeBacklog = request.form.get('activeBacklog')

        # Validate email format
        if not email.endswith('@iitgn.ac.in'):
            flash("Invalid email format. Please use your @iitgn.ac.in email address.", "error")
            return render_template('students/create_profile.html')

        # Handle student image upload
        studentImage = request.files.get('studentImage')
        studentImagePath = None
        if studentImage:
            studentImageFilename = secure_filename(studentImage.filename)
            studentImagePath = os.path.join(app.config['images_folder'], studentImageFilename)

        cur = mysql.connection.cursor()

        # Check if the user already exists
        cur.execute("SELECT Student_ID FROM Student WHERE Student_Email_Id = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            # User already exists, update the profile
            student_id = existing_user[0]
            query = "UPDATE Student SET Student_First_Name = %s, Student_Middle_Name = %s, Student_Last_Name = %s, Active_Backlog = %s, Department = %s, Gender = %s, Year = %s, Student_Image = %s, Minors = %s, Contact_Number = %s WHERE Student_ID = %s"
            values = (firstName, middleName, lastName, activeBacklog, department, gender, currentYear, studentImagePath, minors, contactNumber, student_id)
            cur.execute(query, values)
            mysql.connection.commit()
            flash("Profile updated successfully!", "success")
        else:
            # New user, create a new profile
            cur.execute("SELECT MAX(Student_ID) FROM Student")
            last_student_id = cur.fetchone()[0]
            new_student_id = last_student_id + 1 if last_student_id else 1
            query = "INSERT INTO Student (Student_ID, Student_First_Name, Student_Middle_Name, Student_Last_Name, Active_Backlog, Department, Gender, Year, Student_Image, Minors, Student_Email_Id, Contact_Number) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            values = (new_student_id, firstName, middleName, lastName, activeBacklog, department, gender, currentYear, studentImagePath, minors, email, contactNumber)
            cur.execute(query, values)
            mysql.connection.commit()
            flash("Profile created successfully!", "success")

        cur.close()

        # Redirect to the dashboard after successful profile creation/update
        return redirect(url_for('dashboard'))

    # Render the profile creation/edit form
    user_profile = {}
    return render_template('students/create_profile.html', title='Create Profile', user_profile=user_profile, footer="Create Profile")

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    cur = mysql.connection.cursor()

    # Fetch the user profile data from the database
    cur.execute("SELECT * FROM Student WHERE Student_Email_Id = %s", (email,))
    user_profile = cur.fetchone()
    cur.close()
    # Render the edit profile form
    return render_template('students/create_profile.html',title='Edit Profile', user_profile=user_profile, footer="Update Profile")


# =========================================================



@app.route('/dashboard_recruiter')
def dashboard_recruiter():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    name = session.get('name')
    opportunities = get_recruiter_opportunities(email)
    return render_template('recruiter/dashboard.html', email=email, name=name)


@app.route('/recruiter_profile',methods=['GET'])
def recruiter_profile():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
    user_profile = cur.fetchone()
    cur.close()

    if not user_profile:
        # Redirect to the profile creation page if the user doesn't have a profile
        return render_template('recruiter/create_profile.html',title='Create Profile',user_profile={},footer="Create Profile")

    return render_template('recruiter/profile.html', email=email, user_profile=user_profile)



@app.route('/recruiter/')
def recruiter():
    GOOGLE_CLIENT_ID = '191059943943-0mmksrcae41bh7ok1krrgvdk7thu7nlh.apps.googleusercontent.com'
    GOOGLE_CLIENT_SECRET = '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'

    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    redirect_uri = url_for('google_auth_recruiter', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


def get_recruiter_opportunities(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Opportunity WHERE POC_Email = %s", (email,))
    opportunities = cur.fetchall()
    cur.close()
    return opportunities

@app.route('/google/auth/recruiter/')
def google_auth_recruiter():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token, nonce=None)
    email = user.get('email')
    name = user.get('name', 'Unknown')


    opportunities = get_recruiter_opportunities(email)
    print(opportunities)
    session['email'] = email
    session['name'] = name
    return render_template('recruiter/dashboard.html', email=email, name=name, opportunities=opportunities)

@app.route('/create_profile_recruiter',methods=['GET', 'POST'])
def create_profile_recruiter():
    if 'email' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        firstName = request.form['firstName']
        middleName = request.form['middleName']
        lastName = request.form['lastName']
        designation = request.form['designation']
        comapanyName = request.form['comapanyName']
        interviewer = request.form['interviewer']
        contactNumber = request.form.get('contactNumber')
        cur = mysql.connection.cursor()
        query = "INSERT INTO Person_of_Contact (Poc_Email_Id, Contact_no, Employee_First_Name, Employee_Middle_Name, Employee_Last_Name, Employee_Designation,Company_Name, Interviewer) VALUES (%s,%s, %s, %s, %s, %s, %s, %s)"
        values = (session['email'],contactNumber, firstName, middleName, lastName, designation, comapanyName, interviewer)
        cur.execute(query, values)
        mysql.connection.commit()
        cur.close()

        return render_template('recruiter/dashboard.html')
    
    return render_template('recruiter/dashboard.html')

@app.route('/create_opportunity')
def create_opportunity():
    if 'email' not in session:
        return redirect(url_for('index'))
    
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
    poc_data = cur.fetchall()
    cur.close()

    if not poc_data:
        # Redirect to the profile creation page if the user doesn't have a profile
        return render_template('recruiter/create_profile.html')

    return render_template('recruiter/host_opportunity.html',email=email)

@app.route('/save_opportunity', methods=['POST'])
def save_opportunity():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session['email']

    # Fetching form data from the request
    opp_title = request.form['Opp_Title']
    no_of_positions = request.form['No_of_Positions']
    specific_requirements_file = request.files['Specific_Requirements_file']
    min_cpi_req = request.form['Min_CPI_req']
    no_active_backlogs = request.form['No_Active_Backlogs']
    student_year_req = request.form['Student_year_req']
    program_req = request.form['Program_req']
    job_description_file = request.files['Job_Description_file']
    posted_on = request.form['Posted_on']
    deadline = request.form['Deadline']
    salary = request.form['Salary']

    cur = mysql.connection.cursor()
    cur.execute("SELECT MAX(Opp_ID) FROM Opportunity")
    opp_id = cur.fetchone()[0]
    cur.close()
    if opp_id is None:
        opp_id = 1
    else:
        opp_id = opp_id + 1   

    cur = mysql.connection.cursor()
    query = "INSERT INTO Opportunity (Opp_ID, Opp_Title, No_of_Positions, Specific_Requirements_file, Min_CPI_req, No_Active_Backlogs, Student_year_req, Program_req, Job_Description_file, Posted_on, Deadline, Salary, POC_Email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    values = (opp_id, opp_title, no_of_positions, specific_requirements_file, min_cpi_req, no_active_backlogs, student_year_req, program_req, job_description_file, posted_on, deadline, salary, email)
    cur.execute(query, values)
    mysql.connection.commit()
    cur.close()

    return render_template('recruiter/dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
