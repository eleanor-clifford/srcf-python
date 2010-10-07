"""
	SRCF wrapper for MoinMoin; based on MoinMoin standard CGI driver script 1.9.2

	@copyright: 2000-2005 by Juergen Hermann <jh@web.de>,
	            2008 by MoinMoin:ThomasWaldmann,
	            2008 by MoinMoin:FlorianKrupicka,
	            2010 by Malcolm Scott <mas90@srcf.ucam.org>
	@license: GNU GPL, see COPYING for details.
"""

import sys, os, grp

from MoinMoin import log
# This needs to happen before multiconfig is imported :-(
log.load_config("/usr/local/share/srcf/moin-1.9.2/logconfig.stderr")

from MoinMoin.config import multiconfig, url_prefix_static


class SRCFMoinMoinConfig(multiconfig.DefaultConfig):

	def __init__(self, configdir, title, srcfgroup, args):

		# Critical setup  ---------------------------------------------------

		# Directory containing THIS wikiconfig:
		self.wikiconfig_dir = configdir

		# We assume that this config file is located in the instance directory, like:
		# instance_dir/
		#              wikiconfig.py
		#              data/
		#              underlay/
		# If that's not true, feel free to just set instance_dir to the real path
		# where data/ and underlay/ is located:
		self.instance_dir = configdir

		# Where your own wiki pages are (make regular backups of this directory):
		self.data_dir = os.path.join(self.instance_dir, 'data', '') # path with trailing /

		# Where system and help pages are (you may exclude this from backup):
		self.data_underlay_dir = os.path.join(self.instance_dir, 'underlay', '') # path with trailing /

		# Site name, used by default for wiki name-logo [Unicode]
		if not self.sitename or self.sitename == multiconfig.DefaultConfig.sitename:
			self.sitename = title

		# This is checked by some rather critical and potentially harmful actions,
		# like despam or PackageInstaller action:
		if not self.superuser or self.superuser == multiconfig.DefaultConfig.superuser:
			self.superuser = grp.getgrnam(srcfgroup)[3] + [srcfgroup]

		# IMPORTANT: grant yourself admin rights! replace YourName with
		# your user name. See HelpOnAccessControlLists for more help.
		# All acl_rights_xxx options must use unicode [Unicode]
		if not self.acl_rights_before or self.acl_rights_before == multiconfig.DefaultConfig.acl_rights_before:
			self.acl_rights_before = " ".join(map(lambda user: u"%s:read,write,delete,revert,admin" % user, self.superuser))
		if not self.acl_rights_default or self.acl_rights_default == multiconfig.DefaultConfig.acl_rights_default:
			self.acl_rights_default = u"All:read"

		multiconfig.DefaultConfig.__init__(self, args)


	# The URL prefix we use to access the static stuff (img, css, js).
	# Note: moin runs a static file server at url_prefix_static path (relative
	# to the script url).
	# If you run your wiki script at the root of your site (/), just do NOT
	# use this setting and it will automatically work.
	# If you run your wiki script at /mywiki, you need to use this:
	url_prefix_static = '/_srcf/moin'


	# Wiki identity ----------------------------------------------------

	# Wiki logo. You can use an image, text or both. [Unicode]
	# For no logo or text, use '' - the default is to show the sitename.
	# See also url_prefix setting below!
	#logo_string = u'<img src="%s/common/moinmoin.png" alt="MoinMoin Logo">' % url_prefix_static

	# name of entry page / front page [Unicode], choose one of those:

	# a) if most wiki content is in a single language
	#page_front_page = u"MyStartingPage"

	# b) if wiki content is maintained in many languages
	page_front_page = u"FrontPage"

	# The interwiki name used in interwiki links
	#interwikiname = u'UntitledWiki'
	# Show the interwiki name (and link it to page_front_page) in the Theme,
	# nice for farm setups or when your logo does not show the wiki's name.
	#show_interwiki = 1


	# Security ----------------------------------------------------------

	# Use Raven authentication
	from MoinMoin.auth import GivenAuth
	auth = [GivenAuth(autocreate=True)]

	# This is checked by some rather critical and potentially harmful actions,
	# like despam or PackageInstaller action:
	#superuser = [u"YourName", ]

	# IMPORTANT: grant yourself admin rights! replace YourName with
	# your user name. See HelpOnAccessControlLists for more help.
	# All acl_rights_xxx options must use unicode [Unicode]
	#acl_rights_before = u"YourName:read,write,delete,revert,admin"

	# The default (ENABLED) password_checker will keep users from choosing too
	# short or too easy passwords. If you don't like this and your site has
	# rather low security requirements, feel free to DISABLE the checker by:
	#password_checker = None # None means "don't do any password strength checks"

	# Link spam protection for public wikis (Uncomment to enable)
	# Needs a reliable internet connection.
	from MoinMoin.security.antispam import SecurityPolicy


	# Mail --------------------------------------------------------------

	# Configure to enable subscribing to pages (disabled by default)
	# or sending forgotten passwords.

	# SMTP server, e.g. "mail.provider.com" (None to disable mail)
	mail_smarthost = "localhost"

	# The return address, e.g u"Ihate Unicode <noreply@mywiki.org>" [Unicode]
	mail_from = u"Wiki on SRCF <support@srcf.ucam.org>"

	# "user pwd" if you need to use SMTP AUTH
	#self.mail_login = ""


	# User interface ----------------------------------------------------

	# Add your wikis important pages at the end. It is not recommended to
	# remove the default links.  Leave room for user links - don't use
	# more than 6 short items.
	# You MUST use Unicode strings here, but you need not use localized
	# page names for system and help pages, those will be used automatically
	# according to the user selected language. [Unicode]
	navi_bar = [
	    # If you want to show your page_front_page here:
	    #u'%(page_front_page)s',
	    u'RecentChanges',
	    u'FindPage',
	    u'HelpContents',
	]

	# The default theme anonymous or new users get
	theme_default = 'modern'


	# Language options --------------------------------------------------

	# See http://moinmo.in/ConfigMarket for configuration in
	# YOUR language that other people contributed.

	# The main wiki language, set the direction of the wiki pages
	language_default = 'en'

	# the following regexes should match the complete name when used in free text
	# the group 'all' shall match all, while the group 'key' shall match the key only
	# e.g. CategoryFoo -> group 'all' ==  CategoryFoo, group 'key' == Foo
	# moin's code will add ^ / $ at beginning / end when needed
	# You must use Unicode strings here [Unicode]
	page_category_regex = ur'(?P<all>Category(?P<key>(?!Template)\S+))'
	page_dict_regex = ur'(?P<all>(?P<key>\S+)Dict)'
	page_group_regex = ur'(?P<all>(?P<key>\S+)Group)'
	page_template_regex = ur'(?P<all>(?P<key>\S+)Template)'


	# Content options ---------------------------------------------------

	# Show users hostnames in RecentChanges
	show_hosts = 1

	# Enable graphical charts, requires gdchart.
	#chart_options = {'width': 600, 'height': 300}


