from flask import Flask, render_template, url_for, redirect, request, session
from authlib.integrations.flask_client import OAuth
import os
import uuid
import yaml
from flask_mysqldb import MySQL
from flask import flash, get_flashed_messages



app = Flask(__name__)
app.secret_key = os.urandom(24)
oauth = OAuth(app)

db = yaml.safe_load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)


@app.route('/')
def index():
    
    # print(resultValue)
    # print("hi")
    return render_template('index.html')

@app.route('/google/')
def google():
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
    redirect_uri = url_for('google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/google/auth/')
def google_auth():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token, nonce=None)
    email = user.get('email')
    # Assuming you have other user info available in the 'user' dictionary
    # You can pass any additional information you want to display on the dashboard page
    name = user.get('name', 'Unknown')
    opportunities = get_opportunities()
    session['email'] = email
    session['name'] = name
    return render_template('students/dashboard.html', email=email, name=name, opportunities=opportunities)


# @app.route('/google/auth/')
# def google_auth():
#     token = oauth.google.authorize_access_token()
#     user = oauth.google.parse_id_token(token, nonce=None)
#     email = user.get('email')
#     name = user.get('name', 'Unknown')

#     # Check if the user has a profile
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM users WHERE email = %s", (email,))
#     user_profile = cur.fetchone()
#     cur.close()

#     if not user_profile:
#         # Redirect to the profile creation page if the user doesn't have a profile
#         session['email'] = email
#         session['name'] = name
#         return redirect(url_for('create_profile'))

#     opportunities = get_opportunities()
#     session['email'] = email
#     session['name'] = name
#     return render_template('students/dashboard.html', email=email, name=name, opportunities=opportunities)


# @app.route('/dashboard')
# def dashboard():
#     if 'email' not in session:
#         return redirect(url_for('index'))

#     email = session.get('email')
#     name = session.get('name')
#     opportunities = get_opportunities()
#     return render_template('students/dashboard.html', email=email, name=name, opportunities=opportunities)

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
    return redirect(url_for('index'))


@app.route('/apply',methods=['POST'])
def apply():
    if request.method == 'POST':
        opportunity_id = request.form.get('opportunity_id')
        return render_template('students/apply_form.html', opportunity_id=opportunity_id)
    # return render_template('students/apply_form.html', opportunity_id=opportunity_id)
    else:
        return redirect(url_for('index'))
# @app.route('/apply', methods=['POST'])
# def apply():
#     if 'email' not in session:
#         return redirect(url_for('index'))

#     email = session.get('email')
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM users WHERE email = %s", (email,))
#     user_profile = cur.fetchone()
#     cur.close()

#     if not user_profile:
#         # Redirect to the profile creation page if the user doesn't have a profile
#         return redirect(url_for('create_profile'))

#     opportunity_id = request.form.get('opportunity_id')
#     return render_template('students/apply_form.html', opportunity_id=opportunity_id)



@app.route('/apply_opportunity', methods=['POST'])
def apply_opportunity():
    opportunity_id = request.form.get('opportunity_id')
    name = request.form.get('name')
    branch = request.form.get('branch')
    resume = request.files.get('resume')

    print(f"Opportunity ID: {opportunity_id}")
    print(f"Name: {name}")
    print(f"Branch: {branch}")

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



@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    if 'email' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Handle form submission and save the profile data
        name = request.form.get('name')
        branch = request.form.get('branch')
        resume = request.files.get('resume')

        # Save the profile data to the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (email, name, branch, resume_path) VALUES (%s, %s, %s, %s)",
                    (session['email'], name, branch, resume.filename))
        mysql.connection.commit()
        cur.close()

        # Save the resume file if provided
        if resume:
            resume_path = os.path.join('uploads', resume.filename)
            resume.save(resume_path)

        # Redirect to the dashboard after successful profile creation
        return redirect(url_for('dashboard'))

    # Render the profile creation form
    return render_template('students/create_profile.html')




if __name__ == '__main__':
    app.run(debug=True)
