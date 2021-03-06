#!/bin/bash
# -*- Mode: Shell-script; tab-width: 4; indent-tabs-mode: nil; -*-
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is mozilla.org code.
#
# The Initial Developer of the Original Code is
# Mozilla Corporation.
# Portions created by the Initial Developer are Copyright (C) 2006.
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Bob Clary <bob@bclary.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

if [[ -z "$LIBRARYSH" ]]; then
    source $TEST_DIR/bin/library.sh
fi

export MOZ_CVS_FLAGS="-z3 -q"
export MOZILLA_OFFICIAL=1
export BUILD_OFFICIAL=1

if [[ -z "$CVSROOT" ]]; then
    if grep -q buildbot@qm ~/.ssh/id_dsa.pub; then
        export CVSROOT=:ext:unittest@cvs.mozilla.org:/cvsroot
    else
        export CVSROOT=:pserver:anonymous@cvs-mirror.mozilla.org:/cvsroot
    fi
fi

#
# options processing
#
options="p:b:T:e:"
usage()
{
    cat <<EOF

usage: set-build-env.sh -p product -b branch -T buildtype [-e extra]

-p product      [firefox|thunderbird]
-b branch       [1.8.0|1.8.1|1.9.0|1.9.1]
-T buildtype    [opt|debug]
-e extra        extra qualifier to pick mozconfig and tree

EOF
}

myexit()
{
    myexit_status=$1

    case $0 in
        *bash*)
	        # prevent "sourced" script calls from 
            # exiting the current shell.
            break 99;;
        *)
            exit $myexit_status;;
    esac
}

