# -*- coding: utf-8 -*-
import datetime
# from string import strip
from app import app, db, lm
from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Monitor, ROLE_USER
from .forms import LoginForm, SignUpForm, AboutMeForm, AddMonitorItemForm
from .PriceMonitor import additemcrawl
import tweepy

@app.route('/')
@app.route('/index')
def index():
    try:
        item_number = Monitor.query.count()
        user_number = User.query.count()
    except:
        return render_template("index.html", title="首页")
    return render_template("index.html", title="首页", item_number=item_number, user_number=user_number)

@app.route('/about-me')
def about_me():
    return render_template("about_me.html", title="关于我")

@app.route('/iot2012')
def iot2012():
    return render_template("iot2012.html", title="江大物联网")

@app.route('/twitter')
def twitter():
    consumer_key = "kIzG8NiFtJJKMtM8j6mjIJASm"
    consumer_secret = "zz346qvg5beasTDC8GvUvVqYD4B7XruTez63h7OCLUD8wCYyiT"
    access_token = '851927351831085056-Ennbtyu5E0MIrQcspvYSBuItSZdFX9i'
    access_token_secret = 'ApSomBKX2FQ4vy2r0AZrXReDVerPbmnDhL2p1KeQptXoO'
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    twitter_trump = api.user_timeline('realDonaldTrump')

    return render_template("twitter.html", title="推特", twitter_trump=twitter_trump)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 验证用户是否被验证
    if current_user.is_authenticated:
        return redirect('index')
    # 注册验证
    form = LoginForm()
    if form.validate_on_submit():
        user = User.login_check(request.form.get('user_name'))
        user_name = request.form.get('user_name')
        password = request.form.get('password')

        # 密码验证
        try:
            user_forpwd = User.query.filter(User.nickname == user_name).first()
            print(type(user_forpwd), user_forpwd.password)
            if not check_password_hash(user_forpwd.password, password):
                flash('用户名或密码错误')
                return redirect('/login')
        except:
            flash("该用户疑似不存在密码")
            return redirect('/login')

        if user:
            login_user(user)
            user.last_seen = datetime.datetime.now()

            try:
                db.session.add(user)
                db.session.commit()
            except:
                flash("数据库读取错误，请重试")
                return redirect('/login')

            # flash(request.form.get('user_name'))
            # flash('remember me? ' + str(request.form.get('remember_me')))
            flash('登陆成功')
            return redirect(url_for("users", user_id=current_user.id))
        else:
            flash('没有该用户，请注册')
            return redirect('/login')

    return render_template("login.html", title="Sign In", form=form)


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    form = SignUpForm()
    user = User()
    if form.validate_on_submit():
        user_name = request.form.get('user_name')
        user_email = request.form.get('user_email')
        password = request.form.get('password')
        password = generate_password_hash(password)
        register_check = User.query.filter(db.or_(
            User.nickname == user_name, User.email == user_email)).first()
        if register_check:
            flash("用户名或邮箱重复")
            return redirect('/sign-up')

        if len(user_name) and len(user_email):
            user.nickname = user_name
            user.email = user_email
            user.role = ROLE_USER
            user.password = password
            try:
                db.session.add(user)
                db.session.commit()
            except:
                flash("数据库读取错误，请重试")
                return redirect('/sign-up')

            flash("注册成功")
            return redirect('/login')

    return render_template("sign_up.html", form=form)


@app.route('/user/<int:user_id>', methods=["POST", "GET"])
@login_required
def users(user_id):
    form = AboutMeForm()
    user = User.query.filter(User.id == user_id).first()
    if user_id is not current_user.id:
        return redirect(url_for('index'))
    if not user:
        flash("The user is not exist.")
        redirect("/index")
    all_item = user.all_item.all()

    return render_template("user.html", form=form, user=user, all_item=all_item)


@app.route('/addmonitoritem/<int:user_id>', methods=["POST", "GET"])
@login_required
def addmonitoritem(user_id):
    form = AddMonitorItemForm()
    item = Monitor()
    if form.validate_on_submit():
        item_id = request.form.get("item_id")
        if not len(item_id.strip()):
            flash("商品ID为必填项")
            return redirect(url_for("addmonitoritem", user_id=user_id))
        user_price = request.form.get("user_price")
        if not len(user_price.strip()):
            flash("The content is necessray!")
            return redirect(url_for("addmonitoritem", user_id=user_id))
        mall_id = request.form.get("mall_id")
        if not len(item_id.strip()):
            flash("The content is necessray!")
            return redirect(url_for("addmonitoritem", user_id=user_id))
        item.item_id = item_id
        item.user_price = user_price
        item.mall_id = mall_id
        item.add_date = datetime.datetime.now()
        item.user_id = user_id
        item.status = True
        try:
            item_exist = Monitor.query.filter(Monitor.item_id == item_id).first()
            # print(item_exist)
            if item_exist is not None:
                flash("该商品已经在监控列表中")
                return redirect(url_for("users", user_id=user_id))
        except:
            flash("数据库查询商品错误，请重试")
            return redirect(url_for("addmonitoritem", user_id=user_id))

        item_name, item_price = additemcrawl.additemcrawl(item_id, user_id, mall_id)
        print(type(item_name), type(item_price), item_name)
        if type(item_name) == str:
            flash("该商品不存在，请输入正确的商品ID")
            return redirect(url_for("addmonitoritem", user_id=user_id))
        
        item.item_name = item_name
        item.item_price = item_price

        try:
            db.session.add(item)
            db.session.commit()
        except:
            flash("写入数据库错误")
            return redirect(url_for("addmonitoritem", user_id=user_id))
        flash("添加商品成功")
        return redirect(url_for("users", user_id=user_id))

    return render_template("addmonitoritem.html", form=form)


@app.route('/deleteitem/<int:user_id>/<int:item_id>', methods=["POST", "GET"])
@login_required
def delete_item(item_id, user_id):
    try:
        db.session.query(Monitor).filter_by(id=item_id).delete()
        db.session.commit()
    except:
        flash("数据库读取错误，请重试")
        return redirect(url_for("users", user_id=user_id))
    return redirect(url_for("users", user_id=user_id))


@app.route('/onitem/<int:user_id>/<int:item_id>', methods=["POST", "GET"])
@login_required
def on_item(item_id, user_id):
    try:
        db.session.query(Monitor).filter_by(id=item_id).update({"status": True})
        db.session.commit()
    except:
        flash("数据库读取错误，请重试")
        return redirect(url_for("users", user_id=user_id))
    return redirect(url_for("users", user_id=user_id))


@app.route('/offitem/<int:user_id>/<int:item_id>', methods=["POST", "GET"])
@login_required
def off_item(item_id, user_id):
    try:
        db.session.query(Monitor).filter_by(id=item_id).update({"status": False})
        db.session.commit()
    except:
        flash("数据库读取错误，请重试")
        return redirect(url_for("users", user_id=user_id))
    return redirect(url_for("users", user_id=user_id))