AutoItSetOption("ExpandEnvStrings",1)

Dim $InstalledCount = 0
Dim $IdleFor = 0
Dim $Count = 0
Dim $LoopMe = True

Func RecordLogEntry($message)
	FileWrite("C:/driverinstalllog.txt", $Count & " " & $message & @CRLF)	
	$Count = $Count + 1
EndFunc
RecordLogEntry("Starting version 3")
While $LoopMe
	$NothingHappened = False
	Select
		Case WinExists("Windows Security")
			ControlClick("Windows Security", "", "[CLASS:Button; INSTANCE:1]")
			RecordLogEntry("Clicking on Windows Security button 1")
		Case WinExists("Hardware Installation")
			If StringLeft(WinGetText("Hardware Installation"), 50) = "The software you are installing for this hardware:" Then
				RecordLogEntry("Hardware Installion warning: " & ControlGetText("Hardware Installation", "", 5302))
				ControlClick("Hardware Installation", "", 5303)
			EndIf
		Case WinExists("Software Installation")
			If StringLeft(WinGetText("Software Installation"), 50) = "The software you are installing has not passed Win" Then
				RecordLogEntry("Software Installion UAC warning" & ControlGetText("Software Installation", "", 5302))
				ControlClick("Software Installation", "", 5303)
			EndIf
		Case WinExists("Found New Hardware Wizard")
			If StringLeft(WinGetText("Found New Hardware Wizard"), 40) = "Welcome to the Found New Hardware Wizard" Then
				RecordLogEntry("Found New Hardware Wizard started")
				ControlClick("Found New Hardware Wizard", "", 8105)
				ControlClick("Found New Hardware Wizard", "", 12324)
			EndIf
			If StringLeft(WinGetText("Found New Hardware Wizard"), 43) = "This wizard helps you install software for:" Then
				RecordLogEntry("Found New Hardware Wizard found: " & ControlGetText("Found New Hardware Wizard", "", 1048))
				ControlClick("Found New Hardware Wizard", "", 12324)
			EndIf
			If StringLeft(WinGetText("Found New Hardware Wizard"), 40) = "Completing the Found New Hardware Wizard" Then
				RecordLogEntry("Completed Found New Hardware Wizard" & ControlGetText("Found New Hardware Wizard", "", 1009))
				$InstalledCount += 1
				ControlClick("Found New Hardware Wizard", "", 12325)
			EndIf
		Case WinExists("Hardware Update Wizard")
			If StringLeft(WinGetText("Hardware Update Wizard"), 37) = "Welcome to the Hardware Update Wizard" Then
				RecordLogEntry("Hardware Update Wizard started")
				ControlClick("Hardware Update Wizard", "", 8105)
				ControlClick("Hardware Update Wizard", "", 12324)
			EndIf
			If StringLeft(WinGetText("Hardware Update Wizard"), 43) = "This wizard helps you install software for:" Then
				RecordLogEntry("Hardware Update Wizard found: " & ControlGetText("Hardware Update Wizard", "", 1048))
				ControlClick("Hardware Update Wizard", "", 12324)
			EndIf
			If StringLeft(WinGetText("Hardware Update Wizard"), 42) = "Cannot Continue the Hardware Update Wizard" Then
				$Msg = StringSplit(WinGetText("Hardware Update Wizard"), @LF)
				RecordLogEntry("Cannot continue the hardware update wizard")
				RecordLogEntry("Error: " & $Msg[2])
				ControlClick("Hardware Update Wizard", "", 12325)
			EndIf
			If StringLeft(WinGetText("Hardware Update Wizard"), 26) = "Cannot Start this Hardware" Then
				$Msg = StringSplit(WinGetText("Hardware Update Wizard"), @LF)
				RecordLogEntry("Cannot start this hardware: " & $Msg[3])
				RecordLogEntry("Error: " & $Msg[6])
				ControlClick("Hardware Update Wizard", "", 12325)
			EndIf
			If StringLeft(WinGetText("Hardware Update Wizard"), 37) = "Completing the Hardware Update Wizard" Then
				$Msg = StringSplit(WinGetText("Hardware Update Wizard"), @LF)
				RecordLogEntry("Completing the Hardware Update Wizard" & $Msg[3])
				ControlClick("Hardware Update Wizard", "", 12325)
			EndIf
			
		Case WinExists("Microsoft Windows")
			$Text=WinGetText("Microsoft Windows")
			RecordLogEntry("Microsoft Windows window found")

			if StringInStr($Text, "Restart Now") <> 0 Then
				RecordLogEntry("Restart prompt found")
				ControlClick("Microsoft Windows", "", "[CLASS:Button; INSTANCE:1]")
				RecordLogEntry("Clicked on restart button")
			EndIf
		Case WinExists("Windows Security")
			$Text = WinGetText("Windows Security")
			ControlClick("Windows Security", "", "[CLASS:Button; INSTANCE:1]")
			RecordLogEntry("Clicking on Windows Security button 1")
		Case Else
			$NothingHappened = True
	EndSelect
	If $NothingHappened = True Then
		$IdleFor += 1
	Else
		$IdleFor = 0
	EndIf
	If $IdleFor = 180 Then
		$LoopMe = False
	EndIf
	Sleep(1000)
WEnd
RecordLogEntry("Total installed " & $InstalledCount & @LF)
RecordLogEntry("Ending")
