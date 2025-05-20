from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector
import pandas as pd
from config import Config
import re
import MySQLdb
from flask_mysqldb import MySQL
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = Flask(__name__)
app.config.from_object(Config)

# Render için proxy ayarları
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

mysql = MySQL(app)

# Güvenlik başlıklarını ekle
@app.after_request
def add_security_headers(response):
    for header, value in Config.SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

# Verileri Excel'e kaydetme fonksiyonu
def save_to_excel(data):
    try:
        # Render'da geçici dosya sistemi kullanıldığı için sadece MySQL'e kaydediyoruz
        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO questions (ogrenci_ID, questions, answers, Feedback, topic) VALUES (%s, %s, %s, %s, %s)',
            (data['Student_number'][0], data['Question'][0], data['Answer'][0], data['Sentiment'][0], data['Topic'][0]),
        )
        mysql.connection.commit()
    except Exception as e:
        print(f"Veri kaydedilirken hata oluştu: {e}")

@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'Student_number' in request.form and 'Password' in request.form:
        student_number = request.form['Student_number']
        password = request.form['Password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE Student_number = %s AND Password = %s', (student_number, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['Student_number'] = account['Student_number']
            msg = 'Başarıyla giriş yapıldı!'
            return redirect('/chatbot')
        else:
            msg = 'Geçersiz kullanıcı adı veya şifre!'
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'Student_number' in request.form and 'Password' in request.form and 'name' in request.form:
        student_number = request.form['Student_number']
        password = request.form['Password']
        name = request.form['name']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE Student_number = %s', (student_number,))
        account = cursor.fetchone()
        if account:
            msg = 'Bu öğrenci numarası zaten kayıtlı!'
        elif not re.match(r'[0-9]+', student_number):
            msg = 'Öğrenci numarası sadece rakamlardan oluşmalıdır!'
        elif not re.match(r'[A-Za-z\s]+', name):
            msg = 'İsim sadece harflerden oluşmalıdır!'
        elif not student_number or not password or not name:
            msg = 'Tüm alanlar doldurulmalıdır!'
        else:
            cursor.execute('INSERT INTO users (Student_number, Password, Name) VALUES (%s, %s, %s)', (student_number, password, name))
            mysql.connection.commit()
            msg = 'Başarıyla kayıt oldunuz!'
            return redirect('/')
    return render_template('register.html', msg=msg)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'loggedin' in session:
        msg = ''
        if request.method == 'POST':
            question = request.form.get('question')
            answer = request.form.get('answer')
            sentiment = request.form.get('sentiment')
            topic = request.form.get('topic')

            # Excel'e kaydedilecek veri
            data = {
                'Student_number': [session['Student_number']],
                'Question': [question],
                'Answer': [answer],
                'Sentiment': [sentiment],
                'Topic': [topic]
            }

            # Veriyi Excel dosyasına kaydet
            save_to_excel(data)

            # Veriyi MySQL'e de kaydet (Mevcut kodunuzda olduğu gibi)
            cursor = mysql.connection.cursor()
            cursor.execute(
                'INSERT INTO questions (ogrenci_ID, questions, answers, Feedback, topic) VALUES (%s, %s, %s, %s, %s)',
                (session['Student_number'], question, answer, sentiment, topic),
            )
            mysql.connection.commit()
            msg = 'Soru başarıyla eklendi!'
        return render_template('chatbot.html', msg=msg)
    return redirect('/')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    msg = ''
    if request.method == 'POST' and 'Student_number' in request.form and 'new_password' in request.form:
        student_number = request.form['Student_number']
        new_password = request.form['new_password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE Student_number = %s', (student_number,))
        account = cursor.fetchone()
        
        if account:
            cursor.execute('UPDATE users SET Password = %s WHERE Student_number = %s', (new_password, student_number))
            mysql.connection.commit()
            msg = 'Şifreniz başarıyla sıfırlandı!'
        else:
            msg = 'Öğrenci numaranız bulunamadı!'
    
    return render_template('reset_password.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('Student_number', None)
    return redirect('/')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)