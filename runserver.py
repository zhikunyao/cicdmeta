from flask import Flask, request
#from flask_restful import Resource, Api
from flask_restx import Resource, Api
from flask_sqlalchemy import SQLAlchemy

import requests
import os
import sys
import json
import logging
from datetime import datetime

from extensions import app, db

from model import ServiceEnv, Config, UserBindLane

api = Api(app)

# Test用的资源
@api.route('/config')
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

@api.route('/service')
class ServiceResource(Resource):
    def get(self):
        ret = {}
        ret["service"] = ["cloud-service", "backup-api", "cloud-meta"]
        return ret
@api.route('/service_env')
class ServiceEnvResource(Resource):
    def get(self):
        service_name = request.json.get('service') or "%"
        service_env_name = request.json.get('env') or "%"
        deleted = request.json.get('deleted') or False
        ret = db.session.query(ServiceEnv).filter(ServiceEnv.service_env_name.like(service_env_name),
                                                  ServiceEnv.service_name.like(service_name),
                                                  ServiceEnv.deleted == deleted).limit(50)
        ret = [{"service_env_name": service_env.service_env_name,
                "service_name": service_env.service_name,
                "creator": service_env.creator,
                "update_time": str(service_env.update_time)} for service_env in ret]
        db.session.commit()
        return ret
    def post(self):
        service_name = request.json.get('service')
        service_env_name = request.json.get('env')
        creator_name = request.json.get('creator') or "unknown"
        # check invalid input
        if "uat" in service_env_name or "prod" in service_env_name:
            return {"result": "FAIL", "msg": "service_env name cannot contain uat"}
        ret = db.session.query(ServiceEnv).filter_by(service_env_name=service_env_name,
                                                     service_name=service_name,
                                                     deleted=False).first()
        if ret:
            return {"result": "FAIL", "msg": "service_env already exists",
                    "creator": ret.creator, "create_time": str(ret.create_time),
                    "update_time": str(ret.update_time)}
        else:
            new_service_env = ServiceEnv(service_env_name=service_env_name,
                                         service_name=service_name,
                                         creator=creator_name)
            db.session.add(new_service_env)
            db.session.commit()
            return {"result": "SUCCESS", "msg": "service_env add",
                    "id": new_service_env.id}
    def delete(self):
        service_name = request.json.get('service')
        service_env_name = request.json.get('env')
        force_deleted = request.json.get('force_delete') or False
        service_env = db.session.query(ServiceEnv).filter_by(service_env_name=service_env_name,
                                                             service_name=service_name,
                                                             deleted=False).first()
        if service_env:
            if not force_deleted:
                service_env.deleted = True
                logging.error("user_name: %s, service_env_name: %s" % (service_env.creator, service_env.service_env_name))
            else:
                db.session.delete(service_env)
            db.session.commit()
            return {"result": "SUCCESS", "msg": "service_env delete",
                    "id": service_env.id}
        else:
            return {"result": "FAIL", "msg": "service_env not found"}


@api.route('/user_bind_lane')
class UserBindLaneResource(Resource):
    def get(self):
        ret = {}
        record = db.session.query(UserBindLane).order_by(UserBindLane.update_time.desc())
        for lane in record:
            ret[lane.user_name] = { "lane_name": lane.lane_name, "status": lane.status, "update_time": str(lane.update_time) }
        return ret

    def post(self):
        user_name = request.json['user_name']
        lane_name = request.json['lane_name']
        same_user = db.session.query(UserBindLane).filter_by(user_name=user_name).first()
        if same_user:
            if same_user.status == "locked":
                return {"result": "FAIL", "msg": "user is locked"}
            else:
                same_user.lane_name = lane_name
                same_user.status = "locked"
                db.session.add(same_user)
                db.session.commit()
                return {"result": "SUCCESS", "msg": "success bind existed user with new lane"}
        else:
            same_lane = db.session.query(UserBindLane).filter_by(lane_name=lane_name).first()
            if same_lane:
                if same_lane.status == "locked":
                    return {"result": "FAIL", "msg": "lane is already locked"}
                else:
                    same_lane.user_name = user_name
                    db.session.add(same_lane)
                    db.session.commit()
                    return {"result": "SUCCESS", "msg": "success bind existed lane with new user"}
            else:
                new_user_bind_lane = UserBindLane(user_name=user_name, lane_name=lane_name, status="locked")
                db.session.add(new_user_bind_lane)
                db.session.commit()
                return {"result": "SUCCESS", "msg": "success bind lane with new user and lane"}


# used for demo
@api.route('/redis/<param>')
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

#api.add_resource(ConfigResource, '/config')
#api.add_resource(ServiceResource, '/service')
#api.add_resource(ServiceEnvResource, '/service_env')
#api.add_resource(UserBindLaneResource, '/user_bind_lane')
#api.add_resource(RedisResource, '/redis/<param>')

if __name__ == '__main__':
    app.run(debug=True)
