from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
import requests


# 读取当前目录下的文件以加载敏感配置
import os
import sys
import json
import logging
from datetime import datetime
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

from model import Config, UserBindLane

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app, engine_options={"isolation_level": "READ_UNCOMMITTED"})

api = Api(app)

# Test资源
class ConfigResource(Resource):
    def get(self):
        kvs = Config.query.all()
        ret = {kv.key: kv.value for kv in kvs}
        ret['version'] = "v0.1"
        return ret

    def post(self):
        new_config = Config(key=request.json['key'], value=request.json['value'])
        db.session.add(new_config)
        db.session.commit()
        return {"id":new_config.id, "key":new_config.key, "value":new_config.value}

class ServiceResource(Resource):
    def get(self):
        ret = {}
        ret["service"] = ["cloud-service", "backup-api", "cloud-meta"]
        return ret

class UserBindLaneResource(Resource):
    def get(self):
        ret = {}
        db.session.commit()
        record = UserBindLane.query.order_by(UserBindLane.update_time.desc())
        for lane in record:
            ret[lane.user_name] = { "lane_name": lane.lane_name, "status": lane.status, "update_time": str(lane.update_time) }
        db.session.commit()
        return ret

    def post(self):
        user_name = request.json['user_name']
        lane_name = request.json['lane_name']
        db.session.commit()
        same_user = UserBindLane.query.filter_by(user_name=user_name).first()
        db.session.commit()
        #logging.error(" user_name: %s, lane_name: %s" % (user_name, lane_name))
        if same_user:
            #logging.error(" user_name: %s, lane_name: %s, status: %s" % (same_user.user_name, same_user.lane_name, same_user.status))
            if same_user.status == "locked":
                return {"result": "FAIL", "msg": "user is locked"}
            else:
                same_user.lane_name = lane_name
                same_user.status = "locked"
                same_user.update_time = datetime.now()
                db.session.add(same_user)
                db.session.commit()
                return {"result": "SUCCESS", "msg": "success bind existed user with new lane"}
        else:
            same_lane = UserBindLane.query.filter_by(lane_name=lane_name).first()
            db.session.commit()
            if same_lane:
                if same_lane.status == "locked":
                    return {"result": "FAIL", "msg": "lane is already locked"}
                else:
                    same_lane.user_name = user_name
                    db.session.add(same_lane)
                    db.session.commit()
                    return {"result": "SUCCESS", "msg": "success bind existed lane with new user"}
            else:
                new_user_bind_lane = UserBindLane(user_name=user_name, lane_name=lane_name, status="locked", update_time=datetime.now())
                db.session.add(new_user_bind_lane)
                db.session.commit()
                return {"result": "SUCCESS", "msg": "success bind lane with new user and lane"}


# used for demo
class RedisResource(Resource):
    def get(self, param):
        from rediscluster import RedisCluster
        startup_nodes = [{"host": "cicdmeta-redis-redis-cluster", "port": 6379}]
        redis_cluster = RedisCluster(startup_nodes=startup_nodes, password="YX17UHx4PP")
        byte_data = redis_cluster.get(param)
        string_data = byte_data.decode('utf-8')
        ret = {"key": param, "value": string_data}
        return ret

    def post(self, param):
        key = param
        value = request.json['value']
        from rediscluster import RedisCluster
        startup_nodes = [{"host": "cicdmeta-redis-redis-cluster", "port": 6379}]
        redis_cluster = RedisCluster(startup_nodes=startup_nodes, password="YX17UHx4PP")
        bool_data = redis_cluster.set(key, value)
        ret = {"msg": bool_data, "key": param, "value": value}
        return ret

api.add_resource(ConfigResource, '/config')
api.add_resource(ServiceResource, '/service')
api.add_resource(UserBindLaneResource, '/user_bind_lane')
api.add_resource(RedisResource, '/redis/<param>')

if __name__ == '__main__':
    app.run(debug=True)
