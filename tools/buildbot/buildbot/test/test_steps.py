# -*- test-case-name: buildbot.test.test_steps -*-

# create the BuildStep with a fake .remote instance that logs the
# .callRemote invocations and compares them against the expected calls. Then
# the test harness should send statusUpdate() messages in with assorted
# data, eventually calling remote_complete(). Then we can verify that the
# Step's rc was correct, and that the status it was supposed to return
# matches.

# sometimes, .callRemote should raise an exception because of a stale
# reference. Sometimes it should errBack with an UnknownCommand failure.
# Or other failure.

# todo: test batched updates, by invoking remote_update(updates) instead of
# statusUpdate(update). Also involves interrupted builds.

import os

from twisted.trial import unittest
from twisted.internet import reactor, defer

from buildbot.sourcestamp import SourceStamp
from buildbot.process import buildstep, base, factory
from buildbot.buildslave import BuildSlave
from buildbot.steps import shell, source, python
from buildbot.status import builder
from buildbot.status.builder import SUCCESS, WARNINGS, FAILURE
from buildbot.test.runutils import RunMixin, rmtree
from buildbot.test.runutils import makeBuildStep, StepTester
from buildbot.slave import commands, registry


class MyShellCommand(shell.ShellCommand):
    started = False
    def runCommand(self, c):
        self.started = True
        self.rc = c
        return shell.ShellCommand.runCommand(self, c)

class FakeBuild:
    pass
class FakeBuilder:
    statusbag = None
    name = "fakebuilder"
class FakeSlaveBuilder:
    def getSlaveCommandVersion(self, command, oldversion=None):
        return "1.10"

class FakeRemote:
    def __init__(self):
        self.events = []
        self.remoteCalls = 0
        #self.callRemoteNotifier = None
    def callRemote(self, methname, *args):
        event = ["callRemote", methname, args]
        self.events.append(event)
##         if self.callRemoteNotifier:
##             reactor.callLater(0, self.callRemoteNotifier, event)
        self.remoteCalls += 1
        self.deferred = defer.Deferred()
        return self.deferred
    def notifyOnDisconnect(self, callback):
        pass
    def dontNotifyOnDisconnect(self, callback):
        pass


