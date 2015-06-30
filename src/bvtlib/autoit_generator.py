#
# Copyright (c) 2013 Citrix Systems, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

"""Generate autoit file for windows GUI automation"""
from src.bvtlib.call_exec_daemon import run_via_exec_daemon, call_exec_daemon

class Window:
    def __init__(self, window_name, children):
        self.window_name = window_name
        self.children = children
    def gen(self, ancestors=[]):
        return ('\t\tCase WinExists("%s")\n%s' % (self.window_name,
                ''.join(child.gen(ancestors+[self]) for child in \
                            self.children)))
    
class Match:
    def __init__(self, text_substring, actions):
        self.text_substring = text_substring
        self.actions = actions
    def gen(self, ancestors=[]):
        window_name = ancestors[-1].window_name
        child = '\n'.join( x.gen(ancestors+[self]) for x in self.actions)
        return ('\t\t\tIf StringLeft(WinGetText("%s"), %d) ="%s" Then\n'
                '%s\n\t\t\tEndIf\n') % (window_name,
                                      len(self.text_substring),self.text_substring,child)


class KeySend:
    def __init__(self, keystrokes):
        self.keystrokes = keystrokes
    def gen(self, ancestors=[]):
        return '\t\t\tSend("%s")\n' % self.keystrokes

class Click:
    def __init__(self, control_id, coordinates=None, n=1):
        self.control_id = control_id
        self.coordinates = coordinates
        self.n = n
    def gen(self, ancestors=[]):
        assert len(ancestors)>=2
        assert hasattr(ancestors[-2], 'window_name')
        if self.coordinates is not None: 
            ex = ', "left", %d, %d, %d' % (self.n, self.coordinates[0], self.coordinates[1])
        else: ex = ''
        return '\t\t\t\tControlClick("%s", "", %d%s)' % (ancestors[-2].window_name,
                                                         self.control_id, ex)

class Log:
    def __init__(self, text, control_id=None):
        self.text = text
        self.control_id = control_id
    def gen(self, ancestors):
        pname = ancestors[-2].window_name
        ex = str(int(self.control_id)) if self.control_id is not None else ''
        return '\t\t\t\tRecordLogEntry("%s %s"%s)' % (
            pname, self.text, (' & ControlGetText("'+pname+'", "", '+ex+')') if 
            self.control_id is not None else '')

class LogWin:
    def __init__(self, text):
        self.text = text
    def gen(self, ancestors):
        pname = ancestors[-2].window_name
        return '\t\t\t\tRecordLogEntry("%s %s"%s)' % (
            pname, self.text, (' & WinGetText("'+pname+'")'))

class Code:
    def __init__(self, code): self.code=code
    def gen(self, _): return self.code
class Collection:
    def __init__(self, nodes, state=1): 
        self.nodes = nodes
        self.state = state
    def gen(self, _): 
        pre = ("While $state=%d\n"
               "\tSelect\n" % (self.state))
        post = '\tEndSelect\nSleep(100)\nWEnd\n'
        return (pre+''.join(node.gen([self]) for node in self.nodes)+post).replace(
            '\n','\r\n')

class SetState:
    def __init__(self, state): self.state = state
    def gen(self, _): return '\t\t$State=%d' % (self.state)

class Run:
    def __init__(self, command): self.command = command
    def gen(self, _): return 'ShellExecute("%s","","open")' % (self.command)

class Sleep:
    def __init__(self, milliseconds): self.milliseconds = milliseconds
    def gen(self, _): return '\tSleep(%d)' % (self.milliseconds)

class Program:
    def __init__(self, nodes): self.nodes = nodes
    def gen(self): 
        pre = ('AutoItSetOption("ExpandEnvStrings",1)\n'
               'Dim $Count = 0\n'
               'Dim $State = 1\n'
               'Func RecordLogEntry($message)\n'
                '\tFileWrite("C:/driverinstalllog.txt", $Count & " " & $message & @CRLF)\n'
               '\t$Count = $Count + 1\n'
               'EndFunc\n')
        return (pre+''.join((node.gen([self])+'\n') for node in self.nodes)).replace(
            '\n','\r\n')

hardware_installation =  Window("Hardware Installation", [Match(
            'The software you are installing for this hardware:',
            [Log('warning', 5302), Click(5303)])])
software_installation = Window("Software Installation", [
        Match("The software you are installing has not passed Win", [
                Log("UAC warning", 5302), Click(5303)])])
