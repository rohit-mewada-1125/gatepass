from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = '4vVHzUbjPhBdt+TPaOorZv1Bg1+qNNrc'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql12737165:fKiQFzY8et@sql12.freesqldatabase.com/sql12737165'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.permanent_session_lifetime = timedelta(days=7)

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50))
    lastname = db.Column(db.String(50))
    phone_num = db.Column(db.String(15))
    branch = db.Column(db.String(50))
    year = db.Column(db.String(10))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

class HOD(db.Model):
    __tablename__ = 'hods'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    branch = db.Column(db.String(50))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

class GatePassRequest(db.Model):
    __tablename__ = 'gate_pass_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.Enum('Pending', 'Approved', 'Rejected'), default='Pending')
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    hod_id = db.Column(db.Integer, db.ForeignKey('hods.id'))

class SecurityGuard(db.Model):
    __tablename__ = 'security_guards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

def get_current_user_id():
    return session.get('user_id')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    student = Student.query.filter_by(username=username, password=password).first()
    if student:
        session['user_id'] = student.id
        session.permanent = True
        return jsonify({'message': 'Login successful!', 'redirect_url': url_for('student_dashboard')}), 200

    hod = HOD.query.filter_by(username=username, password=password).first()
    if hod:
        session['user_id'] = hod.id
        session.permanent = True
        return jsonify({'message': 'Login successful!', 'redirect_url': url_for('hod_dashboard')}), 200

    guard = SecurityGuard.query.filter_by(username=username, password=password).first()
    if guard:
        session['guard_id'] = guard.id
        session.permanent = True
        return jsonify({'message': 'Login successful!', 'redirect_url': url_for('security_guard_dashboard')}), 200

    return jsonify({'message': 'Invalid username or password!'}), 401

@app.route('/')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = get_current_user_id()
    student = Student.query.get(user_id)

    if not student:
        return redirect(url_for('login_page'))

    return render_template('studentdash.html', student=student)

@app.route('/login')
def login_page():
    return render_template('student_login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login_page'))

@app.route('/hod_dashboard')
def hod_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = get_current_user_id()
    hod = HOD.query.get(user_id)

    all_requests = GatePassRequest.query.filter_by(branch=hod.branch).all()

    pending_requests = {}
    approved_requests = {}
    rejected_requests = {}

    for request in all_requests:
        date_key = request.date_submitted.strftime('%Y-%m-%d')
        
        if request.status == 'Pending':
            if date_key not in pending_requests:
                pending_requests[date_key] = []
            pending_requests[date_key].append(request)
        elif request.status == 'Approved':
            if date_key not in approved_requests:
                approved_requests[date_key] = []
            approved_requests[date_key].append(request)
        elif request.status == 'Rejected':
            if date_key not in rejected_requests:
                rejected_requests[date_key] = []
            rejected_requests[date_key].append(request)

    return render_template('hod_dashboard.html', 
                           pending_requests=pending_requests, 
                           approved_requests=approved_requests, 
                           rejected_requests=rejected_requests)

@app.route('/apply')
def apply():
    user_id = get_current_user_id()
    student = Student.query.get(user_id)

    if not student:
        return redirect(url_for('login_page'))

    return render_template('apply.html', student=student)

@app.route('/submit-gate-pass', methods=['POST'])
def submit_gate_pass():
    user_id = get_current_user_id()
    student = Student.query.get(user_id)

    if student:
        new_request = GatePassRequest(
            first_name=student.firstname,
            last_name=student.lastname,
            branch=student.branch,
            year=student.year,
            reason=request.form['reason']
        )
        db.session.add(new_request)
        db.session.commit()
        
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login_page'))

@app.route('/approve-request/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    request_to_approve = GatePassRequest.query.get(request_id)
    if request_to_approve:
        request_to_approve.status = 'Approved'
        db.session.commit()
    return redirect(url_for('hod_dashboard'))

@app.route('/reject-request/<int:request_id>', methods=['POST'])
def reject_request(request_id):
    request_to_reject = GatePassRequest.query.get(request_id)
    if request_to_reject:
        request_to_reject.status = 'Rejected'
        db.session.commit()
    return redirect(url_for('hod_dashboard'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/handle_contact', methods=['POST'])
def handle_contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    print(f"Name: {name}, Email: {email}, Message: {message}")
    return redirect(url_for('contact'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/check_status')
def check_status():
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('login_page'))
    
    user = Student.query.get(user_id)
    requests = GatePassRequest.query.filter_by(first_name=user.firstname, last_name=user.lastname).all()
    print(f"Requests for {user.firstname} {user.lastname}: {requests}")

    return render_template('check_status.html', requests=requests)

@app.route('/security_guard_dashboard')
def security_guard_dashboard():
    if 'guard_id' not in session:
        return redirect(url_for('login_page'))

    accepted_requests = GatePassRequest.query.filter_by(status='Approved').all()
    
    return render_template('security_guard_dashboard.html', accepted_requests=accepted_requests)

if __name__ == '__main__':
    app.run()