class BuildStep(unittest.TestCase):

    def setUp(self):
        rmtree("test_steps")
        self.builder = FakeBuilder()
        self.builder_status = builder.BuilderStatus("fakebuilder")
        self.builder_status.basedir = "test_steps"
        self.builder_status.nextBuildNumber = 0
        os.mkdir(self.builder_status.basedir)
        self.build_status = self.builder_status.newBuild()
        req = base.BuildRequest("reason", SourceStamp())
        self.build = base.Build([req])
        self.build.build_status = self.build_status # fake it
        self.build.builder = self.builder
        self.build.slavebuilder = FakeSlaveBuilder()
        self.remote = FakeRemote()
        self.finished = 0

    def callback(self, results):
        self.failed = 0
        self.failure = None
        self.results = results
        self.finished = 1
    def errback(self, failure):
        self.failed = 1
        self.failure = failure
        self.results = None
        self.finished = 1

    def testShellCommand1(self):
        cmd = "argle bargle"
        dir = "murkle"
        self.expectedEvents = []
        buildstep.RemoteCommand.commandCounter[0] = 3
        c = MyShellCommand(workdir=dir, command=cmd, timeout=10)
        c.setBuild(self.build)
        c.setBuildSlave(BuildSlave("name", "password"))
        self.assertEqual(self.remote.events, self.expectedEvents)
        c.step_status = self.build_status.addStepWithName("myshellcommand")
        d = c.startStep(self.remote)
        self.failUnless(c.started)
        d.addCallbacks(self.callback, self.errback)
        d2 = self.poll()
        d2.addCallback(self._testShellCommand1_2, c)
        return d2
    testShellCommand1.timeout = 10

    def poll(self, ignored=None):
        # TODO: This is gross, but at least it's no longer using
        # reactor.iterate() . Still, get rid of this some day soon.
        if self.remote.remoteCalls == 0:
            d = defer.Deferred()
            d.addCallback(self.poll)
            reactor.callLater(0.1, d.callback, None)
            return d
        return defer.succeed(None)

    def _testShellCommand1_2(self, res, c):
        rc = c.rc
        self.expectedEvents.append(["callRemote", "startCommand",
                               (rc, "3",
                               "shell",
                                {'command': "argle bargle",
                                 'workdir': "murkle",
                                 'want_stdout': 1,
                                 'want_stderr': 1,
                                 'logfiles': {},
                                 'timeout': 10,
                                 'env': None}) ] )
        self.assertEqual(self.remote.events, self.expectedEvents)

        # we could do self.remote.deferred.errback(UnknownCommand) here. We
        # could also do .callback(), but generally the master end silently
        # ignores the slave's ack

        logs = c.step_status.getLogs()
        for log in logs:
            if log.getName() == "log":
                break

        rc.remoteUpdate({'header':
                         "command 'argle bargle' in dir 'murkle'\n\n"})
        rc.remoteUpdate({'stdout': "foo\n"})
        self.assertEqual(log.getText(), "foo\n")
        self.assertEqual(log.getTextWithHeaders(),
                         "command 'argle bargle' in dir 'murkle'\n\n"
                         "foo\n")
        rc.remoteUpdate({'stderr': "bar\n"})
        self.assertEqual(log.getText(), "foo\nbar\n")
        self.assertEqual(log.getTextWithHeaders(),
                         "command 'argle bargle' in dir 'murkle'\n\n"
                         "foo\nbar\n")
        rc.remoteUpdate({'rc': 0})
        self.assertEqual(rc.rc, 0)
        
        rc.remote_complete()
        # that should fire the Deferred
        d = self.poll2()
        d.addCallback(self._testShellCommand1_3)
        return d

    def poll2(self, ignored=None):
        if not self.finished:
            d = defer.Deferred()
            d.addCallback(self.poll2)
            reactor.callLater(0.1, d.callback, None)
            return d
        return defer.succeed(None)

    def _testShellCommand1_3(self, res):
        self.assertEqual(self.failed, 0)
        self.assertEqual(self.results, 0)


class MyObserver(buildstep.LogObserver):
    out = ""
    def outReceived(self, data):
        self.out = self.out + data