for step in step1; do # dummy loop for handling exits

    unset product branch buildtype extra

    while getopts $options optname ; 
      do 
      case $optname in
          p) product=$OPTARG;;
          b) branch=$OPTARG;;
          T) buildtype=$OPTARG;;
          e) extra="-$OPTARG";;
      esac
    done

    # include environment variables
    datafiles=$TEST_DIR/data/$product,$branch$extra,$buildtype.data
    loaddata $datafiles

    # echo product=$product, branch=$branch, buildtype=$buildtype, extra=$extra

    if [[ -z "$product" || -z "$branch" || -z "$buildtype" ]]; then
        echo -n "missing"
        if [[ -z "$product" ]]; then
            echo -n " -p product"
        fi
        if [[ -z "$branch" ]]; then
            echo -n " -b branch"
        fi
        if [[ -z "$buildtype" ]]; then
            echo -n " -T buildtype"
        fi
        usage
        myexit 1
    fi

    if [[ $branch == "1.8.0" ]]; then
        export BRANCH_CO_FLAGS=${BRANCH_CO_FLAGS:--r MOZILLA_1_8_0_BRANCH}
    elif [[ $branch == "1.8.1" ]]; then
        export BRANCH_CO_FLAGS=${BRANCH_CO_FLAGS:--r MOZILLA_1_8_BRANCH}
    elif [[ $branch == "1.9.0" ]]; then
        export BRANCH_CO_FLAGS="";
    elif [[ $branch == "1.9.1" ]]; then
        # XXX: mozilla-central
        export BRANCH_CO_FLAGS="";
    else
        echo "Unknown branch: $branch"
        myexit 1
    fi

    if [[ -n "$MOZ_CO_DATE" ]]; then
        export DATE_CO_FLAGS="-D \"$MOZ_CO_DATE\""
    fi

    case $OSID in 
        nt)

            # On Windows, Sisyphus is run under Cygwin, so the OS will be CYGWIN
            # regardless. Check if mozilla-build has been installed to the default
            # location, and if so, set up to call mozilla-build to perform the actual
            # build steps.
            # 
            # To make life simpler, change the mount point of the C: drive in cygwin from
            # /cygdrive/c to /c via mount -c /
            # which will make paths to non cygwin and non msys locations identical between cygwin
            # and msys, e.g. /c/work will work in both to point to c:\work
            # 
            # Note that all commands *except* make client.mk will be performed in cygwin.
            #
            # Note that when calling a command string of the form $buildbash --login -c "command",
            # you must cd to the desired directory as part of "command" since msys will set the 
            # directory to the home directory prior to executing the command.

            if [[ -e "/c/mozilla-build" && $branch != "1.8.0" ]]; then
                export BUILDDIR=${BUILDDIR:-/c/work/mozilla/builds}
                export buildbash="/c/mozilla-build/msys/bin/bash"
                export bashlogin=--login # this is for msys' bash.

                if echo $branch | egrep -q '^1\.8'; then
                    export MOZ_TOOLS=${MOZ_TOOLS:-"/c/mozilla-build/moztools-180compat"}
                    export SET_MSVC_ENV=${SET_MSVC_ENV:-${TEST_DIR}/bin/set-msvc6-env.sh}
                else
                    export MOZ_TOOLS=${MOZ_TOOLS:-"/c/mozilla-build/moztools"}
                    export SET_MSVC_ENV=${SET_MSVC_ENV:-${TEST_DIR}/bin/set-msvc8-env.sh}
                fi

            else
                export BUILDDIR=${BUILDDIR:-/work/mozilla/builds}
                export buildbash="/bin/bash"
                export bashlogin=-l

                if echo $branch | egrep -q '^1\.8'; then
                    export MOZ_TOOLS=${MOZ_TOOLS:-"$BUILDDIR/moztools"}
                    export SET_MSVC_ENV=${SET_MSVC_ENV:-${TEST_DIR}/bin/set-msvc6-env.sh}
                else
                    export MOZ_TOOLS=${MOZ_TOOLS:-"$BUILDDIR/moztools-static"}
                    export SET_MSVC_ENV=${SET_MSVC_ENV:-${TEST_DIR}/bin/set-msvc8-env.sh}
                fi
            fi

            source $SET_MSVC_ENV
            echo moztools Location: $MOZ_TOOLS

            # now convert TEST_DIR and BUILDDIR to cross compatible paths using
            # the common cygdrive prefix for cygwin and msys
            TEST_DIR_WIN=`cygpath -w $TEST_DIR`
            BUILDDIR_WIN=`cygpath -w $BUILDDIR`
            TEST_DIR=`cygpath -u $TEST_DIR_WIN`
            BUILDDIR=`cygpath -u $BUILDDIR_WIN`
            ;;

        linux)
            export BUILDDIR=${BUILDDIR:-/work/mozilla/builds}
            export buildbash="/bin/bash"
            export bashlogin=-l

            # if a 64 bit linux system, assume the 
            # compiler is in the standard reference
            # location /tools/gcc/bin/
            case "$TEST_PROCESSORTYPE" in
                *64)
                    export PATH=/tools/gcc/bin:$PATH
                    ;;
            esac
            
            ;;
        darwin)
            export BUILDDIR=${BUILDDIR:-/work/mozilla/builds}
            export buildbash="/bin/bash"
            export bashlogin=-l
            ;;
        *)
            ;;
    esac

    export SHELL=$buildbash
    export CONFIG_SHELL=$buildbash
    export CONFIGURE_ENV_ARGS=$buildbash


    export TEST_MOZILLA_HG=${TEST_MOZILLA_HG:-http://hg.mozilla.org/mozilla-central/}
    export TEST_MOZILLA_HG_REV=${TEST_MOZILLA_HG_REV:-tip}

    if [[ -z $extra ]]; then
        export BUILDTREE="$BUILDDIR/$branch"
    else
        export BUILDTREE="$BUILDDIR/$branch$extra"

        #
        # extras can't be placed in mozconfigs since not all parts
        # of the build system use mozconfig (e.g. js shell) and since
        # the obj directory is not configurable for them as well thus
        # requiring separate source trees
        #

        case "$extra" in
            -too-much-gc)
                export XCFLAGS="-DWAY_TOO_MUCH_GC=1"
                export CFLAGS="-DWAY_TOO_MUCH_GC=1"
                export CXXFLAGS="-DWAY_TOO_MUCH_GC=1"
                ;;
            -gcov)

                if [[ "$OSID" == "nt" ]]; then
                    echo "NT does not support gcov"
                    myexit 1
                fi
                export CFLAGS="--coverage"
                export CXXFLAGS="--coverage"
                export XCFLAGS="--coverage"
                export OS_CFLAGS="--coverage"
                export LDFLAGS="--coverage"
                export XLDOPTS="--coverage"	
                ;;
            -jprof)
                ;;
        esac
    fi

    if [[ ! -d $BUILDTREE ]]; then
        echo "Build directory $BUILDTREE does not exist"
        myexit 2
    fi

    # here project refers to either browser or mail
    # and is used to find mozilla/(browser|mail)/config/mozconfig
    if [[ $product == "firefox" ]]; then
        project=browser
        export MOZCONFIG=${MOZCONFIG:-"$BUILDTREE/mozconfig-firefox-$OSID-$TEST_PROCESSORTYPE-$buildtype"}
    elif [[ $product == "thunderbird" ]]; then
        project=mail
        export MOZCONFIG=${MOZCONFIG:-"$BUILDTREE/mozconfig-thunderbird-$OSID-$TEST_PROCESSORTYPE-$buildtype"}
    else
        echo "Assuming project=browser for product: $product"
        project=browser
        export MOZCONFIG=${MOZCONFIG:-"$BUILDTREE/mozconfig-firefox-$OSID-$TEST_PROCESSORTYPE-$buildtype"}
    fi

    # js shell builds
    if [[ $buildtype == "debug" ]]; then
        unset BUILD_OPT
    else
        export BUILD_OPT=1
    fi

    case "$OSID" in
        darwin)
            export JS_EDITLINE=1 # required for mac
            ;;
    esac
    # end js shell builds

    set | sed 's/^/environment: /'
    echo "mozconfig: $MOZCONFIG"
    cat $MOZCONFIG | sed 's/^/mozconfig: /'
done

