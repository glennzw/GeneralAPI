# General API
<img align="right" src="theGeneral.jpg">
"Ten-hut! Fall IN, coders."
"Sir, yes, sir!"

### Intro
General API allows you to expose arbitary databases via an API. For example, you have a MySQL database with stuff in it, and want another system to be able to access the data, but you're not that keen to give raw database access. Solution? You fire up GeneralAPI pointing it at your MySQL server, select which tables and columns to share, and it'll automagically expose a RESTful API.

### Quickstart
Edit the ```config.ini``` file to match your database/tables/columns and change the default API access password, then simply run:

```python genAPI.py```

Your API service will start up on port 5001 (by default). List all tables with ```/api/v1/listtables``` and grab some data with ```/api/v1/query/?table=users&cols=name,age```

### API Calls

```/api/v1/listtables/```
Returns all tables that can queried by the API.

```/api/v1/query/```
Query a table for data. There are several parameters that cab be passed:

|Parameter|Purpose|Default|Example|
|---|---|---|---|
|table   |Specify table to query   |None   |```table=users```   |
|cols   |Which columns to fetch data from   |All columns   |```cols=users,depts```   |
|q   |Simple matching query. Colon for equality, coma separated   |None   |```q=name:bob,age:30```   |
|limit|How many rows to return|50|```limit=100```

### Configuration
Below is an example ```config.ini``` file.
```
[database]
name=TopSecret
type=mysql
host=localhost
port=3306
user=topkek
password=potato
database=secrets
encoding=utf-8
allowedtables=users:username,email;countries;hobbies:id,name,description

[authentication]
basicUser=default
basicPassword=default
adminUser=default
adminPassword=default
```

The ```[database]``` section includes specifications for the database to connect to. Host, port, user, and password will not apply to SQLite databases.

The ```allowedtables``` option specifies which tables/columns are allowed. Note the format:
<tablename1>[:col1,col2];<tablename2>[:col1,col2]

If the column names are ommitted, the default behaviour is to allow all columns in the table to be queried.

The ```[authentication]``` section includes credentials for a basic user (to query the API), and an admin user (which is currently not supported).

### Supported Databases
The following databases are supported:
* MySQL
* MSSQL
* PostgreSQL
* SQLite
* Oracle
* Sybase
* Firebird

Testing has only been done on SQLite and MySQL.

### Example Output
 Example output:

```http://localhost:5001/api/v1/listtables/```

```
{
  "count": 2,
  "data": [
    {
      "columns": [
        "id",
        "name"
      ],
      "table": "depts"
    },
    {
      "columns": [
        "id",
        "name",
        "age",
        "password"
      ],
      "table": "users"
    }
  ],
  "status": "success"
}
```

```http://localhost:5001/api/v1/query/?table=users&cols=name,age```

```
{
  "count": 2,
  "data": [
    {
      "columns": [
        "id",
        "name"
      ],
      "table": "depts"
    },
    {
      "columns": [
        "id",
        "name",
        "age",
        "password"
      ],
      "table": "users"
    }
  ],
  "status": "success"
}
```
