## `run`
Execute a subprocess locally or on a remote host.  Returns the stdout of the subprocess as a string.
Many of the optional parameters have default values.  Please refer to the source for that 
information.

### Parameters

| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| args | yes | List | List of strings that specify subprocess to execute with accompanying arguments. |
| timeout | optional | Int | Duration to wait for the subprocess to return. |
| host | optional | String | IP address of the remote machine to execute the subprocess on. |
| split | optional | Boolean | Convert output to a list of lines, each line is a list of words. |
| word_split | optional | Boolean | Split on whitespace to return a list of strings. |
| line_split | optional | Boolean | Split output on the newline character.
| ignore_failure | optional | Boolean | Do not raise exceptions for non-zero exit codes. |
| verify | optional | Boolean | Make sure we can connect to the remote host. |
| cwd | optional | String | Run commands in the specified working directory. |
| user | optional | String | Attempt ssh connection as the specified user. |
| env | optional | Dictionary | Set the specified environment variables upon execution. |
| shell | optional | Boolean | If true, run the command through a shell. | 
| stderr | optional | Boolean | Return stderr in addition to stdout. | 
| echo | optional | Boolean | Echo stdout/stderr through to sys.stdout/sys.stderr. |
| verbose | optional | Boolean | Print the arguments, timing, and exit code for the subprocess. |
| announce_interval | optional | Int | Specify the announce interval. |
| wait | optional | Boolean | If True, wait for the command to complete before returning from run(). |
| check_host_key | optional | Boolean | Perform host key verification for ssh. |

### Example Usage

```python
#Start a guest named win7 on a remote host(specified by IP address) running XT, setting a custom   timeout value.
run(['xec-vm', '-n', 'win7', 'start'], host=host, timeout=60)
 ```

## `retry`
Run the command, retrying in the event of an exception for upto a _timeout_ specified number of seconds, waiting _pace_ seconds between each attempt.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| fn | yes | string | Function to run and retry in the event of failure. |
| description | yes | string | A message that details the the function being retried. |
| pace | optional | int | Duration between each retry attempt. | 
| timeout | optional | int | Duration before BVT should throw a timeout. | 
| catch | optional | list | List of Exceptions to catch to trigger a retry. |

### Example Usage

```python
#Attempts to download a file from a designated url.
retry(lambda: job(['wget', '-q', '-O', dest_file, url], timeout=3600), 
	timeout=7200, description='download '+url)
```


## `readfile`
Returns the contents of a file from a remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| filename | yes | String | Absolute path to the file on the host. |
| host | optional | String | IP address of the remote machine to read the file from. |
| user | optional | String | Ssh to the host as the specified user. |
| check_host_key | optional | Boolean | Perform host key verification for ssh. |

### Example Usage

```python
#Read and return the contents of file config.cfg located on the remote host
readfile("/home/root/config.cfg", host=host)
```

## `writefile`
Write data specified by _content_ to the the file located on the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| _filename_ | yes | String | Absolute path to the file on the host. |
| _content_ | yes | String | Data to be written to the file. |
| _host_ | optional | String | IP address of the remote machine to read the file from. |
| _user_ | optional | String | Ssh to the host as the specified user. |
| _via_root_ | optional | Boolean | Write the file as the root user. |

### Example Usage
```python
#Write the contents of MOUNT_SCRIPT, a local string defined somewhere in the python file to script.sh on a remote host
writefile("/tmp/storage/script.sh", MOUNT_SCRIPT, host=host)
```

## `verify_connection`
Verify that we can connect to a remote host as the specified user.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | String | IP address of the remote machine to read the file from. |
| user | yes | String | Ssh to the host as the specified user. |
| timeout | optional | Int | Duration to wait for subprocess to complete. |
| check_host_key | optional | Boolean | Perform ssh host key verification. |

### Example Usage
```python
#Verify that the host is reachable as user 'user'
verify_connection(host, "user", timeout=60, check_host_key=False)
```

## `run_via_exec_daemon`
Execute a set of arguments on a remote host that is running the execdaemon.  Requires separate
environment setup (a running guest with execdaemon configured and running).

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| args | yes | List | List containing the command and its accompanying arguments to be run. |
| host | yes | String | IP address of the remote machine. |
| timeout | optional | Int | Duration to wait before terminating the operation. |
| ignore_failure | optional | Boolean | Ignore non-zero exit codes. |
| split | optional | Boolean | Return output as a list of lines where each line is a list of words.|
| echo | optional | Boolean | Print extra information to stdout. |
| wait | optional | Boolean | If wait is True, do not return until the remote execution has completed.|

### Example Usage
```python
#List the contents of a windows directory on virtual machine located at _guest_ip_.
run_via_exec_daemon(['dir', 'C:\\Users\\Administrator\\Documents\\'], host=guest_ip, wait=True)
```



| host | yes | String | IP address of the remote machine to read the file from. |
