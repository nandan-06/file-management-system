from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///file_transactions.db'
db = SQLAlchemy(app)
app.secret_key = 'your_super_secret_key'

users = {'user1': 'Test123'}
FILES_DIRECTORY = "./files/"

class FileTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(20), nullable=False) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FileTransaction {self.filename}, {self.action}, {self.timestamp}>"
    
@app.before_first_request
def create_tables():
    db.create_all()

    
def log_transaction(filename, action):
    transaction = FileTransaction(filename=filename, action=action)
    db.session.add(transaction)
    db.session.commit()

def authenticate(username, password):
    return username in users and users[username] == password

def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('home'))
        return func(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            session['username'] = username 
            return redirect(url_for('actions'))
        else:
            return render_template('login.html', message='Invalid credentials')

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/actions')
@login_required
def actions():
    return render_template('actions.html')

@app.route('/files')
@login_required
def list_files():
    files_with_path = [os.path.join(FILES_DIRECTORY, file) for file in os.listdir(FILES_DIRECTORY)]    
    files_details = []
    for file in files_with_path:
        size = os.path.getsize(file)
        _, ext = os.path.splitext(file)
        format = ext[1:] if ext else 'Unknown' 
        creation_time = time.ctime(os.path.getctime(file))

        files_details.append((os.path.basename(file), size, format, creation_time))

    sorted_files_details = sorted(files_details, key=lambda x: x[1]) 
    return render_template('list_files.html', files=sorted_files_details)

@app.route('/upload_files', methods=['GET', 'POST'])
@login_required
def upload_files():
    if request.method == 'GET':
        return render_template('upload.html')
    else:
        uploaded_files = request.files.getlist('files')

        # Check if the list is empty
        if not uploaded_files or all(file.filename == '' for file in uploaded_files):
            return "No files to upload"

        for file in uploaded_files:
            if file.filename != '':  # Check if the file is not empty
                filename = secure_filename(file.filename).replace(' ', '_')
                file.save(os.path.join(FILES_DIRECTORY, filename))
                log_transaction(filename, 'upload')

        return redirect(url_for('list_files'))



@app.route('/download_files/<filename>', methods=['GET'])
@login_required
def download_files(filename):
    log_transaction(filename, 'download')
    return send_from_directory(FILES_DIRECTORY, filename, as_attachment=True)

@app.route('/delete_files/<filename>', methods=['POST'])
@login_required
def delete_files(filename):
    filename = secure_filename(filename)
    file_path = os.path.join(FILES_DIRECTORY, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        log_transaction(filename, 'delete') 
        return redirect(url_for('list_files'))
    else:
        return "File not found", 404

@app.route('/transactions')
@login_required
def get_transactions():
    transactions = FileTransaction.query.all()
    return render_template('transactions.html', transactions=transactions)

if __name__ == '__main__':
    app.run(debug=True)
