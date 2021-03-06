# -*- Mode: perl; tab-width: 4; indent-tabs-mode: nil; -*-
#
# This file is MPL/GPL dual-licensed under the following terms:
#
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
# the License for the specific language governing rights and
# limitations under the License.
#
# The Original Code is PLIF 1.0.
# The Initial Developer of the Original Code is Ian Hickson.
#
# Alternatively, the contents of this file may be used under the terms
# of the GNU General Public License Version 2 or later (the "GPL"), in
# which case the provisions of the GPL are applicable instead of those
# above. If you wish to allow use of your version of this file only
# under the terms of the GPL and not to allow others to use your
# version of this file under the MPL, indicate your decision by
# deleting the provisions above and replace them with the notice and
# other provisions required by the GPL. If you do not delete the
# provisions above, a recipient may use your version of this file
# under either the MPL or the GPL.

package PLIF::Output::Generic;
use strict;
use vars qw(@ISA);
use PLIF::Output;
@ISA = qw(PLIF::Output);
1;

# NOTES
#
# The codepath resulting from a call through PLIF::Output::Generic are
# somewhat involved, although they make for a very flexible and
# powerful potential result.
#
# In the logic code, you simply have to call the output method without
# worrying about anything:
#
#     $app->output->HelloWorld($fullname, $date);
#
# ...or whatever. However this ends up following the following
# codepath:
#
# First, the PLIF internal program logic (Program.pm) looks for a
# specific output handler for the protocol (we'll assume we're using
# HTTP here). This will typically fail.
#
# Then it looks for a generic output handler (probably this module).
#
# It calls the generic output module's 'HelloWorld' method, which in
# this case doesn't exist and ends up going through core PLIF and then
# back to implyMethod implemented in this module and the ancestor
# Output module.
#
# The implyMethod methods first call every output dispatcher service
# for the actual protocol (HTTP in this case) and then every output
# dispatcher service for the generic protocol until one of them
# handles the HelloWorld method.
#
# This ends up calling HelloWorld on one of the output dispatchers,
# which should result in calling the 'output' method of this object
# (defined below) with a string name and a hash.
#
# The output method now fetches the string and related metadata from
# the string data source which calls the default database which calls
# the configuration data source which calls the configuration file
# database which looks up the name of the database, which is used to
# look up the list of variants and the specific string which should be
# used from those variants. If that fails, then the string data source
# will just return a "nope, sorry, not me" response.
#
# If that happens, then the output method instead asks the default
# string datasources.
#
# The output method then calls for an appropriate string expander
# service, passes it the string and the data hash, and waits for
# another string in return.
#
# The string expander typically passes this string to an XML service
# (which typically calls expat) to get it parsed and then handles it
# as appropriate to get some string output.
#
# The resulting string is then passed to any output filter objects for
# postprocessing.
#
# The output method then looks for a protocol outputter and passes it
# the final string.
#
# The stack then unwinds all the way back to the application logic.
#
# Phew! Bet you never thought writing "Hello World" would be that
# hard. But at least this means we can do it in HTML and SVG without
# changing the underlying code.

# To find the list of strings required, do this:
#    my %strings = @{$app->getCollectingServiceList('dispatcher.output')->strings};

sub provides {
    my $class = shift;
    my($service) = @_;
    return ($service eq 'dataSource.strings' or
            $service eq 'dispatcher.commands' or
            $service eq 'dispatcher.output.generic' or 
            $class->SUPER::provides($service));
}

sub protocol {
    return 'generic';
}

__DATA__

sub serviceInstanceInit {
    my $self = shift;
    $self->SUPER::serviceInstanceInit(@_);
    my($app, $session, $protocol) = @_;
    $self->{actualSession} = $session;
    $self->{actualProtocol} = $protocol;
}

