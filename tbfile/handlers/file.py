from os import path, unlink
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, BufferedReader
from PIL import Image
from flask import Blueprint, request, current_app
from werkzeug.wsgi import wrap_file
from werkzeug.exceptions import NotFound
from gridfs import GridFS
from gridfs.errors import NoFile
from flask_pymongo import BSONObjectIdConverter

from tblib.mongo import mongo
from tblib.handler import json_response, ResponseCode

from ..models import FileSchema

executor = ThreadPoolExecutor(max_workers=2)
file = Blueprint('file', __name__, url_prefix='')


@file.route('/files', methods=['POST'])
def create_file():
    """保存表单上传文件到 GridFS
    """

    # 通过 request.files 获取上传的文件信息，如果为空，抛出 NotFound 异常
    if 'file' not in request.files or request.files['file'].filename == '':
        raise NotFound()
    # 调用 PyMongo.save_file(filename, fileobj) 方法上传文件，返回id值
    id = mongo.save_file(request.files['file'].filename, request.files["file"])
    # os.path.splitext 方法将文件名和扩展名分开，这里获取扩展名
    _, ext = path.splitext(request.files['file'].filename)
    # 使用 json_response 生成返回信息并处理为 json
    executor.submit(lambda: make_thumbnails(id))
    return json_response(id='{}{}'.format(id, ext))

def make_thumbnails(id):
    try:
        file = GridFS(mongo.db).get(id)
    except NoFile:
        raise NotFound()

    img = Image.open(file)

    thumbnails = {}
    for size in (1024, 512, 200):
        t = img.copy()
        t.thumbnail((size, size))
        filename = '{}_{}.jpg'.format(id, size)
        filepath = '/tmp/{}'.format(filename)
        t.save(filepath, "JPEG")
        with open(filepath, 'rb') as f:
            thumbnails['{}'.format(size)] = mongo.save_file(filename, f)
        unlink(filepath)

    mongo.db.fs.files.update({'_id': id}, {
        '$set': {
            'thumbnails': thumbnails
        }
    })

@file.route('/files/<id>', methods=['GET'])
def file_info(id):
    """获取文件信息
    """

    # 获取文件的 id 值
    id, _ = path.splitext(id)
    # 使用 flask_pymongo.BSONObjectIdConverter() 函数将 id 字符串转换为 id 对象
    id = BSONObjectIdConverter({}).to_python(id)

    try:
        # 根据 id 获取对应的文件
        file = GridFS(mongo.db).get(id)
    except NoFile:
        raise NotFound()
    # FileSchema().dump(file) 将 file 类对象转换为字典
    return json_response(file=FileSchema().dump(file))


def file_response(id, download=False):
    try:
        file = GridFS(mongo.db).get(id)
    except NoFile:
        raise NotFound()

    # 将 GridFS 文件对象包装为一个 WSGI 文件对象，使用的方法为 werkzeug.wsgi.wrap_file(environ, file, buffer_size=8192)
    data = wrap_file(request.environ, file, buffer_size=1024 * 255)
    # 创建一个 Flask Response 对象来响应文件内容
    response = current_app.response_class(
        data,
        mimetype=file.content_type,
        direct_passthrough=True,
    )
    # 设置内容长度响应头
    response.content_length = file.length
    # 设置内容最后修改时间 和 Etag 响应头，浏览器可根据这些信息来判断文件内容是否有更新
    response.last_modified = file.upload_date
    etag = getattr(file, "md5", None)
    if etag:
        response.set_etag(etag)
    else:
        # 没有 md5 就别强行设置 ETag，避免 Werkzeug 报错
        # 也可以用文件 id 做一个弱 ETag（可选）
        response.set_etag(str(file._id), weak=True)

    # 设置缓存时间和公开性响应头，这里缓存时间设为了大约一年
    response.cache_control.max_age = 365 * 24 * 3600
    response.cache_control.public = True
    # 让响应变为条件性地，如果跟 request 里的头信息对比发现浏览器里已经缓存有最新内容，那么本次响应内容将为空
    response.make_conditional(request)
    # 如果是下载模式，需要添加 Content-Disposition 响应头
    # 注意 filename 需要编码为 utf-8，否则中文会乱码
    if download:
        response.headers.set(
            'Content-Disposition', 'attachment', filename=file.filename.encode('utf-8'))

    return response


@file.route('/<id>', methods=['GET'])
def view_file(id):
    """浏览文件内容，在浏览器里直接展示文件内容，比如图片
    """

    id, _ = path.splitext(id)
    id = BSONObjectIdConverter({}).to_python(id)

    return file_response(id)


@file.route('/<id>/download', methods=['GET'])
def download_file(id):
    """下载文件内容，让浏览器打开一个保存窗口来保存文件
    """

    id, _ = path.splitext(id)
    id = BSONObjectIdConverter({}).to_python(id)

    return file_response(id, True)