class Steps(unittest.TestCase):
    def testMultipleStepInstances(self):
        steps = [
            (source.CVS, {'cvsroot': "root", 'cvsmodule': "module"}),
            (shell.Configure, {'command': "./configure"}),
            (shell.Compile, {'command': "make"}),
            (shell.Compile, {'command': "make more"}),
            (shell.Compile, {'command': "make evenmore"}),
            (shell.Test, {'command': "make test"}),
            (shell.Test, {'command': "make testharder"}),
            ]
        f = factory.ConfigurableBuildFactory(steps)
        req = base.BuildRequest("reason", SourceStamp())
        b = f.newBuild([req])
        #for s in b.steps: print s.name

    def failUnlessClones(self, s1, attrnames):
        f1 = s1.getStepFactory()
        f,args = f1
        s2 = f(**args)
        for name in attrnames:
            self.failUnlessEqual(getattr(s1, name), getattr(s2, name))

    def clone(self, s1):
        f1 = s1.getStepFactory()
        f,args = f1
        s2 = f(**args)
        return s2

    def testClone(self):
        s1 = shell.ShellCommand(command=["make", "test"],
                                timeout=1234,
                                workdir="here",
                                description="yo",
                                descriptionDone="yoyo",
                                env={'key': 'value'},
                                want_stdout=False,
                                want_stderr=False,
                                logfiles={"name": "filename"},
                               )
        shellparms = (buildstep.BuildStep.parms +
                      ("remote_kwargs description descriptionDone "
                       "command logfiles").split() )
        self.failUnlessClones(s1, shellparms)


    # test the various methods available to buildsteps

    def test_getProperty(self):
        s = makeBuildStep("test_steps.Steps.test_getProperty")
        bs = s.step_status.getBuild()

        s.setProperty("prop1", "value1")
        s.setProperty("prop2", "value2")
        self.failUnlessEqual(s.getProperty("prop1"), "value1")
        self.failUnlessEqual(bs.getProperty("prop1"), "value1")
        self.failUnlessEqual(s.getProperty("prop2"), "value2")
        self.failUnlessEqual(bs.getProperty("prop2"), "value2")
        s.setProperty("prop1", "value1a")
        self.failUnlessEqual(s.getProperty("prop1"), "value1a")
        self.failUnlessEqual(bs.getProperty("prop1"), "value1a")


    def test_addURL(self):
        s = makeBuildStep("test_steps.Steps.test_addURL")
        s.addURL("coverage", "http://coverage.example.org/target")
        s.addURL("icon", "http://coverage.example.org/icon.png")
        bs = s.step_status
        links = bs.getURLs()
        expected = {"coverage": "http://coverage.example.org/target",
                    "icon": "http://coverage.example.org/icon.png",
                    }
        self.failUnlessEqual(links, expected)

    def test_addLog(self):
        s = makeBuildStep("test_steps.Steps.test_addLog")
        l = s.addLog("newlog")
        l.addStdout("some stdout here")
        l.finish()
        bs = s.step_status
        logs = bs.getLogs()
        self.failUnlessEqual(len(logs), 1)
        l1 = logs[0]
        self.failUnlessEqual(l1.getText(), "some stdout here")
        l1a = s.getLog("newlog")
        self.failUnlessEqual(l1a.getText(), "some stdout here")

    def test_addHTMLLog(self):
        s = makeBuildStep("test_steps.Steps.test_addHTMLLog")
        l = s.addHTMLLog("newlog", "some html here")
        bs = s.step_status
        logs = bs.getLogs()
        self.failUnlessEqual(len(logs), 1)
        l1 = logs[0]
        self.failUnless(isinstance(l1, builder.HTMLLogFile))
        self.failUnlessEqual(l1.getText(), "some html here")

    def test_addCompleteLog(self):
        s = makeBuildStep("test_steps.Steps.test_addCompleteLog")
        l = s.addCompleteLog("newlog", "some stdout here")
        bs = s.step_status
        logs = bs.getLogs()
        self.failUnlessEqual(len(logs), 1)
        l1 = logs[0]
        self.failUnlessEqual(l1.getText(), "some stdout here")
        l1a = s.getLog("newlog")
        self.failUnlessEqual(l1a.getText(), "some stdout here")

    def test_addLogObserver(self):
        s = makeBuildStep("test_steps.Steps.test_addLogObserver")
        bss = s.step_status
        o1,o2,o3 = MyObserver(), MyObserver(), MyObserver()

        # add the log before the observer
        l1 = s.addLog("one")
        l1.addStdout("onestuff")
        s.addLogObserver("one", o1)
        self.failUnlessEqual(o1.out, "onestuff")
        l1.addStdout(" morestuff")
        self.failUnlessEqual(o1.out, "onestuff morestuff")

        # add the observer before the log
        s.addLogObserver("two", o2)
        l2 = s.addLog("two")
        l2.addStdout("twostuff")
        self.failUnlessEqual(o2.out, "twostuff")

    # test more stuff about ShellCommands

    def test_description(self):
        s = makeBuildStep("test_steps.Steps.test_description.1",
                          step_class=shell.ShellCommand,
                          workdir="dummy",
                          description=["list", "of", "strings"],
                          descriptionDone=["another", "list"])
        self.failUnlessEqual(s.description, ["list", "of", "strings"])
        self.failUnlessEqual(s.descriptionDone, ["another", "list"])

        s = makeBuildStep("test_steps.Steps.test_description.2",
                          step_class=shell.ShellCommand,
                          workdir="dummy",
                          description="single string",
                          descriptionDone="another string")
        self.failUnlessEqual(s.description, ["single string"])
        self.failUnlessEqual(s.descriptionDone, ["another string"])

