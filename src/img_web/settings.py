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
#~ along with this program.  If not, see <http://www.gnu.org/licenses/>

# Django settings for img project.
from os.path import abspath, dirname, join
PROJECT_DIR = dirname(__file__)

IMGCONF="/etc/imager/img.conf"

import ConfigParser
config = ConfigParser.ConfigParser()
config.readfp(open(IMGCONF))

url_prefix = config.get('web', 'url_prefix')
process_filename = config.get('web', 'image_process')
static_media_collect = config.get('web', 'static_media_collect')

boss_host = config.get('web', 'boss_host')
boss_user = config.get('web', 'boss_user')
boss_pass = config.get('web', 'boss_pass')
boss_vhost = config.get('web', 'boss_vhost')

db_engine = config.get('web', 'db_engine')
db_name = config.get('web', 'db_name')
db_user = config.get('web', 'db_user')
db_pass = config.get('web', 'db_pass')

DEVICEGROUP = config.get('web', 'devicegroup')
TEMPLATESDIR = config.get('web', 'templates_dir')

USE_LDAP = config.getboolean('web', 'use_ldap')
if USE_LDAP:
  LDAP_SERVER = config.get('web', 'ldap_server')
  LDAP_DN_TEMPLATE = config.get('web', 'ldap_dn_template', raw=True)
  
  mail_attr = config.get('web', 'ldap_mail_attr', raw=True)
  fname_attr = config.get('web', 'ldap_fname_attr', raw=True)
  lname_attr = config.get('web', 'ldap_lname_attr', raw=True)
  AUTH_LDAP_USER_ATTR_MAP = {"first_name" : fname_attr, "last_name" : lname_attr, "email":mail_attr}

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS
DATABASES = {
            'default': {
                'ENGINE' : 'django.db.backends.' + db_engine,
                'NAME' : db_name,
                'USER' : db_user,
                'PASSWORD' : db_pass,
                'HOST' : '',
                'PORT' : '',
                }
            }

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/' + url_prefix + '/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/' + url_prefix + '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'yn!2toc#7_#!c5k)xeh9j75()8kb7n2p!tl_h#@+%eptl=vd16'

STATIC_ROOT = static_media_collect

#STATIC_ROOT = join(PROJECT_DIR, "site_media")

STATIC_URL = '/site_media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'img_web.urls'

TEMPLATE_DIRS = (
                 join(PROJECT_DIR,'templates'), 
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'south',
    'img_web.app',
)

FORCE_SCRIPT_NAME = ''

LOGIN_URL='/' + url_prefix + "/login/"
LOGIN_REDIRECT_URL='/' + url_prefix + "/"

if USE_LDAP:
  import ldap
  from django_auth_ldap.config import LDAPSearch
  import logging
  
  logger = logging.getLogger('django_auth_ldap')
  logger.addHandler(logging.StreamHandler())
  logger.setLevel(logging.DEBUG)

  AUTH_LDAP_SERVER_URI = LDAP_SERVER
  AUTH_LDAP_USER_DN_TEMPLATE = LDAP_DN_TEMPLATE

  AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
  )

