from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
import requests


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
TOKENS = config['API_TOKENS']

from model import Config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

class RedisResource(Resource):
    def get(self, param):
        from rediscluster import RedisCluster
        startup_nodes = [{"host": "cicdmeta-redis-redis-cluster", "port": 6379}]
        redis_cluster = RedisCluster(startup_nodes=startup_nodes, password="YX17UHx4PP")
        ret = redis_cluster.get(param)
        return ret


api.add_resource(ConfigResource, '/config')
api.add_resource(ServiceResource, '/service')
api.add_resource(ServiceResource, '/redis/<param>')

if __name__ == '__main__':
    app.run(debug=True)