class VersionCheckingStep(buildstep.BuildStep):
    def start(self):
        # give our test a chance to run. It is non-trivial for a buildstep to
        # claw its way back out to the test case which is currently running.
        master = self.build.builder.botmaster.parent
        checker = master._checker
        checker(self)
        # then complete
        self.finished(buildstep.SUCCESS)

version_config = """
from buildbot.process import factory
from buildbot.test.test_steps import VersionCheckingStep
from buildbot.buildslave import BuildSlave
BuildmasterConfig = c = {}
f1 = factory.BuildFactory([
    factory.s(VersionCheckingStep),
    ])
c['slaves'] = [BuildSlave('bot1', 'sekrit')]
c['schedulers'] = []
c['builders'] = [{'name':'quick', 'slavename':'bot1',
                  'builddir': 'quickdir', 'factory': f1}]
c['slavePortnum'] = 0
"""

class SlaveVersion(RunMixin, unittest.TestCase):
    def setUp(self):
        RunMixin.setUp(self)
        self.master.loadConfig(version_config)
        self.master.startService()
        d = self.connectSlave(["quick"])
        return d

    def doBuild(self, buildername):
        br = base.BuildRequest("forced", SourceStamp())
        d = br.waitUntilFinished()
        self.control.getBuilder(buildername).requestBuild(br)
        return d


    def checkCompare(self, s):
        cver = commands.command_version
        v = s.slaveVersion("svn", None)
        # this insures that we are getting the version correctly
        self.failUnlessEqual(s.slaveVersion("svn", None), cver)
        # and that non-existent commands do not provide a version
        self.failUnlessEqual(s.slaveVersion("NOSUCHCOMMAND"), None)
        # TODO: verify that a <=0.5.0 buildslave (which does not implement
        # remote_getCommands) handles oldversion= properly. This requires a
        # mutant slave which does not offer that method.
        #self.failUnlessEqual(s.slaveVersion("NOSUCHCOMMAND", "old"), "old")

        # now check the comparison functions
        self.failIf(s.slaveVersionIsOlderThan("svn", cver))
        self.failIf(s.slaveVersionIsOlderThan("svn", "1.1"))
        self.failUnless(s.slaveVersionIsOlderThan("svn", cver + ".1"))

        self.failUnlessEqual(s.getSlaveName(), "bot1")

    def testCompare(self):
        self.master._checker = self.checkCompare
        d = self.doBuild("quick")
        return d


class _SimpleBuildStep(buildstep.BuildStep):
    def start(self):
        args = {"arg1": "value"}
        cmd = buildstep.RemoteCommand("simple", args)
        d = self.runCommand(cmd)
        d.addCallback(lambda res: self.finished(SUCCESS))

class _SimpleCommand(commands.Command):
    def start(self):
        self.builder.flag = True
        self.builder.flag_args = self.args
        return defer.succeed(None)

class CheckStepTester(StepTester, unittest.TestCase):
    def testSimple(self):
        self.slavebase = "testSimple.slave"
        self.masterbase = "testSimple.master"
        sb = self.makeSlaveBuilder()
        sb.flag = False
        registry.registerSlaveCommand("simple", _SimpleCommand, "1")
        step = self.makeStep(_SimpleBuildStep)
        d = self.runStep(step)
        def _checkSimple(results):
            self.failUnless(sb.flag)
            self.failUnlessEqual(sb.flag_args, {"arg1": "value"})
        d.addCallback(_checkSimple)
        return d

class Python(StepTester, unittest.TestCase):
    def testPyFlakes1(self):
        self.masterbase = "Python.testPyFlakes1"
        step = self.makeStep(python.PyFlakes)
        output = \
