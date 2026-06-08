from flask import Flask, render_template, redirect, session, request,url_for, flash, abort, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_manager,  login_user, login_required, current_user, UserMixin, logout_user
from dotenv import load_dotenv
import os, json
from datetime import date, datetime
import qrcode
import io
import base64
import cv2
import pandas as pd
import numpy as np
import re
from zoneinfo import ZoneInfo

load_dotenv()

# Fetch the exact time specifically for India
local_time = datetime.now(ZoneInfo("Asia/Kolkata"))

app  = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pro_secret_key_99')

raw_db_url = os.getenv('DATABASE_URL')
use_tmp_sqlite = os.getenv('VERCEL') == '1'
if raw_db_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url.replace("postgres://", "postgresql://", 1)
elif use_tmp_sqlite:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/database.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'home'


#Migrate Procedure
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Stack Holder Details 

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    register = db.Column(db.String(12), unique=True, nullable=False)
    dob = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100))
    year = db.Column(db.String(2)) 
    college = db.Column(db.String(100))
    room_no = db.Column(db.String(5))

    # Changed from Integer to String(15) to protect leading zeros 
    # and avoid mathematical overflow errors
    student_no = db.Column(db.String(10))
    father_no = db.Column(db.String(10))
    mother_no = db.Column(db.String(10))
    guardient_no = db.Column(db.String(10))

    def __repr__(self):
        return f'<Student {self.register}>'
    
