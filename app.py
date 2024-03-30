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
    if not email.endswith('@iitgn.ac.in'):
        flash("Invalid email format. Please use your @iitgn.ac.in email address.", "error")
        return render_template('index.html')
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
    return render_template('students/apply_form.html', opportunity_id=opportunity_id, email=email,student_id = user_profile[0])



@app.route('/apply_opportunity', methods=['POST'])
def apply_opportunity():
    opportunity_id = request.form.get('opportunity_id')
    student_id = request.form.get('student_id')
    resume = request.form.get('resume')

    cur = mysql.connection.cursor()
    query = "INSERT INTO Application (Student_ID, Status,Opp_ID, Resume_File) VALUES (%s, %s, %s, %s)"
    values = (student_id,"Pending",opportunity_id, resume)
    cur.execute(query, values)
    mysql.connection.commit()
    flash("Form submitted successfully!", "success")
    email = session.get('email')
    user_name = session.get('name')
    opportunities = get_opportunities()
    return render_template('students/dashboard.html', email=email, name=user_name, opportunities=opportunities)


@app.route('/status_opp_student',methods=['GET'])
def status_opp_student():
    if 'email' not in session:
        return redirect(url_for('index'))
    email = session.get('email')
    cur = mysql.connection.cursor()
    students = cur.execute("SELECT * FROM Student WHERE Student_Email_Id = %s", (email,))
    student_id = cur.fetchone()[0]
    cur = mysql.connection.cursor()

    cur.execute("SELECT A.*, O.Opp_Title, O.Company FROM Application A JOIN Opportunity O ON A.Opp_ID = O.Opp_ID WHERE A.Student_ID = %s", (student_id,))
    applications = cur.fetchall()
    print(applications)
    cur.close()
    return render_template('students/opportunity_status.html',applications=applications)

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


        # Handle student image upload
        studentImage = request.form.get('studentImage')
        CPI = request.form.get('CPI')
        SSAC_or_not = request.form.get('SSAC_or_not') 
        # studentImagePath = None
        # if studentImage:
        #     studentImageFilename = secure_filename(studentImage.filename)
        #     studentImagePath = os.path.join(app.config['images_folder'], studentImageFilename)

        cur = mysql.connection.cursor()

        # Check if the user already exists
        cur.execute("SELECT Student_ID FROM Student WHERE Student_Email_Id = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            # User already exists, update the profile
            student_id = existing_user[0]
            query = "UPDATE Student SET Student_First_Name = %s, Student_Middle_Name = %s, Student_Last_Name = %s, Active_Backlog = %s, Department = %s, Gender = %s, Year = %s, Student_Image = %s, Minors = %s, Contact_Number = %s, CPI = %s, SSAC_or_not = %s WHERE Student_ID = %s"
            values = (firstName, middleName, lastName, activeBacklog, department, gender, currentYear, studentImage, minors, contactNumber, CPI, SSAC_or_not, student_id)
            cur.execute(query, values)
            mysql.connection.commit()
            flash("Profile updated successfully!", "success")
        else:
            # New user, create a new profile
            cur.execute("SELECT MAX(Student_ID) FROM Student")
            last_student_id = cur.fetchone()[0]
            new_student_id = last_student_id + 1 if last_student_id else 1
            query = "INSERT INTO Student (Student_ID, Student_First_Name, Student_Middle_Name, Student_Last_Name, Active_Backlog, Department, Gender, Year, Student_Image, Minors, Student_Email_Id, Contact_Number, CPI, SSAC_or_not) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            values = (new_student_id, firstName, middleName, lastName, activeBacklog, department, gender, currentYear, studentImage, minors, email, contactNumber, CPI, SSAC_or_not)
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
# Recruiter


@app.route('/edit_profile_recruiter', methods=['GET', 'POST'])
def edit_profile_recruiter():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    cur = mysql.connection.cursor()

    # Fetch the user profile data from the database
    cur.execute("SELECT * FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
    user_profile = cur.fetchone()
    cur.close()
    # Render the edit profile form
    return render_template('recruiter/create_profile.html',title='Edit Profile', user_profile=user_profile, footer="Update Profile")


@app.route('/dashboard_recruiter',methods=['GET'])
def dashboard_recruiter():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')
    name = session.get('name')
    
    return render_template('recruiter/dashboard.html', email=email, name=name)

@app.route('/created_opportunity',methods=['GET'])
def created_opportunity():
    if 'email' not in session:
        return redirect(url_for('index'))
    email = session.get('email')
    opportunities = get_recruiter_opportunities(email)
    return render_template('recruiter/opportunities.html', opportunities=opportunities)


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

@app.route('/google/auth/recruiter/')
def google_auth_recruiter():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token, nonce=None)
    email = user.get('email')
    name = user.get('name', 'Unknown')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
    user_profile = cur.fetchone()
    print(email)
    if not user_profile:
        return render_template('index.html')
    cur.close()
    opportunities = get_recruiter_opportunities(email)
    # print(opportunities)
    session['email'] = email
    session['name'] = name
    return render_template('recruiter/dashboard.html', email=email, name=name, opportunities=opportunities)


def get_recruiter_opportunities(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Opportunity WHERE POC_Email = %s", (email,))
    opportunities = cur.fetchall()
    cur.close()
    return opportunities

@app.route('/create_profile_recruiter', methods=['GET', 'POST'])
def create_profile_recruiter():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session.get('email')

    if request.method == 'POST':
        firstName = request.form.get('firstName')
        middleName = request.form.get('middleName')
        lastName = request.form.get('lastName')
        designation = request.form.get('designation')
        companyName = request.form.get('companyName')
        interviewer = request.form.get('interviewer')
        contactNumber = request.form.get('contactNumber')

        cur = mysql.connection.cursor()

        # Check if the user already exists
        cur.execute("SELECT Poc_Email_Id FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            query = "UPDATE Person_of_Contact SET Employee_First_Name = %s, Employee_Middle_Name = %s, Employee_Last_Name = %s, Employee_Designation = %s, Company_Name = %s, Interviewer = %s, Contact_no = %s WHERE Poc_Email_Id = %s"
            values = (firstName, middleName, lastName, designation, companyName, interviewer, contactNumber, email)
            cur.execute(query, values)
            mysql.connection.commit()
            flash("Profile updated successfully!", "success")
        else:
            # query = "INSERT INTO Person_of_Contact (Poc_Email_Id, Contact_no, Employee_First_Name, Employee_Middle_Name, Employee_Last_Name, Employee_Designation, Company_Name, Interviewer) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            # values = (email, contactNumber, firstName, middleName, lastName, designation, companyName, interviewer)
            # cur.execute(query, values)
            # mysql.connection.commit()
            # flash("Profile created successfully!", "success")
            return redirect(url_for('index'))

        cur.close()

        return render_template('recruiter/dashboard.html')

    return render_template('recruiter/create_profile.html', title='Create Profile', user_profile={}, footer="Create Profile")


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
        return render_template('recruiter/create_profile.html',title='Create Profile',user_profile={},footer="Create Profile")
    return render_template('recruiter/host_opportunity.html',opp_id=-1,email=email,opportunity={},rounds={},title='Create Opportunity',footer="Create Opportunity")

from flask import request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os

@app.route('/save_opportunity', methods=['POST'])
def save_opportunity():
    if 'email' not in session:
        return redirect(url_for('index'))

    email = session['email']
    opp_id = request.form['opp_id']
    opp_title = request.form['Opp_Title']
    Company = request.form['Company']
    no_of_positions = request.form['No_of_Positions']
    specific_requirements_file = request.form['Specific_Requirements_file']
    min_cpi_req = request.form['Min_CPI_req']
    no_active_backlogs = request.form['No_Active_Backlogs']
    student_year_req = request.form['Student_year_req']
    program_req = request.form['Program_req']
    job_description_file = request.form['Job_Description_file']
    salary = request.form['Salary']
    rounds = int(request.form['No_of_Rounds'])  # Number of rounds
    round_details = []  # List to store round details
    cur = mysql.connection.cursor()


    for i in range(1, rounds + 1):
        round_type = request.form[f'Round_Type{i}']
        round_date = request.form[f'Round_Date{i}']
        round_venue = request.form[f'Round_Venue{i}']
        round_start_time = request.form[f'Round_Start_Time{i}']
        round_end_time = request.form[f'Round_End_Time{i}']
        round_details.append((round_type, round_date, round_venue, round_start_time, round_end_time))

    # Check if the opportunity already exists
    # cur.execute("SELECT Opp_ID FROM Opportunity WHERE Opp_Title = %s", (opp_title,))
    # existing_opp = cur.fetchone()
    # if opp_id != -1 :
    # # print(round_details)
    # # if existing_opp:  
    # #     opp_id = existing_opp[0]
    # #     query = "UPDATE Opportunity SET Opp_Title = %s, No_of_Positions = %s, Specific_Requirements_file = %s, Min_CPI_req = %s, No_Active_Backlogs = %s, Student_year_req = %s, Program_req = %s, Job_Description_file = %s, Posted_on = %s, Deadline = %s, Salary = %s, POC_Email = %s WHERE Opp_ID = %s"
    # #     values = (opp_title, no_of_positions, specific_requirements_file, min_cpi_req, no_active_backlogs, student_year_req, program_req, job_description_file, posted_on, deadline, salary, email, opp_id)
    # # else:  # If opportunity doesn't exist, insert it


    #     query = "UPDATE INTO Opportunity (Opp_ID, Opp_Title, No_of_Positions, Specific_Requirements_file, Min_CPI_req, No_Active_Backlogs, Student_year_req, Program_req, Job_Description_file, Salary, POC_Email) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    #     values = (opp_id, opp_title, no_of_positions, specific_requirements_file, min_cpi_req, no_active_backlogs, student_year_req, program_req, job_description_file, salary, email)
    #     cur.execute(query, values)
    #     mysql.connection.commit()

    #     for i, round_detail in enumerate(round_details, start=1):
    #         round_type, round_date, round_venue, round_start_time, round_end_time = round_detail
    #         cur.execute("""
    #             INSERT INTO Round (Opp_ID, Round_ID, Type, Date, Venue, Start_Time, End_Time)
    #             VALUES (%s, %s, %s, %s, %s, %s, %s)
    #         """, (opp_id, i, round_type, round_date, round_venue, round_start_time, round_end_time))
    #         mysql.connection.commit()


    cur.execute("SELECT MAX(Opp_ID) FROM Opportunity")
    opp_id = cur.fetchone()[0]
    if opp_id is None:
        opp_id = 1
    else:
        opp_id = opp_id + 1
    query = "INSERT INTO Opportunity (Opp_ID, Opp_Title, No_of_Positions, Specific_Requirements_file, Min_CPI_req, No_Active_Backlogs, Student_year_req, Program_req, Job_Description_file, Salary, POC_Email,Company) VALUES ( %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    values = (opp_id, opp_title, no_of_positions, specific_requirements_file, min_cpi_req, no_active_backlogs, student_year_req, program_req, job_description_file, salary, email,Company)
    cur.execute(query, values)
    mysql.connection.commit()

    for i, round_detail in enumerate(round_details, start=1):
        round_type, round_date, round_venue, round_start_time, round_end_time = round_detail
        cur.execute("""
            INSERT INTO Round (Opp_ID, Round_ID, Type, Date, Venue, Start_Time, End_Time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (opp_id, i, round_type, round_date, round_venue, round_start_time, round_end_time))
        mysql.connection.commit()
    cur.close()
    return redirect(url_for('dashboard_recruiter'))


@app.route('/view_applications')
def view_applications():
    if 'email' not in session:
        return redirect(url_for('index'))
    opp_id = request.args.get('opp_id')
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT A.*, CONCAT(S.Student_First_Name, ' ', S.Student_Last_Name) AS Student_Name FROM Application A JOIN Student S ON A.Student_ID = S.Student_ID WHERE A.Opp_ID = %s", (opp_id,))
    applications = cur.fetchall()

    return render_template('recruiter/view_applications.html', applications=applications)

@app.route('/update_status/', methods=['GET','POST'])
def update_status():
    if 'email' not in session:
        return redirect(url_for('index'))
    

    student_id = request.args.get('student_id')
    opp_id = request.args.get('opp_id')
    status = request.form.get('status')
    cur = mysql.connection.cursor()
    print(opp_id)
    print(student_id)
    cur.execute("UPDATE Application SET Status = %s WHERE Student_ID = %s AND Opp_ID = %s", (status, student_id, opp_id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('dashboard_recruiter'))


# Test this also 
# @app.route('/update_status/<int:student_id>/<int:opp_id>', methods=['POST'])
# def update_status(student_id, opp_id):
#     if 'email' not in session:
#         return redirect(url_for('index'))
    
#     status = request.form['status']
    
#     cur = mysql.connection.cursor()
#     cur.execute("UPDATE Application SET Status = %s WHERE Student_ID = %s AND Opp_ID = %s", (status, student_id, opp_id))
#     mysql.connection.commit()
#     cur.close()
    
#     return redirect(url_for('view_applications'))



# ========================================

# CDS 

@app.route('/cds/')
def cds():
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
    redirect_uri = url_for('google_auth_cds', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/google/auth/cds/')
def google_auth_cds():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token, nonce=None)
    email = user.get('email')
    name = user.get('name', 'Unknown')

    # opportunities = get_recruiter_opportunities(email)
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM CDS_USER WHERE Email = %s", (email,))
    user_profile = cur.fetchone()
    if not user_profile:
        return render_template('index.html')
    cur.close()
    session['email'] = email
    session['name'] = name
    return render_template('cds/dashboard.html', email=email, name=name, opportunities=opportunities)


@app.route('/add_poc')
def add_poc():
    if 'email' not in session:
        return redirect(url_for('index'))
    return render_template('cds/add_poc.html',title='Create Profile',user_profile={},footer="Add Profile")


@app.route('/create_profile_poc',methods=['GET', 'POST'])
def create_profile_poc():
    if 'email' not in session:
        return redirect(url_for('index'))


    if request.method == 'POST':
        firstName = request.form.get('firstName')
        middleName = request.form.get('middleName')
        lastName = request.form.get('lastName')
        designation = request.form.get('designation')
        companyName = request.form.get('companyName')
        interviewer = request.form.get('interviewer')
        contactNumber = request.form.get('contactNumber')
        emailPOC = request.form.get('Email')
        cur = mysql.connection.cursor()

        # Check if the user already exists
        cur.execute("SELECT Poc_Email_Id FROM Person_of_Contact WHERE Poc_Email_Id = %s", (emailPOC,))
        existing_user = cur.fetchone()

        if existing_user:
            query = "UPDATE Person_of_Contact SET Employee_First_Name = %s, Employee_Middle_Name = %s, Employee_Last_Name = %s, Employee_Designation = %s, Company_Name = %s, Interviewer = %s, Contact_no = %s WHERE Poc_Email_Id = %s"
            values = (firstName, middleName, lastName, designation, companyName, interviewer, contactNumber, emailPOC)
            cur.execute(query, values)
            mysql.connection.commit()
            flash("Profile updated successfully!", "success")
        else:
            query = "INSERT INTO Person_of_Contact (Poc_Email_Id, Contact_no, Employee_First_Name, Employee_Middle_Name, Employee_Last_Name, Employee_Designation, Company_Name, Interviewer) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            values = (emailPOC, contactNumber, firstName, middleName, lastName, designation, companyName, interviewer)
            cur.execute(query, values)
            mysql.connection.commit()
            flash("Profile created successfully!", "success")

        cur.close()

        return render_template('cds/dashboard.html')

    return render_template('cds/add_poc.html', title='Create Profile', user_profile={}, footer="Create Profile")


# ================================================
# Delete opportuinity -- Recuriter -- Opportunites.html
@app.route('/delete_opportunity/<int:opp_id>', methods=['GET', 'POST'])
def delete_opportunity(opp_id):
    if 'email' not in session:
        return redirect(url_for('index'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Opportunity WHERE Opp_ID = %s", (opp_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('created_opportunity'))


# ================================================
# Edit opportuinity -- Recuriter -- Opportunites.html
@app.route('/edit_opportunity/<int:opp_id>', methods=['GET', 'POST'])
def edit_opportunity(opp_id):
    if 'email' not in session:
        return redirect(url_for('index'))
    
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
    poc_data = cur.fetchall()
    cur.execute("SELECT * FROM Opportunity WHERE Opp_ID = %s", (opp_id,))
    opportunity = cur.fetchone()

    cur.execute("SELECT * FROM Round WHERE Opp_ID = %s", (opp_id,))
    rounds = cur.fetchall()
    print(rounds)
    cur.close()
    if not poc_data:
        return render_template('recruiter/create_profile.html',title='Create Profile',user_profile={},footer="Create Profile")
    return render_template('recruiter/host_opportunity.html',opp_id=opp_id,email=email,opportunity=opportunity,rounds=rounds,title='Edit Opportunity',footer="Update Opportunity")




# import datetime
# @app.route('/edit_opportunity/<int:opp_id>', methods=['GET', 'POST'])
# def edit_opportunity(opp_id):
#     if 'email' not in session:
#         return redirect(url_for('index'))
#     email = session['email']
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM Person_of_Contact WHERE Poc_Email_Id = %s", (email,))
#     poc_data = cur.fetchall()
#     cur.execute("SELECT * FROM Opportunity WHERE Opp_ID = %s", (opp_id,))
#     opportunity = cur.fetchone()
#     cur.execute("SELECT * FROM Round WHERE Opp_ID = %s", (opp_id,))
#     rounds = cur.fetchall()
#     print(rounds)
#     cur.close()

#     # Convert rounds to a list of dictionaries
#     round_details = []
#     for round_data in rounds:
#         start_time = (datetime.min + round_data[5]).time()  # Convert timedelta to time object
#         end_time = (datetime.min + round_data[6]).time()  # Convert timedelta to time object
#         round_details.append({
#             'roundType': round_data[2],
#             'roundDate': round_data[3].strftime('%Y-%m-%d'),  # Convert date to string in the desired format
#             'roundVenue': round_data[4],
#             'roundStartTime': round_data[5].strftime('%H:%M'),  # Convert time to string in the desired format
#             'roundEndTime': round_data[6].strftime('%H:%M')  # Convert time to string in the desired format
#         })

#     if not poc_data:
#         return render_template('recruiter/create_profile.html', title='Create Profile', user_profile={}, footer="Create Profile")
#     return render_template('recruiter/host_opportunity.html', opp_id=opp_id, email=email, opportunity=opportunity, rounds=round_details, title='Edit Opportunity', footer="Update Opportunity")



# =============================================================
#  OPPORTUNITY DETAILS

@app.route('/opportunity_details/<int:opp_id>')
def opportunity_details(opp_id):
    if 'email' not in session:
        return redirect(url_for('index'))
    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Opportunity WHERE Opp_ID = %s", (opp_id,))
    opportunity = cur.fetchone()
    cur.execute("SELECT * FROM Round WHERE Opp_ID = %s", (opp_id,))
    rounds = cur.fetchall()
    return render_template('recruiter/opportunity_details.html', opportunity=opportunity, rounds=rounds)

# =============================================================

@app.route('/student_Details')
def student_Details():
    details = get_student_Details()
    return render_template('cds/student_details.html', details=details)

def get_student_Details():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Student")
    details = cur.fetchall()
    #print(details)
    cur.close()
    return details

@app.route('/view_details/<string:student_email>')
def view_details(student_email):
    user_profile = get_Details(student_email)
    return render_template('cds/view_details.html', user_profile=user_profile)

def get_Details(student_email):

    cur = mysql.connection.cursor()

    # Fetch the user profile data from the database
    cur.execute("SELECT * FROM Student WHERE Student_Email_Id = %s", (student_email,))
    user_profile = cur.fetchone()
    cur.close()
    return user_profile

@app.route('/go_back')
def go_back():
    return render_template('cds/dashboard.html')

@app.route('/see_opportunities')
def see_opportunities():
    opportunities = see_opportunities()
    return render_template('cds/opportunities.html', opportunities=opportunities)


def see_opportunities():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Opportunity")
    opportunities = cur.fetchall()
    # print(opportunities)
    cur.close()
    return opportunities


if __name__ == '__main__':
    app.run(debug=True)
