from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import webview
import threading 

app = Flask(__name__, static_folder='./static', template_folder='./templates')
app.secret_key = 'many random bytes'
app.config['MYSQL_USER'] = 'root'           #this is root username here
app.config['MYSQL_PASSWORD'] = ''           #give the mysql database here
app.config['MYSQL_DB'] = ''                 #here create a database name in mysql workbench
app.config['MYSQL_HOST'] = 'localhost'

mysql = MySQL(app)

# Google Sheets configuration
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('', scope)  #login into the google cloud and download json data and give path here
client = gspread.authorize(creds)
sheet = client.open_by_key('').worksheet('Sheet1')  #here give the google sheet key

@app.route('/')
@app.route('/page/<int:page>')
def Index(page=1):
    per_page = 10
    cur = mysql.connection.cursor()
    
    offset = (page - 1) * per_page
    cur.execute("SELECT * FROM students LIMIT %s OFFSET %s", (per_page, offset))
    data = cur.fetchall()
    
    cur.execute("SELECT COUNT(*) FROM students")
    total = cur.fetchone()[0]
    cur.close()
    
    total_pages = total // per_page + (1 if total % per_page > 0 else 0)
    
    return render_template('index2.html', students=data, page=page, total_pages=total_pages)

@app.route('/insert', methods=['POST'])
def insert():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        # Check if email or phone already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students WHERE email=%s OR phone=%s", (email, phone))
        existing_record = cur.fetchone()

        if existing_record:
            flash("Email or phone number already exists. Please use a different email or phone number.", "error")
        else:
            flash("Data Inserted Successfully", "success")
            cur.execute("INSERT INTO students (name, email, phone) VALUES (%s, %s, %s)", (name, email, phone))
            mysql.connection.commit()

            cur.execute("SELECT LAST_INSERT_ID()")
            last_id = cur.fetchone()[0]

            # Update Google Sheets
            sheet.append_row([last_id, name, email, phone])

        cur.close()

        return redirect(url_for('Index'))

@app.route('/delete/<string:id_data>', methods=['GET'])
def delete(id_data):
    flash("Record Has Been Deleted Successfully")
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM students WHERE id=%s", (id_data,))
    mysql.connection.commit()

    # Delete data from Google Sheets
    records = sheet.get_all_records()
    for idx, record in enumerate(records):
        if str(record.get('id')) == id_data:
            sheet.delete_rows(idx + 2)  # Adjust for header row
            break

    return redirect(url_for('Index'))

@app.route('/update', methods=['POST', 'GET'])
def update():
    if request.method == 'POST':
        id_data = request.form['id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        cur = mysql.connection.cursor()
        cur.execute("""
               UPDATE students
               SET name=%s, email=%s, phone=%s
               WHERE id=%s
            """, (name, email, phone, id_data))
        flash("Data Updated Successfully")
        mysql.connection.commit()

        # Update data in Google Sheets
        records = sheet.get_all_records()
        for idx, record in enumerate(records):
            if str(record.get('id')) == id_data:
                sheet.update_cell(idx + 2, 2, name)  # Adjust for header row, column 2 for 'name'
                sheet.update_cell(idx + 2, 3, email)  # Column 3 for 'email'
                sheet.update_cell(idx + 2, 4, phone)  # Column 4 for 'phone'
                break

        return redirect(url_for('Index'))

def start_server():
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=start_server).start()
    
    webview.create_window("My Web App", "http://127.0.0.1:5000")
    webview.start()