class Warden(UserMixin, db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    username =  db.Column(db.String(50),unique=True)
    password = db.Column(db.String(50))
    name = db.Column(db.String(50))

class Security(UserMixin, db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    username =  db.Column(db.String(50),unique=True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(50)) 
    
class Staff(UserMixin, db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    username =  db.Column(db.String(50),unique=True)
    name = db.Column(db.String(50))
    department = db.Column(db.String(50)) #AI&DS, IT, CSE, ECE, AI&ML, EEE, MECH, CY 
    password = db.Column(db.String(50)) 

class HOD(UserMixin, db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    username =  db.Column(db.String(50),unique=True)
    name = db.Column(db.String(50))
    department = db.Column(db.String(50)) #AI&DS, IT, CSE, ECE, AI&ML, EEE, MECH, CY 
    password = db.Column(db.String(50)) 

class Admin(UserMixin, db.Model) :
    id = db.Column(db.Integer,primary_key=True)
    username =  db.Column(db.String(50),unique=True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(50)) 

#Letter Processing
class Letter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Student Info (Snapshot at time of request)
    student_name = db.Column(db.String(50))
    student_department = db.Column(db.String(60))
    student_year = db.Column(db.String(10))
    student_college = db.Column(db.String(100))
    
    # Request Details
    category = db.Column(db.String(50))  # e.g., 'Staff, HOD, Warden'
    nameSelection = db.Column(db.String(50))
    letter_content = db.Column(db.Text)   # The main body text
    request_category = db.Column(db.String(50))
    request_date = db.Column(db.String(20)) # The date string from the form
    
    # Parent/Guardian Details
    parent_name = db.Column(db.String(100))
    parent_no = db.Column(db.Integer)
    parent_start_time = db.Column(db.DateTime)
    parent_end_time = db.Column(db.DateTime)
    
    # Status & Routing
    status = db.Column(db.String(20), default='Progress') # Pending, Approved, Rejected
    # warden_name = db.Column(db.String(50)) # The ID of the warden selected in the form
    
    # Relationship Link
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Letter {self.id} from {self.student_name}>'
    

#Detailed Pass
class DetailedPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    letter_id = db.Column(db.String(50))
    student_name = db.Column(db.String(150))
    dept = db.Column(db.String(100))
    year = db.Column(db.String(20))
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    # Flask-Login sessions store IDs as strings, so we convert to int
    uid = int(user_id)
    
    user = User.query.get(uid)
    if user:
        return user
    
    student = Student.query.get(uid)
    if student:
        return student
    
    warden = Warden.query.get(uid)
    if warden :
        return warden
    
    staff = Staff.query.get(uid)
    if staff :
        return staff
    
    hod = HOD.query.get(uid)
    if hod :
        return hod
        
    admin = Admin.query.get(uid)
    if admin :
        return admin
        
    return None
    
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='user').first():
        db.session.add(User(username='user', password='user123'))
        db.session.commit()
    # Added .first() to actually fetch a record or None
    if not Student.query.filter_by(register='410123243006').first():
        db.session.add(Student(
            register='410123243006', 
            dob="2006-01-19", 
            name='Bharath',
            department="AI&DS",
            year='4',
            college='ACET',
            room_no='AD214',
            student_no='7418771913',
            father_no='9364290146',
            mother_no='9092051423',
            guardient_no='9710210537'
        ))
        db.session.commit()
    if not Warden.query.filter_by(username='suresh').first() :
        db.session.add(Warden(username='suresh', password='suresh123',name='Mr.Suresh'))
        db.session.commit()
    if not Security.query.filter_by(username='security').first() :
        db.session.add(Security(username='security', password='security123',name='SecurityName'))
        db.session.commit()
    if not Staff.query.filter_by(username='asha').first() :
        db.session.add(Staff(username='asha', password='asha123',name='Ms.Asha Marry',department='AI&DS'))
        db.session.commit()
    if not HOD.query.filter_by(username='hod_aids').first() :
        db.session.add(HOD(username='hod_aids', password='aids',name='Dr. V.BELMER GLADSON',department='AI&DS'))
        db.session.commit()
    if not Admin.query.filter_by(username='Adhi').first() :
        db.session.add(Admin(username='Adhi', password='Adhi123',name='Adhi Admin'))
        db.session.commit()
        
@app.route('/')
def home() :
    logout_user()
    return render_template('welcome.html')


# Student Manage

@app.route('/student_login',methods=['POST','GET'])
def student_login() :
    if request.method == 'POST' :
        student = Student.query.filter_by(register=request.form.get('register')).first()
        if student and student.dob == request.form.get('dob') :
            login_user(student)
            return redirect(url_for('student_page',id=student.id))
    return render_template('student_login.html')


@app.route('/student_page/<int:id>')
@login_required
def student_page(id) :
    if current_user.id != id:
        return render_template('error_page.html')
    student = Student.query.get_or_404(id)
    # Fetch letters to display on the dashboard
    letters = Letter.query.filter_by(student_id=id).order_by(Letter.id.desc()).all()
    return render_template('student_page.html', student=student,letters=letters)

@app.route('/student_profile/<int:student_id>')
def student_profile(student_id) :
    student = Student.query.get_or_404(student_id)
    return render_template('student_profile.html',student=student)

@app.route('/add_student',methods=['GET','POST'])
def add_student() :
    if request.method == 'POST':
        # Account & Personal Info
        register = request.form.get('register')
        dob = request.form.get('dob')
        name = request.form.get('name')
        
        # Academic & Location Info
        department = request.form.get('department')
        year = request.form.get('year')
        college = request.form.get('college')
        room_no = request.form.get('room_no')
        
        # Contact Numbers (Converted to integers where necessary)
        # Using .get() ensures it doesn't crash if a field is empty
        student_no = request.form.get('student_no')
        father_no = request.form.get('father_no')
        mother_no = request.form.get('mother_no')
        guardient_no = request.form.get('guardient_no')

        # Create the new student object with all fields
        new_student = Student(
            register=register, 
            dob=dob, 
            name=name,
            department=department,
            year=year,
            college=college,
            room_no=room_no,
            student_no=student_no,
            father_no=father_no,
            mother_no=mother_no,
            guardient_no=guardient_no
        )

        # Add to database and commit
        try:
            db.session.add(new_student)
            db.session.commit()
            return redirect(url_for('home'))
            # Redirect or flash success message here
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            # Handle error (e.g., duplicate username)
    return render_template('add_student.html')

@app.route('/students', methods=['GET'])
def view_students():
    # Fetch all students out of your model database
    students = Student.query.order_by(Student.register.asc()).all()
    return render_template('students.html', students=students)

@app.route('/student/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    if request.method == 'POST':
        # Modify the object record structural parameters 
        student.register = request.form.get('register')
        student.name = request.form.get('name')
        student.dob = request.form.get('dob')
        student.department = request.form.get('department')
        student.year = request.form.get('year')
        student.college = request.form.get('college')
        student.room_no = request.form.get('room_no')
        student.student_no = request.form.get('student_no')
        student.father_no = request.form.get('father_no')
        student.mother_no = request.form.get('mother_no')
        student.guardient_no = request.form.get('guardient_no')
        
        db.session.commit()
        flash('Student file data modified successfully.')
        return redirect(url_for('view_students'))
        
    return render_template('edit_student.html', student=student)

@app.route('/student/delete/<int:id>', methods=['GET','POST'])
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('view_students'))
    

@app.route('/request_letter/<int:student_id>',methods=['GET','POST'])
@login_required
def request_letter(student_id) :
    student = Student.query.get_or_404(student_id)
    warden =  Warden.query.all()
    # Query all names and organize into a dictionary
    # This matches the 'value' attributes in your HTML <select>
    db_data = {
        "warden": [w.name for w in Warden.query.all()],
        "staff": [st.name for st in Staff.query.all()],
        "HOD" : [h.name for h in HOD.query.all()]
    }
    today_date = date.today().strftime('%Y-%m-%d')
    return render_template('request_letter.html',data=db_data, student=student,warden=warden,today=today_date)

#Security
@app.route('/security_login',methods=['GET','POST'])
def security() :
    if request.method == 'POST' :
        security = Security.query.filter_by(username=request.form.get('username')).first()
        if security and security.password == request.form.get('password') :
            login_user(security)
            return redirect(url_for('security_page',id=security.id))
    return render_template('security_login.html')


@app.route('/security_page/<int:id>', methods=['GET', 'POST'])
@login_required
def security_page(id):
    if current_user.id != id:
        return render_template('error_page.html')
    security = Security.query.get_or_404(id)
    records = DetailedPass.query.order_by(DetailedPass.scanned_at.desc()).all()
    return render_template('security_page.html', security=security, records=records)

def get_val(pattern, text):
    """Extracts values based on your specific QR format labels."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"

@app.route('/open_scanner')
def open_scanner():
    records = DetailedPass.query.order_by(DetailedPass.scanned_at.desc()).all()
    return render_template('scanner.html', records=records)

@app.route('/verify_id', methods=['POST'])
def verify_id():
    letter_id = request.form.get('letter_id')
    
    # 1. Check if the ID was actually provided
    if not letter_id:
        flash("Please enter a Letter ID to verify.", "warning")
        return redirect(url_for('open_scanner'))
        
    # 2. Query the database for the letter
    letter = Letter.query.filter_by(id=letter_id).first()
    
    # 3. Check if the letter exists and if it is 'Approved'
    if not letter or letter.status != 'Approved':
        # If it exists but is already complete, give a specific message
        if letter and letter.status == 'Complete':
            flash(f"Already Scanned Completed {letter.id}", "warning")
        else:
            flash("Invalid Letter ID or not approved.", "error")
        return redirect(url_for('open_scanner'))
    
    # 4. Process the valid, approved letter
    letter.status = 'Complete'
    
    # 5. Create the new DetailedPass record
    new_record = DetailedPass(
        letter_id=letter.id,
        student_name=letter.student_name,
        dept=letter.student_department,
        year=letter.student_year,
        scanned_at=datetime.utcnow()  # Note: Use timezone-aware dates if possible in your app
    )
    
    # 6. Commit both changes to the database in one transaction
    try:
        db.session.add(new_record)
        db.session.commit()
        flash(f"Gate pass for {letter.student_name} verified successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while saving the data.", "error")
        # Optional: log the error `e` here
        
    return redirect(url_for('open_scanner'))

@app.route('/save_scan', methods=['POST'])
def save_scan():
    data = request.get_json()
    raw_text = data.get('qr_text', '')

    if not raw_text:
        return jsonify({"status": "error", "message": "No data received"}), 400

    try:
        # 1. Parse the JSON from the QR code
        q = json.loads(raw_text)
        
        # 2. Map JSON keys to your DetailedPass Database Columns
        new_record = DetailedPass(
            letter_id      = str(q.get("ID", "")),
            student_name   = q.get("Student Name", "Unknown"),
            dept           = q.get("Department", ""),
            year           = str(q.get("Year", "")),
            scanned_at     = datetime.utcnow() # Records exactly when security scanned it
        )

        db.session.add(new_record)
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": f"Pass verified for {new_record.student_name}"
        }), 200

    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Invalid QR Format. Please use the updated Gate Pass."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# Warden Manage
@app.route('/warden_login',methods=['POST','GET'])
def warden_login() :
    if request.method == 'POST' :
        warden = Warden.query.filter_by(username=request.form.get('username')).first()
        if warden and warden.password == request.form.get('password') :
            login_user(warden)
            return redirect(url_for('warden_page',id=warden.id))
    return render_template('warden_login.html')


@app.route('/warden_page/<int:id>', methods=['GET', 'POST'])
@login_required
def warden_page(id):
    if current_user.id != id:
        return render_template('error_page.html')
    warden = Warden.query.get_or_404(id)
    letters = Letter.query.filter_by(nameSelection=warden.name).all()
    
    return render_template('warden_page.html', warden=warden, letters=letters)


@app.route('/add_warden',methods=['GET','POST'])
def add_warden() :
    if request.method == 'POST' :
        new_warden = Warden(
            username = request.form.get('username'),
            password = request.form.get('password'),
            name = request.form.get('name')
        )
        db.session.add(new_warden)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_warden.html')


#Approve Letter
@app.route('/staff_approval_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def staff_approval_letter(id):
    letter = Letter.query.get_or_404(id)
    try:
        # Update the status
        letter.status = 'Pending HOD'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been approved.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('staff_page', id=current_user.id))

@app.route('/hod_approval_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def hod_approval_letter(id):
    letter = Letter.query.get_or_404(id)
    warden = Warden.query.all()
    try:
        # Update the status
        if request.form.get('nameSelection') :
            letter.nameSelection = request.form.get('nameSelection')
            letter.status = 'Pending Warden'
            db.session.commit()
        
        
        flash(f"Letter from {letter.student_name} has been approved.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('hod_page', id=current_user.id,warden=warden))

@app.route('/warden_approval_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def warden_approval_letter(id):
    letter = Letter.query.get_or_404(id)
    try:
        # Update the status
        letter.status = 'Approved'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been approved.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('warden_page', id=current_user.id))


@app.route('/approval_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def approval_letter(id):
    letter = Letter.query.get_or_404(id)
    try:
        # Update the status
        letter.status = 'Approved'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been approved.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('warden_page', id=current_user.id))

@app.route('/warden_page/approval_letters/<int:id>',methods=['GET','POST'])    
def warden_approval_letter_list(id) :
    warden = Warden.query.get_or_404(id)
    letters = Letter.query.all()
    return render_template('approved_letters.html',warden=warden,letters=letters)




#Reject Letter
@app.route('/reject_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def reject_letter(id):
    letter = Letter.query.get_or_404(id)

    try:
        # Update the status
        letter.status = 'Rejected'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been rejected.", "warning")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('warden_page', id=current_user.id))

@app.route('/staff_reject_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def staff_reject_letter(id):
    letter = Letter.query.get_or_404(id)
    try:
        # Update the status
        letter.status = 'Rejected Staff'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been rejected.", "warning")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('staff_page', id=current_user.id))


@app.route('/hod_reject_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def hod_reject_letter(id):
    letter = Letter.query.get_or_404(id)
    try:
        # Update the status
        letter.status = 'Rejected HOD'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been rejected.", "warning")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('hod_page', id=current_user.id))

@app.route('/warden_reject_letter/<int:id>', methods=['POST', 'GET'])
@login_required
def warden_reject_letter(id):
    letter = Letter.query.get_or_404(id)
    try:
        # Update the status
        letter.status = 'Rejected Warden'
        db.session.commit()
        
        flash(f"Letter from {letter.student_name} has been rejected.", "warning")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the status.", "danger")

    # Redirect back to the warden's dashboard
    return redirect(url_for('warden_page', id=current_user.id))


@app.route('/warden_page/rejected_letters/<int:id>',methods=['GET','POST'])    
def warden_rejected_letter(id) :
    warden = Warden.query.get_or_404(id)
    letters = Letter.query.all()
    return render_template('rejected_letters.html',warden=warden,letters=letters)

    
#Letter Submit
@app.route('/submit_request', methods=['POST'])
def submit_request():
    if request.method == 'POST':
        # Convert HTML datetime-local strings to Python datetime objects
        start_str = request.form.get('parent_start_time')
        end_str = request.form.get('parent_end_time')
        
        # Formatting the time (HTML returns YYYY-MM-DDTHH:MM)
        start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M') if start_str else None
        end_dt = datetime.strptime(end_str, '%Y-%m-%dT%H:%M') if end_str else None
        # 1. First, determine the approval statuses based on the category
        category = request.form.get('category')
        if category == 'staff':
            status = 'Pending Staff'
        elif category == 'HOD':
            status = 'Pending HOD'
        else:
            status = 'Pending Warden'
        # 2. Now, safely instantiate the Letter object
        new_letter = Letter(
            student_name=request.form.get('student_name'),
            student_department=request.form.get('department'),
            student_year=request.form.get('year'),
            student_college=request.form.get('college'),
            category=category,
            nameSelection=request.form.get('nameSelection'),
            letter_content=request.form.get('letter_content'),
            request_date=request.form.get('request_date'),
            parent_name=request.form.get('parent_name'),
            parent_no=request.form.get('parent_no'),
            parent_start_time=start_dt,
            parent_end_time=end_dt,
            request_category=request.form.get('request_category'),
            status=status,
            student_id=current_user.id  # Link to the logged-in student
        )

        db.session.add(new_letter)
        db.session.commit()
        flash("Letter submitted to the warden successfully!", "success")
        return redirect(url_for('student_page',id=current_user.id))
@app.route('/qr_code/<int:letter_id>', methods=['GET'])
def qr_code(letter_id):
    # 1. Get the letter data
    letter = Letter.query.get_or_404(letter_id)
    
    # CRITICAL FIX: Encode just the raw string ID instead of complex JSON
    qr_data = str(letter.id) 

    # 3. Generate QR Image with High Error Correction
    qr = qrcode.QRCode(
        version=None, 
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # 4. Save to memory buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    # 5. Convert to string for HTML
    qr_base64 = base64.b64encode(buf.getvalue()).decode('ascii')
    
    return render_template('qr_code.html', qr_code=qr_base64, letter=letter)

# Logout Process
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
    
#Staff Page
@app.route('/staff_login',methods=['GET','POST'])
def staff_login() :
    if request.method == 'POST':
        staff = Staff.query.filter_by(username=request.form.get('username')).first()
        if staff and staff.password == request.form.get('password'):
            login_user(staff)
            return redirect(url_for('staff_page',id=staff.id))
    return render_template('staff_login.html')

@app.route('/staff_page/<int:id>',methods=['GET','POST'])
@login_required
def staff_page(id) :
    if current_user.id != id:
        return render_template('error_page.html')
    staff = Staff.query.get_or_404(id)
    letters = Letter.query.filter_by(nameSelection=staff.name).all()
    return render_template('staff_page.html',staff=staff,letters=letters)



#HOD Page
@app.route('/hod_login',methods=['GET','POST'])
def hod_login() :
    if request.method == 'POST':
        hod = HOD.query.filter_by(username=request.form.get('username')).first()
        if hod and hod.password == request.form.get('password'):
            login_user(hod)     
            return redirect(url_for('hod_page',id=hod.id))
    return render_template('hod_login.html')

@app.route('/hod_page/<int:id>',methods=['GET','POST'])
@login_required
def hod_page(id) :
    if current_user.id != id:
        return render_template('error_page.html')
    hod = HOD.query.get_or_404(id)
    letters = Letter.query.filter_by(student_department=hod.department).all()
    warden = Warden.query.all()
    return render_template('hod_page.html',hod=hod,letters=letters,warden=warden)


#Admin Page
@app.route('/admin_login',methods=['GET','POST'])
def admin_login() :
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form.get('username')).first()
        if admin and admin.password == request.form.get('password'):
            login_user(admin)
            return redirect(url_for('admin_page', id=admin.id))
    return render_template('admin_login.html')

@app.route('/admin_page/<int:id>',methods=['GET','POST'])
@login_required
def admin_page(id) :
    if current_user.id != id:
        return render_template('error_page.html')
    admin = Admin.query.get_or_404(id)
    return render_template('admin_page.html', admin=admin)

# ==============================
# Bulk Upload Route
# ==============================
# --- Helper for File Validation ---
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Route for File Upload & Processing ---
@app.route('/upload_students', methods=['GET', 'POST'])
def upload_students():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected. Please choose a file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            try:
                # Force specific columns to be read as strings to preserve leading zeros
                string_columns = ['register', 'year', 'room_no', 'student_no', 'father_no', 'mother_no', 'guardient_no']
                converters = {col: str for col in string_columns}
                
                # Parse based on file type using pandas
                if file_ext == 'csv':
                    df = pd.read_csv(file, converters=converters)
                else:
                    df = pd.read_excel(file, converters=converters)
                
                df.columns = df.columns.str.strip()
                df = df.where(pd.notnull(df), None)
                
                students_to_add = []
                duplicate_errors = []
                
                for index, row in df.iterrows():
                    register_val = str(row.get('register', '')).strip() if row.get('register') else None
                    name_val = str(row.get('name', '')).strip() if row.get('name') else None
                    dob_val = str(row.get('dob')).strip().split(' ')[0] if row.get('dob') else None
                    
                    if not register_val or not name_val or not dob_val:
                        continue
                        
                    existing = Student.query.filter_by(register=register_val).first()
                    if existing:
                        duplicate_errors.append(f"Row {index + 2}: Register '{register_val}' already exists. Skipped.")
                        continue
                    
                    student = Student(
                        register=register_val,
                        dob=dob_val,
                        name=name_val,
                        department=row.get('department'),
                        year=row.get('year'),
                        college=row.get('college'),
                        room_no=row.get('room_no'),
                        student_no=row.get('student_no'),
                        father_no=row.get('father_no'),
                        mother_no=row.get('mother_no'),
                        guardient_no=row.get('guardient_no')
                    )
                    students_to_add.append(student)
                
                if students_to_add:
                    db.session.bulk_save_objects(students_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(students_to_add)} new student records!', 'success')
                
                if duplicate_errors:
                    for err in duplicate_errors:
                        flash(err, 'warning')
                 
                return redirect(url_for('admin_page', id=current_user.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error parsing file: {str(e)}", 'danger')
                return redirect(request.url)
                
        else:
            flash('Invalid format! Please use a valid .csv, .xlsx, or .xls file.', 'danger')
            return redirect(request.url)
            
    return render_template('student_bulk_import.html')


# --- Route for HOD File Upload & Processing ---
@app.route('/upload_hod', methods=['GET', 'POST'])
def upload_hod():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected. Please choose a file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            try:
                # Force username and password to string to keep format intact (e.g. leading zeros)
                string_columns = ['username', 'password']
                converters = {col: str for col in string_columns}
                
                # Parse file
                if file_ext == 'csv':
                    df = pd.read_csv(file, converters=converters)
                else:
                    df = pd.read_excel(file, converters=converters)
                
                # Clean up whitespaces from headers
                df.columns = df.columns.str.strip()
                df = df.where(pd.notnull(df), None)
                
                hods_to_add = []
                duplicate_errors = []
                
                # Iterate rows
                for index, row in df.iterrows():
                    username_val = str(row.get('username', '')).strip() if row.get('username') else None
                    name_val = str(row.get('name', '')).strip() if row.get('name') else None
                    dept_val = str(row.get('department', '')).strip() if row.get('department') else None
                    password_val = str(row.get('password', '')).strip() if row.get('password') else None
                    
                    # Validate required fields
                    if not username_val or not name_val or not password_val:
                        continue # Skip empty or invalid rows
                        
                    # Check for existing username duplicates
                    existing = HOD.query.filter_by(username=username_val).first()
                    if existing:
                        duplicate_errors.append(f"Row {index + 2}: Username '{username_val}' already exists. Skipped.")
                        continue
                    
                    hod = HOD(
                        username=username_val,
                        name=name_val,
                        department=dept_val,
                        password=password_val # Note: Consider using generate_password_hash in real production environments
                    )
                    hods_to_add.append(hod)
                
                # Bulk Database Save
                if hods_to_add:
                    db.session.bulk_save_objects(hods_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(hods_to_add)} HOD records!', 'success')
                
                if duplicate_errors:
                    for err in duplicate_errors:
                        flash(err, 'warning')
                        
                return redirect(url_for('admin_page', id=current_user.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error parsing file: {str(e)}", 'danger')
                return redirect(request.url)
                
        else:
            flash('Invalid format! Please use a valid .csv, .xlsx, or .xls file.', 'danger')
            return redirect(request.url)
            
    return render_template('hod_bulk_import.html')

# --- Route for Staff File Upload & Processing ---
@app.route('/upload_staff', methods=['GET', 'POST'])
def upload_staff():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected. Please choose a file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            try:
                # Force specific columns to be read as strings to preserve formatting
                string_columns = ['username', 'password']
                converters = {col: str for col in string_columns}
                
                # Parse based on file type
                if file_ext == 'csv':
                    df = pd.read_csv(file, converters=converters)
                else:
                    df = pd.read_excel(file, converters=converters)
                
                # Clean header spacing
                df.columns = df.columns.str.strip()
                df = df.where(pd.notnull(df), None)
                
                staff_to_add = []
                duplicate_errors = []
                
                # Iterate rows and extract data
                for index, row in df.iterrows():
                    username_val = str(row.get('username', '')).strip() if row.get('username') else None
                    name_val = str(row.get('name', '')).strip() if row.get('name') else None
                    dept_val = str(row.get('department', '')).strip() if row.get('department') else None
                    password_val = str(row.get('password', '')).strip() if row.get('password') else None
                    
                    # Validate required constraints
                    if not username_val or not name_val or not password_val:
                        continue # Skip bad/empty rows
                        
                    # Check for unique username constraint violation
                    existing = Staff.query.filter_by(username=username_val).first()
                    if existing:
                        duplicate_errors.append(f"Row {index + 2}: Username '{username_val}' already exists. Skipped.")
                        continue
                    
                    staff = Staff(
                        username=username_val,
                        name=name_val,
                        department=dept_val,
                        password=password_val
                    )
                    staff_to_add.append(staff)
                
                # Commit valid rows dynamically
                if staff_to_add:
                    db.session.bulk_save_objects(staff_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(staff_to_add)} Staff records!', 'success')
                
                if duplicate_errors:
                    for err in duplicate_errors:
                        flash(err, 'warning')
                        
                return redirect(url_for('admin_page', id=current_user.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error parsing file: {str(e)}", 'danger')
                return redirect(request.url)
                
        else:
            flash('Invalid format! Please use a valid .csv, .xlsx, or .xls file.', 'danger')
            return redirect(request.url)
            
    return render_template('staff_bulk_import.html')

# --- Route for Warden File Upload & Processing ---
@app.route('/upload_warden', methods=['GET', 'POST'])
def upload_warden():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected. Please choose a file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            try:
                # Force username and password columns to remain as string datatypes
                string_columns = ['username', 'password']
                converters = {col: str for col in string_columns}
                
                # Parse depending on layout format
                if file_ext == 'csv':
                    df = pd.read_csv(file, converters=converters)
                else:
                    df = pd.read_excel(file, converters=converters)
                
                # Clean up accidental whitespace padding from headers
                df.columns = df.columns.str.strip()
                df = df.where(pd.notnull(df), None)
                
                wardens_to_add = []
                duplicate_errors = []
                
                # Loop through sheet rows
                for index, row in df.iterrows():
                    username_val = str(row.get('username', '')).strip() if row.get('username') else None
                    name_val = str(row.get('name', '')).strip() if row.get('name') else None
                    password_val = str(row.get('password', '')).strip() if row.get('password') else None
                    
                    # Validate that required elements are not missing
                    if not username_val or not name_val or not password_val:
                        continue # Skip empty or invalid rows safely
                        
                    # Prevent database crashes due to duplicate unique keys
                    existing = Warden.query.filter_by(username=username_val).first()
                    if existing:
                        duplicate_errors.append(f"Row {index + 2}: Username '{username_val}' already exists. Skipped.")
                        continue
                    
                    warden = Warden(
                        username=username_val,
                        name=name_val,
                        password=password_val
                    )
                    wardens_to_add.append(warden)
                
                # Efficient bulk transaction commit
                if wardens_to_add:
                    db.session.bulk_save_objects(wardens_to_add)
                    db.session.commit()
                    flash(f'Successfully imported {len(wardens_to_add)} Warden records!', 'success')
                
                if duplicate_errors:
                    for err in duplicate_errors:
                        flash(err, 'warning')
                        
                return redirect(url_for('admin_page', id=current_user.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f"Error parsing file: {str(e)}", 'danger')
                return redirect(request.url)
                
        else:
            flash('Invalid format! Please use a valid .csv, .xlsx, or .xls file.', 'danger')
            return redirect(request.url)
            
    return render_template('warden_bulk_import.html')

if __name__ == '__main__' :
    app.run(debug=True)

