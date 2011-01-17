#!/usr/bin/python

 
from  RuoteAMQP.workitem import Workitem
from  RuoteAMQP.participant import Participant
try:
     import json
except ImportError:
     import simplejson as json
import time
import os, sys, traceback, ConfigParser, optparse, io, pwd, grp
import daemon
from img.common import build_kickstart
participant_name = "build_ks"

# Fallback configuration. If you need to customize it, copy it somewhere 
# ( ideally to your system's configuration directory ), modify it and 
# pass it with the -c option
defaultconf = """[boss]
amqp_host = 127.0.0.1:5672
amqp_user = boss
amqp_pwd = boss
amqp_vhost = boss
[%s]
daemon = Yes 
logfile = /var/log/%s.log
runas_user = nobody
runas_group = nogroup
ksstore = /srv/BOSS/ksstore
reposerver = http://download.meego.com
""" % ( participant_name, participant_name ) 

parser = optparse.OptionParser()
parser.add_option("-c", "--config", dest="filename", 
                  help="read configuration from CFILE", metavar="CFILE")
(options, args) = parser.parse_args()

try:
    conf = open(options.filename)
except:
    # Fallback
    conf = io.BytesIO(defaultconf)

config = ConfigParser.ConfigParser()
config.readfp(conf)
conf.close()

amqp_vhost = config.get('boss', 'amqp_vhost')
amqp_pwd = config.get('boss', 'amqp_pwd')
amqp_user = config.get('boss', 'amqp_user')
amqp_host = config.get('boss', 'amqp_host')
d = config.get(participant_name, 'daemon')
daemonize = False
if d == "Yes":
    daemonize = True

logfile = config.get(participant_name, 'logfile')
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]

ksstore = config.get(participant_name, "ksstore")
reposerver = config.get(participant_name, "reposerver")



packages= {}
class KickstartBuilderParticipant(Participant):    
    def consume(self):
        try:
            wi = self.workitem
            print json.dumps(wi.to_h(), sort_keys=True, indent=4)
            fields = wi.fields()
            params = wi.params()

            projects = []
            if "project" in fields.keys() and "repo" in fields.keys():
              project = fields["project"] 
              repo = fields["repository"]
              project_uri = project.replace(":", ":/")
              repo = repo.replace(":", ":/")
              base_url = reposerver+'/'+project_uri+'/'+repo
              projects = [ base_url ]

            packages = []
            if 'from' in params.keys():
              packages = fields[params['from']]
            else:
              packages = fields["packages"]
            
            print packages
            sys.stdout.flush()

            if "ksfile" in fields.keys():
              ksfile = os.path.join(ksstore, fields["ksfile"])
              ks = build_kickstart(ksfile, packages=packages, projects=projects)
            elif "kickstart" in fields.keys():
              kstemplate = tempfile.NamedTemporaryFile(delete=False)
              kstemplate.write(fields("kickstart"))
              kstemplate.close()
              ksfile = kstemplate.name
              ks = build_kickstart(ksfile, packages=packages, projects=projects)
              os.remove(ksfile)

            wi.set_field("kickstart", str(ks.handler))
            if "rid" in fields.keys():
              wi.set_field("id", str(fields['rid']) + '-' + time.strftime('%Y%m%d-%H%M%S'))
            else:
              wi.set_field("id", time.strftime('%Y%m%d-%H%M%S'))

            if not "name" in fields.keys():
              wi.set_field("name", os.path.basename(ksfile)[0:-3])

            msg = wi.lookup("msg") if "msg" in wi.fields() else []
            msg.append("Kickstart handled successfully.")
            wi.set_field("msg", msg)

            print json.dumps(wi.to_h(), sort_keys=True, indent=4)
            sys.stdout.flush()
            result = True
        except Exception as e:
            print type(e)
            print e
            traceback.print_exc(file=sys.stdout)
            sys.stdout.flush()
            result = False
            msg = wi.lookup("msg") if "msg" in wi.fields() else []
            msg.append("Failed to handle to kickstart.")
            wi.set_field("msg", msg)
            wi.set_field("status", "FAILED")
            pass
        wi.set_result(result)
  
def main():
    print "Kickstart building participant running"
    sys.stdout.flush()
    # Create an instance
    p = KickstartBuilderParticipant(ruote_queue=participant_name, amqp_host=amqp_host,  amqp_user=amqp_user, amqp_pass=amqp_pwd, amqp_vhost=amqp_vhost)
    # Register with BOSS
    p.register(participant_name, {'queue':participant_name})
    # Enter event loop
    p.run()               

if __name__ == "__main__":
    if daemonize:
        log = open(logfile,'a+')
        with daemon.DaemonContext(stdout=log, stderr=log, uid=uid, gid=gid):
            main()
    else:
        main() 
