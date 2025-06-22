from flask import Flask, render_template, request, redirect, session, flash
from flask_mail import Mail, Message
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Email 設定
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'a0966480840@gmail.com'
app.config['MAIL_PASSWORD'] = 'cl930927'
mail = Mail(app)

# 初始化資料庫
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            item TEXT,
            quantity INTEGER,
            status TEXT DEFAULT '準備中'
        )
    """)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    latest_order = None
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("""SELECT item, quantity, status FROM orders 
                     WHERE username=? ORDER BY id DESC LIMIT 1""",
                  (session['username'],))
        latest_order = c.fetchone()
        conn.close()
    return render_template('index.html', latest_order=latest_order)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("註冊成功，請登入")
            return redirect('/login')
        except:
            flash("帳號已存在")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = username
            flash("登入成功")
            return redirect('/')
        else:
            flash("登入失敗")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("已登出")
    return redirect('/')

@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])
        username = session['username']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO orders (username, item, quantity) VALUES (?, ?, ?)",
                  (username, item, quantity))
        conn.commit()
        conn.close()

        # ✅ 寄出 email 通知
        try:
            msg = Message('訂單已送出',
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[f'{username}@example.com'])  #⚠️ 這邊請改成實際 email
            msg.body = f"您已成功下訂單：{item} x {quantity}"
            mail.send(msg)
        except Exception as e:
            print(f"Email 發送失敗：{e}")

        flash("✅ 訂單已成功送出！")
        return redirect('/')

    return render_template('order.html')

@app.route('/my_orders')
def my_orders():
    if 'username' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, item, quantity, status FROM orders WHERE username=?", (session['username'],))
    orders_raw = c.fetchall()
    conn.close()

    orders = [(item, qty, status, order_id) for order_id, item, qty, status in orders_raw]

    return render_template('my_orders.html', orders=orders)

@app.route('/manage_orders', methods=['GET', 'POST'])
def manage_orders():
    if session.get('username') != 'admin':
        return redirect('/')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        order_id = request.form['order_id']
        new_status = request.form['new_status']
        c.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
        conn.commit()
    c.execute("SELECT id, username, item, quantity, status FROM orders")
    orders = c.fetchall()
    conn.close()
    return render_template('manage_orders.html', orders=orders)

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # 確認該訂單屬於登入使用者且狀態是「準備中」
    c.execute("SELECT status FROM orders WHERE id=? AND username=?", (order_id, username))
    order = c.fetchone()

    if order and order[0] == '準備中':
        c.execute("DELETE FROM orders WHERE id=?", (order_id,))
        conn.commit()
        flash("訂單已取消")
    else:
        flash("無法取消此訂單")

    conn.close()
    return redirect('/my_orders')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
