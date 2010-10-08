#!/usr/bin/python2.6
#~ Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
#~ Contact: Ramez Hanna <ramez.hanna@nokia.com>
#~ This program is free software: you can redistribute it and/or modify
#~ it under the terms of the GNU General Public License as published by
#~ the Free Software Foundation, either version 3 of the License, or
#~ (at your option) any later version.

#~ This program is distributed in the hope that it will be useful,
#~ but WITHOUT ANY WARRANTY; without even the implied warranty of
#~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#~ GNU General Public License for more details.

#~ You should have received a copy of the GNU General Public License
#~ along with this program.  If not, see <http://www.gnu.org/licenses/>.

try:
     import json
except ImportError:
     import simplejson as json
import subprocess as sub
from subprocess import CalledProcessError
import os, sys, random, pwd, grp
import daemon
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import shutil
import re
import time
from amqplib import client_0_8 as amqp
from img.worker import ImageWorker
from multiprocessing import Process, Queue, Pool

import pykickstart.commands as kscommands
import pykickstart.constants as ksconstants
import pykickstart.errors as kserrors
import pykickstart.parser as ksparser
import pykickstart.version as ksversion
from pykickstart.handlers.control import commandMap
from pykickstart.handlers.control import dataMap

from mic.imgcreate.kscommands import desktop
from mic.imgcreate.kscommands import moblinrepo
from mic.imgcreate.kscommands import micboot

import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imager/img.conf')

amqp_host = config.get('amqp', 'amqp_host')
amqp_user = config.get('amqp', 'amqp_user')
amqp_pwd = config.get('amqp', 'amqp_pwd')
amqp_vhost = config.get('amqp', 'amqp_vhost')
num_workers = config.getint('worker', 'num_workers')
base_dir = config.get('worker', 'base_dir')
base_url = config.get('worker', 'base_url')
use_kvm = config.get('worker', 'use_kvm')
reposerver = config.get('worker', 'reposerver')
templates_dir = config.get('worker', 'templates_dir')

# Daemon information
participant_name = "build_image"
d = config.get("", 'daemon')
daemonize = False
if d == "Yes":
    daemonize = True

config_logfile = config.get(participant_name, 'logfile')
config_logfile = config_logfile+'.'+str(random.randint(1,65535))
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]
# if not root...kick out
if not os.geteuid()==0:
    sys.exit("\nOnly root can run this script\n")
if not os.path.exists('/dev/kvm') and use_kvm == "yes":
    sys.exit("\nYou must enable KVM kernel module\n")
conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
chan = conn.channel()

chan.queue_declare(queue="image_queue", durable=True, exclusive=False, auto_delete=False)
chan.queue_declare(queue="kickstarter_queue", durable=True, exclusive=False, auto_delete=False)
chan.queue_declare(queue="status_queue", durable=False, exclusive=False, auto_delete=False)

chan.exchange_declare(exchange="image_exchange", type="direct", durable=True, auto_delete=False,)
chan.exchange_declare(exchange="django_result_exchange", type="direct", durable=True, auto_delete=False,)

chan.queue_bind(queue="image_queue", exchange="image_exchange", routing_key="img")
chan.queue_bind(queue="kickstarter_queue", exchange="image_exchange", routing_key="ks")
chan.queue_bind(queue="status_queue", exchange="django_result_exchange", routing_key="status")

using_version = ksversion.DEVEL
commandMap[using_version]["desktop"] = desktop.Moblin_Desktop
commandMap[using_version]["repo"] = moblinrepo.Moblin_Repo
commandMap[using_version]["bootloader"] = micboot.Moblin_Bootloader
dataMap[using_version]["RepoData"] = moblinrepo.Moblin_RepoData
superclass = ksversion.returnClassForVersion(version=using_version)

class KSHandlers(superclass):
    def __init__(self, mapping={}):
        superclass.__init__(self, mapping=commandMap[using_version])

def mic2(id, name,type, email, kickstart, release, arch):
    dir = "%s/%s"%(base_dir, id)
    os.mkdir(dir, 0775)    
    tmp = open(dir+'/'+name+'.ks', mode='w+b')    
    tmpname = tmp.name
    logfile_name = dir+'/'+name+"-log"
    tmp.write(kickstart)            
    tmp.close()
    os.chmod(tmpname, 0644)
    file = base_url+"%s"%id    
    logfile = open(logfile_name,'w')
    logurl = base_url+id+'/'+os.path.split(logfile.name)[-1]     
    worker = ImageWorker(id, tmpname, type, logfile, dir, chan=chan, name=name, release=release, arch=arch)    
    worker.build()
    logfile.close()
    
job_pool = Pool(num_workers)
def mic2_callback(msg):  
    print "mic2"
    job = json.loads(msg.body)    
    email = job["email"]
    id = job["id"]    
    type = job['imagetype']
    ksfile = job['ksfile']   
    name = job['name']
    release = job['release']
    arch = None
    if 'arch' in job:
        arch = job['arch']
    file = base_url+id
    data = json.dumps({"status":"IN QUEUE", "id":str(id), 'url':str(file)})
    statusmsg = amqp.Message(data)
    chan.basic_publish(statusmsg, exchange="django_result_exchange", routing_key="status")  
    args=(id, name, type, email, ksfile)
    #job_pool.apply_async(mic2, args=args)
    mic2(id, name, type, email, ksfile, release, arch)        
 
def kickstarter_callback(msg):
    print "ks"
    kickstarter = json.loads(msg.body)    
    config = kickstarter["config"]
    email = kickstarter["email"]    
    id = kickstarter['id']
    imagetype = kickstarter['imagetype']
    release = kickstarter['release']
    config = kickstarter['config']
    print config
    kstemplate = config['Template']
    ks = ksparser.KickstartParser(KSHandlers())
    ks.readKickstart(kstemplate)
    if 'Packages' in config.keys():
        packages = config['Packages']
        ks.handler.packages.add(packages)
    if 'Projects' in config.keys():
        projects = config['Projects']
        for project in projects:
            project_uri = project.replace(":", ":/")
            base_url = reposerver+'/'+project_uri
            ks.handler.repo.repoList.append(moblinrepo.Moblin_RepoData(baseurl=base_url,name=project))
    # We got the damn thing published, move on
    ksfile = str(ks.handler)

    data = json.dumps({'email':email, 'id':id, 'imagetype':imagetype, 'ksfile':ksfile, 'name':os.path.basename(kstemplate), 'release':release})
    msg2 = amqp.Message(data)        
    chan.basic_publish(msg2, exchange="image_exchange", routing_key="img")        
    
    print "ks end"
    
def main():
    chan.basic_consume(queue='image_queue', no_ack=True, callback=mic2_callback)
    chan.basic_consume(queue='kickstarter_queue', no_ack=True, callback=kickstarter_callback)
    while True:
        chan.wait()
    chan.basic_cancel("img")
    chan.basic_cancel("ks")
    chan.close()
    conn.close()

if __name__ == "__main__":
    if daemonize:
        log = open(config_logfile,'w+')
        with daemon.DaemonContext(stdout=log, stderr=log, uid=uid, gid=gid):
            main()
    else:
        main()