#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# @glennzw
# ToDo: Only allow certain columns
#	Include API key / user in auth.sql
#   Handle UTF and MySQL no sleep options for connection string
#   Add OR functioanlity
#   Add GT and LT for numeric,time
#   Joins? No, rather give user ability to  create JOIN VIEWS in webui
#   WebUI

from sqlalchemy import *
import ConfigParser
from flask import Response, Flask, request, jsonify
import logging
from functools import wraps
import os.path

DEBUG_MODE = False
PORT = 5001

# Console colors
W  = '\033[0m'  # white (normal)
R  = '\033[31m' # red
G  = '\033[32m' # green
O  = '\033[33m' # orange
B  = '\033[34m' # blue
P  = '\033[35m' # purple
C  = '\033[36m' # cyan
GR = '\033[37m' # gray
BB = '\033[1m'  # Bold
NB = '\033[0m'  # Not bold
F  = '\033[5m'  # Flash
NF = '\033[25m' # Not flash

#Logging
logging.addLevelName(logging.INFO,P + "+" + G)
logging.addLevelName(logging.ERROR,R + "!!" + G)
logging.addLevelName(logging.DEBUG,"D")
logging.addLevelName(logging.WARNING, R + "WARNING" + G)
logging.addLevelName(logging.CRITICAL, R + "CRITICAL ERROR" + G)

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(filename)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='generalAPI.log',
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
logging.getLogger('').addHandler(console)

def row2dict(row):
    d = {}
    for column in row.keys():#__table__.columns:
        tmp =  getattr(row, column)
        if isinstance(tmp, unicode):
            tmp = tmp.encode('utf-8')
        tmp = str(tmp)
        d[column] = tmp
    return d

def returnData(results):
    data = []
    numResults = len(results)
    for row in results:
        r = row2dict(row)
        data.append(r)

    toReturn = {"status": "success", "count" : numResults, "data" : data }
    return(jsonify(toReturn))

class GeneralAPI(object):
    """Class to expose a database via a Flask driven API"""

    def __init__(self, configFile="config.ini"):
        #Read the config file
        if not os.path.isfile(configFile):
            logging.error("Cannot find config file '%s'" % configFile)
            exit(0)
        Config = ConfigParser.ConfigParser()
        Config.read(configFile)

        name = Config.get("database", "name")
        dialect = Config.get("database", "type")
        database = Config.get("database", "database")
        if dialect != "sqlite":
            user = Config.get("database", "user")
            password = Config.get("database", "password")
            host = Config.get("database", "host")
            port  = Config.get("database", "port")
        tmp_at = Config.get("database", "allowedtables")
        self.allowedTables = {}
        for a_tbl in tmp_at.split(";"):
            ts = a_tbl.split(":")
            tblName = ts[0]
            if len(ts) > 1:
              cols = ts[1]
            else:
               cols = "*"
            cols = cols.split(",")
            self.allowedTables.setdefault(tblName, []).extend(cols)

        self.basicUser = Config.get("authentication", "basicUser")
        self.basicPass = Config.get("authentication", "basicPassword")
        self.adminUser = Config.get("authentication", "adminUser")
        self.adminPass = Config.get("authentication", "adminPassword")

        if self.basicUser == "default" or self.basicPass == "default" or self.adminUser == "default" or self.adminPass == "default":
            logging.error("Please change the default usernames and passwords in the config file!")
            exit(-1)

        if dialect != "sqlite":
            tmp_dbms = dialect + "://" + user + ":" + password + "@" + host + ":" + port + "/" + database
        else:
            tmp_dbms = dialect + "://" + database

        logging.info("Connecting to %s database" % dialect)
        try:
            self.db = create_engine(tmp_dbms)
            self.metadata = MetaData(self.db)
            self.metadata.reflect()
        except Exception, e:
            logging.exception(e)
            logging.exception("Unable to connect to database using connection string: '%s'" % tmp_dbms)
        logging.info("Connection successful")

    def startAPIServer(self):
        app = Flask(__name__)

        """Below we have functions to handle authentication"""
        def check_auth(username, password):
            return username == self.basicUser and password == self.basicPass

        def authenticate():
            """Sends a 401 response that enables basic auth"""
            return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'})

        def requires_auth(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                auth = request.authorization
                if not auth or not check_auth(auth.username, auth.password):
                    return authenticate()
                return f(*args, **kwargs)
            return decorated


        """Below we have functions to handle API calls"""

        @app.route('/api/v1/listtables/')
        @requires_auth
        def list_tables():
            result = []
            for table in self.allowedTables:
                tmp_tbl = self.metadata.tables[table]
                tmpR = {"table" : table, "columns":[]}
                for c in tmp_tbl.columns:
                    c = str(c).partition(".")[2]
                    if "*" in self.allowedTables[table] or c in self.allowedTables[table]:
                        tmpR["columns"].append(c)
                result.append(tmpR)

            message = {"status":"success", "count":len(self.allowedTables), "data": result}
            return jsonify(message)


        @app.route('/api/v1/query/')
        @requires_auth
        def get_raw():
            table = request.args.get('table')
            if not table:
                result = {"status":"error", "reason":"No table specified"}
                return jsonify(result)
            if table not in self.allowedTables:
                result = {"status":"error", "reason":"Bad table name"}
                return jsonify(result)

            tmp_tbl = self.metadata.tables[table]
            cols = request.args.get('cols')
            if not cols:
                cols = [x.name for x in tmp_tbl.columns]
            else:
                cols = cols.split(",")
            limit = request.args.get('limit')
            if not limit:
                limit = 50
            filters = []
            queries = request.args.get('q')
            if queries:
                queries = queries.split(",")
                for q in queries:
                    try:
                        col, search = q.split(":")
                        filters.append(tmp_tbl.columns[col] == search )
                    except Exception, e:
                        logging.exception(e)
                        result = {"status":"error", "reason":"Bad query"}
                        return jsonify(result)

            colsR = []
            for c in cols:
                if c not in tmp_tbl.columns:
                    result = {"status":"error", "reason":"No such column"}
                    return jsonify(result)
                colsR.append(tmp_tbl.columns[c])
            s = select(colsR, and_(*filters)).limit(limit)
            res = self.db.execute(s).fetchall()
            #return "Querying table '%s' for column '%s' for query '%s'" % (table, cols, queries)
            return( returnData(res))

        logging.info("Starting API service...")
        app.debug=DEBUG_MODE
        app.run(host="0.0.0.0",port=PORT)

def main():
    ga = GeneralAPI()
    ga.startAPIServer()

if __name__ == "__main__":
    main()
