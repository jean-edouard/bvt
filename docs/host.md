## `check_mac_addresses`
Verify that the MAC address match between eth0 and brbridged.  Also a standalone test case.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the host machine to check for MAC address match. |

### Example Usage
```python
check_mac_addresses(host)
```

## `check_mounts`
Verify that the expected mount points exist and are mounted on the target host machine.  Also a standalone test case.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the host machine to check for clean mounts. |

### Example Usage
```python
check_mounts(host)
```

## `Console_Monitor`
Class to initiate simple serial logging for a remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host to invoke serial logging on. | 
| result_id | yes | int | Flag. |

### Example Usage
```python
with ConsoleMonitor(host, result_id) as monit:
	#do things, monit is the handle to the monitor object inside this scope.
	#ConsoleMonitor is written with __enter and __exit, thus designed to work
	#in the 'with' context.
```
## `start_logging`
Start logging dbus messages on remote host to dbus log file on BVT machine.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host to invoke dbus logging on. | 

### Example Usage
```python
start_logging(host)
```

## `stop_logging`
Stop logging dbus messages on remote host (cleanup for companion function start_logging())

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host to stop dbus logging on. | 

### Example Usage
```python
stop_logging(host)
```

## `test_enforce_encrypted_disks`
Test to see if the host enforces the inability to boot when an encrypted vhd has been tampered with. Also exists as a standalone test.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host to run test. | 

### Example Usage
```python
stop_logging(host)
```

## `FilesystemWriteAccess`
Gain temporary read-write access to a filesystem on remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host to gain rw access. |
| filesystem | yes | string | Path to the mount point of the filesystem (eg, '/', '/mnt'). |

### Example Usage
```python
with FilesystemWriteAccess(host, '/'):
	#do stuff
```

## `try_get_build`
Attempt to get the build information about a remote XT machine.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host to check build information. |
| timeout | optional | int | Duration to wait before throwing a timeout error. |


## `get_xc_config`
Get the config information for a remote XT machine or throw an exception.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote machine. |
| timeout | optional | int | Duration to wait before throwing a timeout error. |

### Example Usage
```python
config = get_xc_config(host, timeout=100)
```

## `try_get_xc_config_field`
Attempt to return the value of the specified field of the XT config on remote host.  An already
retrieved config may be used.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host to check build information. |
| field | yes | string | Field name of the config we want to get. |
| timeout | optional | int | Duration to wait before throwing a timeout error. |
| config | optional | Dictionary | An optional cached config. |

### Example Usage
```python
field_val = try_get_xc_config_field(host, 'build', timeout=120)
```

## `grep_dut_log`

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host to search log file. |
| logname | yes | string | Name of the rotating log file to search. |
| pattern | yes | string | Pattern to search for in the log file. |
| user | optional | string | Username to use when sshing to the remote host. Defaults to 'root'.|
| verify | optional | Boolean | Verify that the host can be reached before sshing to it. |


### Example Usage
```python
#Prints the results of grepping the rotating log to std out
print grep_dut_log(host, '/var/log/messages.1.gz', pattern)
```


## `network_test`
Use iperf to run a network performance check of the host, a guest, or all targets on a remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host to run iperf test on.|
| description | yes | string | Specifies whether to do network performance test for host and all guests or a specific target. |
| duration | optional | int | Length of time to run the test for, in seconds. |
| windows | optional | Boolean | Specifies whether the target is a windows OS. |

### Example Usage
```python
network_test(host, "dom0", duration=60)
```


## `partition_table_test`
Verify that all partitions on the remote host are 4K aligned.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host to verify partition table. |

### Example Usage
```python
partition_table_test(host)
```

## `set_power_state`
Transition the remote machine into the specified power state.  Wraps amttool so it can be passed valid amttool arguments.  Requires 
the AMT_PASSWORD variable set in settings.py.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host to modify the power state. |
| state | yes | string | Power state to put the remote host into. |
| args | yes | List | List of strings that contain arguments to pass to amttool. |

### Example Usage
```python
set_power_state(host, 's0', ['powerup', 'pxe']
```

## `set_s5`
Wrapper function to set powerstate to s5.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host. |

### Example Usage
```python
set_s5(host)
```

## `set_s0`
Wrapper function to set powerstate to s0.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host. |

### Example Usage
```python
set_s0(host)
```

## `set_pxe_s0`
Wrapper function to set powerstate to s0 and perform a pxe boot.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host. |

### Example Usage
```python
set_pxe_s0(host)
```

## `power_cycle`
Power cycle the remote machine.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote host. |
| pace | optional | int | Duration to sleep in sections. |
| pxe | optional | Boolean | Flag to enable a pxe boot when the machine boots. |

### Example Usage
```python
power_cycle(host, pace=15, pxe=True)
```

## `get_power_state`
Return the power state of the remote machine.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote machine. |

### Example Usage
```python
get_power_state(host)
```

## `verify_power_state`
Check that the remote machine is in the specified state.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of remote machine. |
| state | yes | string | State to verify the remote machine is in. |

### Example Usage
```python
verify_power_state(host, 's5')
```