# output.generic service instance method
sub output {
    my $self = shift;
    my($string, $data, $session) = @_;
    $self->dump(9, "outputting string '$string' on protocol '". ($self->{actualProtocol}) .'\'');
    if (not defined($self->{outputter})) {
        $self->{outputter} = $self->{app}->getService("output.generic.$self->{actualProtocol}");
    }
    $self->{outputter}->output($self->getOutput($string, $data, $session));
}

# output.generic service instance method
# same as output, but don't actually output.
# returns a hash with data about the output.
# you want $output->{'string'}
sub getOutput {
    my $self = shift;
    my($string, $data, $session) = @_;
    if (not defined($session)) {
        $session = $self->{actualSession};
    }
    $self->fillData($data);
    my $outputArgs = {
        'app' => $self->{app},
        'session' => $session,
        'protocol' => $self->{actualProtocol},
        'name' => $string,
        'data' => $data,
    };
    # for efficiency, we modify $outputArgs in place:
    if ($self->getExpandedString($outputArgs)) {
        $self->error("Failed to output string '$outputArgs->{'name'}'");
    }
    foreach my $filter ($self->{app}->getObjectList('output.filter')) {
        $string = $filter->filterOutput($outputArgs);
    }
    return $outputArgs;
}

# output.generic service instance method
# If we don't implement the output handler directly, let's see if some
# specific output dispatcher service for this protocol does.
# Note: We pass ourselves as the 'output object for this protocol'
# even though this is actually the generic output handler, because
# there _is_ no 'output object for this protocol' since if there was
# the generic output module wouldn't get called!
sub implyMethod {
    my $self = shift;
    my($method, @arguments) = @_;
    if (not $self->{app}->dispatchMethod('dispatcher.output.'.$self->{actualProtocol}, 'output', $method, $self, @arguments)) {
        # ok, no generic output dispatcher for the actual protocol, let's try the generic protocol
        if (not $self->{app}->dispatchMethod('dispatcher.output.'.$self->protocol, 'output', $method, $self, @arguments)) {
            # nope, so let's do our own.
            # this assumes the string will be the same as the output
            # method and that the arguments will be all in 'data'.
            $self->output($method, { 'data' => \@arguments });
        }
    }
}

# output.generic service instance method
sub fillData {
    my $self = shift;
    my($data) = @_;
    $data->{'app'} = $self->{app}->hash;
    if (defined($self->{actualSession})) {
        $data->{'session'} = $self->{actualSession}->hash;
    }
    $data->{'input'} = $self->{app}->input->hash;
    $data->{'output'} = $self->{outputter}->hash;
}

# dataSource.strings default implementation
sub getString {
    my $self = shift;
    my($args) = @_;
    $args->{'app'}->getSelectingServiceList('dataSource.strings.customised')->getCustomisedString($args);
    if (not defined $args->{'string'}) {
        $args->{'app'}->getSelectingServiceList('dataSource.strings.default')->getDefaultString($args);
        $self->assert(defined $args->{'string'}, 1, "No suitable '$args->{'name'}' string available for the '$args->{'protocol'}' protocol");
    }
    return 1 if (not defined $args->{'string'});
    return;
}

# dataSource.strings default implementation
sub expandString {
    my $self = shift;
    my($args) = @_;
    my $expander = $args->{'app'}->getService("string.expander.$args->{'type'}");
    $self->assert($expander, 1, "Could not find a string expander for string '$args->{'name'}' of type '$args->{'type'}'");
    $expander->expand($args);
}

# dataSource.strings default implementation
sub getExpandedString {
    my $self = shift;
    my($args) = @_;
    $self->getString($args);
    return 1 if (not defined $args->{'string'});
    $self->expandString($args);
    return 1 if (not defined $args->{'string'});
    return;
}

# dispatcher.commands
sub cmdShowTemplate {
    my $self = shift;
    my($app) = @_;
    my $string = $app->input->getArgument('string');
    $app->output->showTemplate($string);
}

# dispatcher.output.generic
sub outputShowTemplate {
    my $self = shift;
    my($app, $output, $string) = @_;
    $output->output($string, {});
}
