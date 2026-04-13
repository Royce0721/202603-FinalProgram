from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from tblib.money import to_money

from ..forms import RegisterForm, LoginForm, ProfileForm, AvatarForm, PasswordForm, WalletForm
from ..services import TbUser, TbFile
from ..models import User

user = Blueprint('user', __name__, url_prefix='/users')


@user.route('/register', methods=['GET', 'POST'])
def register():
    """注册用户
    """

    form = RegisterForm()
    # 通过表单的验证
    if form.validate_on_submit():
        # 使用 post 方法向用户服务接口 /users 注册用户信息并获得响应
        resp = TbUser(current_app).post_json('/users', json={
            'username': form.username.data,
            'password': form.password.data,
        }, check_code=False)
        # 如果响应不是成功的，就在前端闪现返回的信息，最后再返回注册页面
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/register.html', form=form)

        # 在前端闪现“注册成功”
        flash('注册成功，请登录', 'success')
        # 把页面重定向到登录页面
        return redirect(url_for('.login'))

    # 如果输入的信息没有通过表单验证，返回注册页面
    return render_template('user/register.html', form=form)


@user.route('/login', methods=['GET', 'POST'])
def login():
    """登录
    """

    form = LoginForm()
    if form.validate_on_submit():
        # 使用 get 方法向后台用户服务接口 /users/check_password 发送用户名和密码用于验证用户名和密码是否正确，并获得响应
        resp = TbUser(current_app).get_json('/users/check_password', params={
            'username': form.username.data,
            'password': form.password.data,
        }, check_code=False)
        # 如果响应不是成功的，就在前端闪现返回的信息，最后再返回登录页面
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/login.html', form=form)
        # 如果响应的 isCorrect 为 False，就说明用户名或是密码错误，依然返回登录页面
        if not resp['data']['isCorrect']:
            flash('用户名或密码错误')
            return render_template('user/login.html', form=form)

        # 用户登录
        login_user(User(resp['data']['user']), form.remember_me.data)
        # 成功登录，重定向到主页
        return redirect(url_for('common.index'))

    # 如果用户输入的信息不符合表单的验证，返回登录页面
    return render_template('user/login.html', form=form)


# 必须在登录的情况下才能退出
@user.route('/logout')
@login_required
def logout():
    """退出
    """

    # 退出用户登录
    logout_user()
    # 向前端闪现“退出成功”
    flash('退出成功', 'success')
    # 把页面重定向到主页
    return redirect(url_for('common.index'))


# 必须在登录情况下才能编辑个人资料
@user.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        # 使用 post 方法向后台用户服务接口 /users/<int:id> 发送数据修改用户个人资料，并获得响应
        resp = TbUser(current_app).post_json(
            '/users/{}'.format(current_user.get_id()), json={
                'username': form.username.data,
                'gender': form.gender.data,
                'mobile': form.mobile.data,
            }, check_code=False)
        # 如果修改不成功，闪现对应消息并返回个人资料修改页面
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/profile.html', form=form)
        # 如果修改成功，返回个人主页
        return redirect(url_for('common.index'))

    # 如果信息没有通过表单验证，返回个人资料修改页面
    return render_template('user/profile.html', form=form)


# 必须在登录情况下才能设置头像
@user.route('/avatar', methods=['GET', 'POST'])
@login_required
def avatar():
    """设置头像
    """

    form = AvatarForm()
    if form.validate_on_submit():
        # 上传头像文件到文件服务，获得一个文件 ID
        f = form.avatar.data
        # 使用 post 方法向后台文件服务接口 /files 发送文件信息，并获得响应
        resp = TbFile(current_app).post_json('/files', files={
            'file': (secure_filename(f.filename), f, f.mimetype),
        }, check_code=False)
        # 如果没有成功存储文件，向前端闪现消息，并返回设置头像页面
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/avatar.html', form=form)

        # 将前面获得的文件 ID 通过用户服务接口更新到用户资料里
        # 使用 post 方法向后台用户服务接口 /users/<int:id> 发送数据，修改头像对应的id值
        resp = TbUser(current_app).post_json(
            '/users/{}'.format(current_user.get_id()), json={
                'avatar': resp['data']['id'],
            }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/avatar.html', form=form)

        return redirect(url_for('common.index'))

    return render_template('user/avatar.html', form=form)


# 必须在登录状态下才能修改密码
@user.route('/password', methods=['GET', 'POST'])
@login_required
def password():
    """修改密码
    """

    form = PasswordForm()
    if form.validate_on_submit():
        # 使用 post 方法向后台用户服务接口 /users/<int:id> 发送数据修改密码，并返回响应
        resp = TbUser(current_app).post_json(
            '/users/{}'.format(current_user.get_id()), json={
                'password': form.password.data,
            }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/password.html', form=form)

        return redirect(url_for('common.index'))

    return render_template('user/password.html', form=form)


# 必须在登录状态下才能进行钱包充值
@user.route('/wallet', methods=['GET', 'POST'])
@login_required
def wallet():
    """钱包充值
    """

    form = WalletForm()
    if form.validate_on_submit():
        # 使用 post 方法向后台用户服务接口 /users/<int:id> 发送数据充值钱包金额，修改后的钱包金额是当前钱包金额加上充值金额
        resp = TbUser(current_app).post_json(
            '/users/{}'.format(current_user.get_id()), json={
                'wallet_money': to_money(current_user.wallet_money) + form.money.data,
            }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('user/wallet.html', form=form)

        flash('充值成功', 'info')
        return redirect(url_for('.wallet'))

    return render_template('user/wallet.html', form=form)

@user.route('/wallet_transactions')
@login_required
def wallet_transactions():
    """钱包交易记录
    """

    resp = TbUser(current_app).get_json('/wallet_transactions', params={
        'user_id': current_user.get_id(),
    })
    wallet_transactions = resp['data']['wallet_transactions']
    total = resp['data']['total']

    return render_template('user/wallet_transactions.html', wallet_transactions=wallet_transactions, total=total)