def runCGIwiki(moinmoinversion, configdir):

	# a) Configuration of Python's code search path
	#    If you already have set up the PYTHONPATH environment variable for the
	#    stuff you see below, you don't need to do a1) and a2).

	# a1) Path of the directory where the MoinMoin code package is located.
	#     Needed if you installed with --prefix=PREFIX or you didn't use setup.py.
	#sys.path.insert(0, 'PREFIX/lib/python2.3/site-packages')

	# a2) Path of the directory where wikiconfig.py / farmconfig.py is located.
	#     See wiki/config/... for some sample config files.
	#sys.path.insert(0, '/etc/moin')
	sys.path.insert(0, configdir)

	# b) Configuration of moin's logging
	#    If you have set up MOINLOGGINGCONF environment variable, you don't need this!
	#    You also don't need this if you are happy with the builtin defaults.
	#    See wiki/config/logging/... for some sample config files.
	# This is done on import (ugh) because multiconfig prods the logger on input (ugh ugh!).

	# this works around a bug in flup's CGI autodetection (as of flup 1.0.1):
	os.environ['FCGI_FORCE_CGI'] = 'Y' # 'Y' for (slow) CGI, 'N' for FCGI

	# SRCF hack: avoid "index.cgi" appearing in generated URLs
	os.environ['SCRIPT_NAME'] = os.environ['SCRIPT_NAME'].replace('/index.cgi','',1)

	if moinmoinversion == "1.9.2":
		from MoinMoin.web.flup_frontend import CGIFrontEnd
		CGIFrontEnd().run()
	else:
		print "Content-type: text/plain\n\n"
		print "Don't know how to handle the specified version of MoinMoin!\n\n"
		print "Contact soc-srcf-admin@lists.cam.ac.uk for assistance."

