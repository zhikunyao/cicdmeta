from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 读取根目录下的文件以加载敏感配置
import os
import sys
import json
import datetime
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(120), nullable=False)
    def __repr__(self):
        return '<Key %r>' % self.key

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(80), unique=True, nullable=False)
    main_git_url = db.Column(db.String(1024), nullable=False)
    main_artifact_url = db.Column(db.String(1024), nullable=False)

class Artifact(db.Model):
    # build info
    id = db.Column(db.Integer, primary_key=True)
    artifact_name = db.Column(db.String(80), unique=True, nullable=False) #milvus
    artifact_type = db.Column(db.String(20), nullable=False) # target = adm_image or arm_image or XXX
    build_image_name = db.Column(db.String(1024), nullable=False) # how to prepare the build env
    main_git_url = db.Column(db.String(1024), nullable=False) # git source
    main_artifact_url = db.Column(db.String(1024), nullable=False) # 主存制品的harbor镜像地址，通常是离构建机房最近的harbor
    build_command = db.Column(db.String(120), nullable=True)

class ArtifactVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    create_time = db.Column(db.DateTime, nullable=False)
    update_time = db.Column(db.DateTime, nullable=False)
    artifact_name = db.Column(db.String(80), nullable=False)
    artifact_version = db.Column(db.String(80), unique=True, nullable=False)
    main_git_commit_id = db.Column(db.String(80), nullable=False) # commit id = e55c4450...
    main_git_commit_title = db.Column(db.String(120), nullable=False)  # commit message = enhance: use the key
    main_git_branch = db.Column(db.String(120), nullable=False) # 构建分支
    build_url = db.Column(db.String(1024), nullable=False) # 记录编译任务的链接 = https://jenkins...
    artifact_url = db.Column(db.String(1024), nullable=False) # 记录上传制品的链接 = https://harbor...

    artifact_tag = db.Column(db.String(120), nullable=False) # 关键的制品标签置信源，用于实现不同业务版本的构建区分，比如商业版vs开源版

class ServiceTree(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_tree_name = db.Column(db.String(80), unique=True, nullable=False)
    parent_service_tree_name = db.Column(db.String(80), nullable=False) # default as root，一层树状结构

    attributes = db.Column(db.String(4096), nullable=False) # Json 格式扩展，聚合某一些微服务的通用配置

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(80), unique=True, nullable=False) # milvusdb, 不同镜像的同代码服务，算一个服务，例如Arm和adm
    service_type = db.Column(db.String(20), nullable=False) # default=microservice
    service_tree_name = db.Column(db.String(80), nullable=False) # 挂载在某个服务树下，默认为root

    attributes = db.Column(db.String(4096), nullable=False) # Json 格式扩展

class ServiceEnv(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_env_name = db.Column(db.String(80), unique=True, nullable=False) # 全局唯一，保留值有uat、prod等，避免新建
    service_name = db.Column(db.String(80), nullable=False) # 这个环境有哪个服务，cloud-backup-provider等
    # artifact_name = db.Column(db.String(80), nullable=False)  # 这个环境的镜像仓库,先删除避免出现多个cluster不一样镜像
    deleted = db.Column(db.Boolean, nullable=False, default=False)
    creator = db.Column(db.String(80), nullable=False)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)

    attributes = db.Column(db.String(120), nullable=False)  # Json 格式扩展，可以通过Service继承部分配置

class ServiceEnvLane(db.Model):
    # 服务环境能够处理大多数问题，泳道环境是一个基于prod基线和base基线的临时管理的环境，用于补充这一种场景
    id = db.Column(db.Integer, primary_key=True)
    service_env_name = db.Column(db.String(80), nullable=False) # service_env_name=test_milvusdb_arm
    lane_name = db.Column(db.String(80), nullable=False) # lane_name=feat123. 相同lane的不同服务环境是互通的
    __table_args__ = (
        db.UniqueConstraint('service_env_name', 'lane_name', name='_service_env_name_lane_name_uc'),
    ) # 相同service_env_name下的lane_name是唯一的


class ServiceEnvCluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 部署层面的信息，最小部署单元，考虑对齐k8s概念

class ServiceDeployHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

class UserBindLane(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(80), nullable=False)
    lane_name = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    update_time = db.Column(db.DateTime, nullable=False)
    # 记录锁定状态，status=locked，表示lane被锁定，不允许其他用户绑定
    def __repr__(self):
        return '<Username %r>' % self.user_name


@app.cli.command()
def initdb():
    db.create_all()
    print("Initialized the database.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        #db.drop_all()
