from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this to a real secret key

DATABASE = 'bank.db'
ADMIN_PASSWORD = 'admin123'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            balance REAL NOT NULL CHECK (balance >= 0)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        name = request.form['name'].strip()
        password = request.form['password']
        deposit = request.form['deposit']

        if not name or not password or not deposit:
            flash('All fields are required.', 'danger')
            return redirect(url_for('create_account'))
        try:
            deposit = float(deposit)
            if deposit < 0:
                raise ValueError
        except ValueError:
            flash('Deposit must be a positive number.', 'danger')
            return redirect(url_for('create_account'))

        conn = get_db_connection()
        conn.execute('INSERT INTO accounts (name, password, balance) VALUES (?, ?, ?)', 
                     (name, password, deposit))
        conn.commit()
        account_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        flash(f'Account created! Your Account ID is {account_id}', 'success')
        return redirect(url_for('home'))

    return render_template('create_account.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        if role == 'admin':
            password = request.form['password']
            if password == ADMIN_PASSWORD:
                session['admin_logged_in'] = True
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin password.', 'danger')
                return redirect(url_for('login'))
        else:
            account_id = request.form['account_id']
            password = request.form['password']
            if not account_id.isdigit():
                flash('Account ID must be numeric.', 'danger')
                return redirect(url_for('login'))
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM accounts WHERE account_id = ? AND password = ?', 
                                (int(account_id), password)).fetchone()
            conn.close()
            if user:
                session['user_id'] = user['account_id']
                session['user_name'] = user['name']
                flash(f'Welcome, {user["name"]}!', 'success')
                return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid Account ID or password.', 'danger')
                return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM accounts WHERE account_id = ?', (user_id,)).fetchone()
    conn.close()
    return render_template('user_dashboard.html', user=user)

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    amount = request.form.get('amount', '')
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash('Please enter a valid positive amount.', 'danger')
        return redirect(url_for('user_dashboard'))

    user_id = session['user_id']
    conn = get_db_connection()
    conn.execute('UPDATE accounts SET balance = balance + ? WHERE account_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
    flash(f'Deposited ₹{amount:.2f} successfully.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    amount = request.form.get('amount', '')
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash('Please enter a valid positive amount.', 'danger')
        return redirect(url_for('user_dashboard'))

    user_id = session['user_id']
    conn = get_db_connection()
    balance = conn.execute('SELECT balance FROM accounts WHERE account_id = ?', (user_id,)).fetchone()['balance']
    if amount > balance:
        flash('Insufficient balance.', 'danger')
        conn.close()
        return redirect(url_for('user_dashboard'))

    conn.execute('UPDATE accounts SET balance = balance - ? WHERE account_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
    flash(f'Withdrawn ₹{amount:.2f} successfully.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login as admin first.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', accounts=accounts)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
