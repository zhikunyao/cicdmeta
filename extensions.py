from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# 读取当前目录下的文件以加载敏感配置
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 获取环境变量设置配置文件
if 'CICDMETA_ENV' in os.environ:
    if os.environ['CICDMETA_ENV'] == 'prod':
        config_name = "config_prod.json"
    elif os.environ['CICDMETA_ENV'] == 'dev':
        config_name = "config_dev.json"
else:
    config_name = "config_dev.json"

with open(config_name, 'r') as f:
    config = json.load(f)
# 读取特定 section 的特定 key 的值
DB = config['SQLALCHEMY_DATABASE_URI']
if os.environ.get('CICDMETA_ENV') == 'prod' and 'SECRET_MYSQL_PASSWORD' in os.environ and 'SECRET_MYSQL_USER' in os.environ:
    DB = DB.replace("SECRET_MYSQL_PASSWORD", os.environ['SECRET_MYSQL_PASSWORD'])
    DB = DB.replace("SECRET_MYSQL_USER", os.environ['SECRET_MYSQL_USER'])

TOKENS = config['API_TOKENS']

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"isolation_level": "READ_UNCOMMITTED"}

db = SQLAlchemy(app)