"""pyflakes buildbot
buildbot/changes/freshcvsmail.py:5: 'FCMaildirSource' imported but unused
buildbot/clients/debug.py:9: redefinition of unused 'gtk' from line 9
buildbot/clients/debug.py:9: 'gnome' imported but unused
buildbot/scripts/runner.py:323: redefinition of unused 'run' from line 321
buildbot/scripts/runner.py:325: redefinition of unused 'run' from line 323
buildbot/scripts/imaginary.py:12: undefined name 'size'
buildbot/scripts/imaginary.py:18: 'from buildbot import *' used; unable to detect undefined names
"""
        log = step.addLog("stdio")
        log.addStdout(output)
        log.finish()
        step.createSummary(log)
        desc = step.descriptionDone
        self.failUnless("unused=2" in desc)
        self.failUnless("undefined=1" in desc)
        self.failUnless("redefs=3" in desc)
        self.failUnless("import*=1" in desc)
        self.failIf("misc=" in desc)

        self.failUnlessEqual(step.getProperty("pyflakes-unused"), 2)
        self.failUnlessEqual(step.getProperty("pyflakes-undefined"), 1)
        self.failUnlessEqual(step.getProperty("pyflakes-redefs"), 3)
        self.failUnlessEqual(step.getProperty("pyflakes-import*"), 1)
        self.failUnlessEqual(step.getProperty("pyflakes-misc"), 0)
        self.failUnlessEqual(step.getProperty("pyflakes-total"), 7)

        logs = {}
        for log in step.step_status.getLogs():
            logs[log.getName()] = log

        for name in ["unused", "undefined", "redefs", "import*"]:
            self.failUnless(name in logs)
        self.failIf("misc" in logs)
        lines = logs["unused"].readlines()
        self.failUnlessEqual(len(lines), 2)
        self.failUnlessEqual(lines[0], "buildbot/changes/freshcvsmail.py:5: 'FCMaildirSource' imported but unused\n")

        cmd = buildstep.RemoteCommand(None, {})
        cmd.rc = 0
        results = step.evaluateCommand(cmd)
        self.failUnlessEqual(results, FAILURE) # because of the 'undefined'

    def testPyFlakes2(self):
        self.masterbase = "Python.testPyFlakes2"
        step = self.makeStep(python.PyFlakes)
        output = \
"""pyflakes buildbot
some more text here that should be ignored
buildbot/changes/freshcvsmail.py:5: 'FCMaildirSource' imported but unused
buildbot/clients/debug.py:9: redefinition of unused 'gtk' from line 9
buildbot/clients/debug.py:9: 'gnome' imported but unused
buildbot/scripts/runner.py:323: redefinition of unused 'run' from line 321
buildbot/scripts/runner.py:325: redefinition of unused 'run' from line 323
buildbot/scripts/imaginary.py:12: undefined name 'size'
could not compile 'blah/blah.py':3:
pretend there was an invalid line here
buildbot/scripts/imaginary.py:18: 'from buildbot import *' used; unable to detect undefined names
"""
        log = step.addLog("stdio")
        log.addStdout(output)
        log.finish()
        step.createSummary(log)
        desc = step.descriptionDone
        self.failUnless("unused=2" in desc)
        self.failUnless("undefined=1" in desc)
        self.failUnless("redefs=3" in desc)
        self.failUnless("import*=1" in desc)
        self.failUnless("misc=2" in desc)


    def testPyFlakes3(self):
        self.masterbase = "Python.testPyFlakes3"
        step = self.makeStep(python.PyFlakes)
        output = \
"""buildbot/changes/freshcvsmail.py:5: 'FCMaildirSource' imported but unused
buildbot/clients/debug.py:9: redefinition of unused 'gtk' from line 9
buildbot/clients/debug.py:9: 'gnome' imported but unused
buildbot/scripts/runner.py:323: redefinition of unused 'run' from line 321
buildbot/scripts/runner.py:325: redefinition of unused 'run' from line 323
buildbot/scripts/imaginary.py:12: undefined name 'size'
buildbot/scripts/imaginary.py:18: 'from buildbot import *' used; unable to detect undefined names
"""
        log = step.addLog("stdio")
        log.addStdout(output)
        log.finish()
        step.createSummary(log)
        desc = step.descriptionDone
        self.failUnless("unused=2" in desc)
        self.failUnless("undefined=1" in desc)
        self.failUnless("redefs=3" in desc)
        self.failUnless("import*=1" in desc)
        self.failIf("misc" in desc)


