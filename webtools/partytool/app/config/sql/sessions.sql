# $Id: sessions.sql,v 1.1 2007-05-25 05:54:14 rflint%ryanflint.com Exp $
#
# Copyright 2005-2007,	Cake Software Foundation, Inc.
#								1785 E. Sahara Avenue, Suite 490-204
#								Las Vegas, Nevada 89104
#
# Licensed under The MIT License
# Redistributions of files must retain the above copyright notice.
# http://www.opensource.org/licenses/mit-license.php The MIT License

CREATE TABLE cake_sessions (
  id varchar(255) NOT NULL default '',
  data text,
  expires int(11) default NULL,
  PRIMARY KEY  (id)
);