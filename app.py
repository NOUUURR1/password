from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import bcrypt
import os
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

app = Flask(__name__ )
CORS(app)

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# نموذج المستخدم
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    birthdate = db.Column(db.String(20))
    profile_image_url = db.Column(db.String(500))

# نموذج كود إعادة التعيين
class ResetCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

with app.app_context():
    db.create_all()

# إرسال كود إلى الإيميل
@app.route('/send-reset-code', methods=['POST'])
def send_reset_code():
    data = request.get_json()
    email = data.get('email')

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Email not found'}), 404

    code = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=10)

    # حذف أي أكواد قديمة
    ResetCode.query.filter_by(email=email).delete()

    reset_code = ResetCode(email=email, code=code, expiry=expiry)
    db.session.add(reset_code)
    db.session.commit()

    # بيانات البريد
    sender_email = "projectteam1235@gmail.com"
    sender_password = os.getenv("EMAIL_PASSWORD")  # يتم أخذه من متغير بيئي في Railway
    subject = "Your Password Reset Code"
    body = f"Your verification code is: {code}"

    message = MIMEText(body)
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = subject

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, message.as_string())
        server.quit()
    except Exception as e:
        return jsonify({'message': f'Failed to send email: {str(e)}'}), 500

    return jsonify({'message': 'Reset code sent to email'}), 200

# التحقق من الكود
@app.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')

    record = ResetCode.query.filter_by(email=email, code=code).first()
    if not record:
        return jsonify({'message': 'Invalid code'}), 400
    if datetime.utcnow() > record.expiry:
        return jsonify({'message': 'Code expired'}), 400

    return jsonify({'message': 'Code verified'}), 200

# إعادة تعيين كلمة المرور
@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')

    record = ResetCode.query.filter_by(email=email, code=code).first()
    if not record:
        return jsonify({'message': 'Invalid code'}), 400
    if datetime.utcnow() > record.expiry:
        return jsonify({'message': 'Code expired'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password = hashed_password

    db.session.commit()
    db.session.delete(record)
    db.session.commit()

    return jsonify({'message': 'Password has been reset successfully'}), 200

# تشغيل الخادم
if __name__ == "__main__":
    app.run
