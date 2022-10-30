import json
import time
from flask import Flask
import volatildap

schemas=['core.schema', 'cosine.schema', 'inetorgperson.schema', 'nis.schema']
people = {
    'ou=people,dc=lueneburg,dc=wirgarten,dc=com': {
        'objectClass': ['organizationalUnit', 'top'],
        'ou': ['people']
    },
}
admin = {
    'uid=admin,ou=people,dc=lueneburg,dc=wirgarten,dc=com': {
        'objectClass': ['person', 'organizationalPerson', 'inetOrgPerson'],
        'cn': ['admin'],
        'sn': ['admin'],
        'uid': ['admin'],
    },
}
initial_data = {**people, **admin}

s = None


app = Flask(__name__)

@app.route('/start')
def start():
    global s
    s = volatildap.LdapServer(schemas=schemas, host='0.0.0.0', port=5000, rootpw='7sYTyHOhEHrnOq8l6taa', rootdn='cn=testadmin,dc=lueneburg,dc=wirgarten,dc=com', suffix='dc=lueneburg,dc=wirgarten,dc=com', initial_data=initial_data)
    s.start()
    time.sleep(3)
    return json.dumps({})


@app.route('/stop')
def stop():
    global s
    if s is None:
        return json.dumps({})
    s.stop()
    return json.dumps({})

app.run(host='0.0.0.0', port=1000)