found_new_hardware = Window("Found New Hardware Wizard", [
        Match("Welcome to the Found New Hardware Wizard", 
              [Log("started"), Click(8105), Click(12324)]),
        Match("Cannot Install this Hardware",
              [Log("cannot install"), Click(12325)]),
        Match("This wizard helps you install software for:",
              [Log("wizard", 1048), Click(12324)]),
        Match("Completing the Found New Hardware Wizard",
              [Log("completed"), Click(12325)])])
hardware_update_wizard = Window("Hardware Update Wizard", [
        Match("Welcome to the Hardware Update Wizard",
              [Log("started"), Click(8105), Click(12324)]),
        Match("This wizard helps you install software for:",
              [Log("found", 1048), Click(12324)]),
        Match("Cannot Continue the Hardware Update Wizard",
              [LogWin("cannot continue the hardware update wizard. Error: "),Click(12325)]),
        Match("Cannot Start this Hardware",
              [LogWin("Cannot start this hardware: "), Click(12325)]),
        Match("Completing the Hardware Update Wizard",
              [LogWin("Completing the hardware update ziard: "), Click(12325)])])
tools_setup_matchers = [
        Match("WixUI_Bmp", [Log('seen splash'), Click(512), Click(490)]),
        Match("&Finish", [Log('seen splash finish'), Click(432)]),
        Match("&Yes", [Log('seen splash restart'), Click(24)]),
        ]
tools_setup_splash = Window('Citrix XenClient Tools Setup', tools_setup_matchers)
microsoft_windows = Window("Microsoft Windows", [Code("""
	 $Text=WinGetText("Microsoft Windows")
	 RecordLogEntry("Microsoft Windows window found")

	 if StringInStr($Text, "Restart Now") <> 0 Then
		RecordLogEntry("Restart prompt found")
		ControlClick("Microsoft Windows", "", "[CLASS:Button; INSTANCE:1]")
		RecordLogEntry("Clicked on restart button")
	 EndIf
""")])
windows_security = Window("Windows Security", [Code("""
			$Text = WinGetText("Windows Security")
			ControlClick("Windows Security", "", "[CLASS:Button; INSTANCE:1]")
			RecordLogEntry("Clicking on Windows Security button 1")
""")])

install_tools_recognisers = [hardware_installation, software_installation,
                             found_new_hardware, hardware_update_wizard, microsoft_windows,
                             windows_security, tools_setup_splash]

install_tools_script = Program([Collection(install_tools_recognisers)]).gen()

select_input_device = Window("Regional and Language Options", [
        Match("Regional Options", [Click(12320, (136, 13))]),
        Match("Languages", [Click(1172), SetState(2)])])
remove_first_keyboard = Window("Text Services and Input Languages", [
    Match("Settings", [Click(1104, coordinates=(125,8), n=2), 
                       Sleep(500),
                       Click(1206),
                       Sleep(500),
                       Click(1), 
                       Sleep(500),
                       SetState(3)])])
close_up = Window("Regional and Language Options", [
        Match("Languages", [Click(1), SetState(4)])])
        
set_keyboard_layout = Program([Run("C:\\WINDOWS\\system32\\intl.cpl"),
                               Collection([select_input_device], state=1),
                               Collection([remove_first_keyboard], state=2),
                               Collection([close_up], state=3)
                               ]).gen()


def compile(vm_address, name, program):
    """Generate an EXE on vm_address"""
    target_file = 'C:\\install\\'+name+'.au3'    
    call_exec_daemon('unpackTarball', 
                     ['http://autotest.cam.xci-test.com/bin/autoit.tar.gz',
                      'C:\\'], host=vm_address)
    run_via_exec_daemon(['del', target_file], timeout=600, host=vm_address)
    call_exec_daemon('createFile', [target_file, program], host=vm_address)
    target_exe  = target_file.replace('.au3', '.exe')
    run_via_exec_daemon(['taskkill', '/IM', target_exe.split('\\')[-1]], 
                        timeout=600, ignore_failure=True, host=vm_address)
    run_via_exec_daemon(['del', target_exe], timeout=600, host=vm_address)
    run_via_exec_daemon(['C:\\install\\autoit3\\aut2exe\\aut2exe.exe', '/in',
                        target_file, '/out', target_exe], timeout=600,
                        host=vm_address)
    return target_exe
