import json
from insite_plugin import InsitePlugin
from ipmi_poller import poller


class Plugin(InsitePlugin):

    """
       Returns true if we can pass more then 1 host in through the hosts field in the fetch function
    """
    # ldconfig -p | grep python
    # nano setup/application.json
    # "CLASSPATH" : "{nature-home}/application/lib/*:{nature-home}/application/lib/insite/*:{nature-home}/configuration/global:{nature-home}",
    # "LD_PRELOAD" : "/usr/lib/x86_64-linux-gnu/libpython3.5m.so.1.0"

    def can_group(self):
        return False

    """
       Fetches the details for the provided host
       Will return a json formatted string of the form
       @note the initial arguments may also be accessed through the use of
             the dictionary self.parameters which contains all the values
             specified in the script arguments for the poller configuration
       @param hosts, A list of hosts that we want to poll.  This will always
                     contain a single host unless can_group() returns true in
                     which all hosts we want to poll will be pushed into the
                     hosts array in a single call
       @return a single document of the structure
       {
          "fields" : {
             "fieldname": "value",
             "fieldname": value,
             ...
          },
          "host" : "host",
          "name" : "metric-group"
       }
       or
       an array of these objects [{...}, {...}, ...]
    """

    def fetch(self, hosts):

        state = None
        passwd = None
        user = None
        hostname = None
        nosecure = None

        try:

            self.ipmi

        except Exception:

            self.ipmi = poller(address=hosts[-1], user=user, passwd=passwd,
                               hostname=hostname, nosecure=nosecure, state=state)

        documents = []

        _xml = self.ipmi.webfetch()

        if _xml:

            self.ipmi.sensorProcess(_xml)

            for host in self.ipmi.returnServer():

                for sensor in self.ipmi.returnSensors(host):

                    document = {
                        "fields": sensor,
                        "host": host,
                        "name": 'poller'
                    }

                    documents.append(document)

        return json.dumps(documents)