class OrdinaryCompile(shell.Compile):
    warningPattern = "ordinary line"

class Warnings(StepTester, unittest.TestCase):
    def testCompile1(self):
        self.masterbase = "Warnings.testCompile1"
        step = self.makeStep(shell.Compile)
        output = \
"""Compile started
normal line
warning: oh noes!
ordinary line
error (but we aren't looking for errors now, are we)
line 23: warning: we are now on line 23
ending line
"""
        log = step.addLog("stdio")
        log.addStdout(output)
        log.finish()
        step.createSummary(log)
        self.failUnlessEqual(step.getProperty("warnings-count"), 2)
        logs = {}
        for log in step.step_status.getLogs():
            logs[log.getName()] = log
        self.failUnless("warnings" in logs)
        lines = logs["warnings"].readlines()
        self.failUnlessEqual(len(lines), 2)
        self.failUnlessEqual(lines[0], "warning: oh noes!\n")
        self.failUnlessEqual(lines[1],
                             "line 23: warning: we are now on line 23\n")

        cmd = buildstep.RemoteCommand(None, {})
        cmd.rc = 0
        results = step.evaluateCommand(cmd)
        self.failUnlessEqual(results, WARNINGS)

    def testCompile2(self):
        self.masterbase = "Warnings.testCompile2"
        step = self.makeStep(shell.Compile, warningPattern="ordinary line")
        output = \
"""Compile started
normal line
warning: oh noes!
ordinary line
error (but we aren't looking for errors now, are we)
line 23: warning: we are now on line 23
ending line
"""
        log = step.addLog("stdio")
        log.addStdout(output)
        log.finish()
        step.createSummary(log)
        self.failUnlessEqual(step.getProperty("warnings-count"), 1)
        logs = {}
        for log in step.step_status.getLogs():
            logs[log.getName()] = log
        self.failUnless("warnings" in logs)
        lines = logs["warnings"].readlines()
        self.failUnlessEqual(len(lines), 1)
        self.failUnlessEqual(lines[0], "ordinary line\n")

        cmd = buildstep.RemoteCommand(None, {})
        cmd.rc = 0
        results = step.evaluateCommand(cmd)
        self.failUnlessEqual(results, WARNINGS)

    def testCompile3(self):
        self.masterbase = "Warnings.testCompile3"
        step = self.makeStep(OrdinaryCompile)
        output = \
"""Compile started
normal line
warning: oh noes!
ordinary line
error (but we aren't looking for errors now, are we)
line 23: warning: we are now on line 23
ending line
"""
        step.setProperty("warnings-count", 10)
        log = step.addLog("stdio")
        log.addStdout(output)
        log.finish()
        step.createSummary(log)
        self.failUnlessEqual(step.getProperty("warnings-count"), 11)
        logs = {}
        for log in step.step_status.getLogs():
            logs[log.getName()] = log
        self.failUnless("warnings" in logs)
        lines = logs["warnings"].readlines()
        self.failUnlessEqual(len(lines), 1)
        self.failUnlessEqual(lines[0], "ordinary line\n")

        cmd = buildstep.RemoteCommand(None, {})
        cmd.rc = 0
        results = step.evaluateCommand(cmd)
        self.failUnlessEqual(results, WARNINGS)


class TreeSize(StepTester, unittest.TestCase):
    def testTreeSize(self):
        self.slavebase = "TreeSize.testTreeSize.slave"
        self.masterbase = "TreeSize.testTreeSize.master"

        sb = self.makeSlaveBuilder()
        step = self.makeStep(shell.TreeSize)
        d = self.runStep(step)
        def _check(results):
            self.failUnlessEqual(results, SUCCESS)
            kib = step.getProperty("tree-size-KiB")
            self.failUnless(isinstance(kib, int))
            self.failUnless(kib < 100) # should be empty, I get '4'
            s = step.step_status
            self.failUnlessEqual(" ".join(s.getText()),
                                 "treesize %d KiB" % kib)
        d.addCallback(_check)
        return d
