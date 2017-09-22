## `install_guest`
Install a new guest on the specified host from media of specified
type.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of host machine to install guest on.|
| guest | optional | string | Type of guest being installed (XP, Linux, etc) |
| kind | optional | string | Type of media we are installing the guest from (iso, vhd, etc) | 
| busy_stop | optional | Boolean | Perform a busy stop of the guest. |
| encrypt_vhd | optional | Boolean | Encrypt the VHD of the new guest. |
| url | optional | string | URL to remove VHD. |

### Example Usage

```python
install_guest(host, guest='Linux', kind='vhd', url=URL)
```

## `check_free`
Check to see if host has enough free memory and free disk space for an operation

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of host machine to examine free memory and disk space. |
| amount | optional | int | Amount of free disk space to verify.  Raise an exception if there is less than _amount_. |
| target_os | optional | string | Profile for average memory size needed by that OS as a guest. |

### Example Usage

```python
check_free(host, amount=5000000, target_os=os_name)
```

## `download_image`
Download an image to use for BVT

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of host machine to download the image to. |
| kind | yes | string | Type of image (iso, with_tools). |
| guest | yes | string | Type of guest that is on the iso/vhd. |
| dest_file | yes | string | Name of file destination for vhd being downloaded. |
| url | optional | string | URL to the vhd to be downloaded. |

### Example Usage

```python
download_image(host, 'iso', 'Linux', PATH, url=URL)
```

## `list_cd_devices`
Output a list of all cd devices recognized by the remote target.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host (domain or Linux-based guest). |

### Example Usage

```python
print list_cd_devices(host)
```

## `file_exists`
Checks to see if a file exists on a remote target.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote target. |
| file_name | yes | string | Absolute path to the file on the remote target. |

### Example Usage

```python
if file_exists(host, '/usr/lib/libpython2.7.so'):
	...
```

## `create_file`
Write _content_ to specified filename on remote target.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote target. |
| file_name | yes | string | Absolute path to the file to be created on the remote target. |
| content | yes | string | Content to write to _file_name_. |

### Example Usage

```python
TEST_SCRIPT=""" #!/bin/bash
echo 'foobar'
""" 
create_file(host, '/home/user/script.sh', TEST_SCRIPT)
```

## `make_tools_iso_available`
Make the xc_tools iso available to guest on a remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host. |
| vm_address | yes | string | IP address of the Linux guest. |
| vm_name | yes | string | Name of the guest located on remote host. |
| domain | yes | Dictionary | Dictionary with attributes of Linux guest on remote host. |

### Example Usage

```python
make_tools_iso_available(host, guest_ip_address, 'Deb guest', domain_dict)
```

## `soft_reboot`
Perform a soft reboot from inside the linux guest.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host. |
| vm_name | yes | string | Name of the Linux guest VM. |

### Example Usage

```python
soft_reboot(host, 'win7')
```

## `soft_reboot_and_wait`
Perform a soft reboot but wait for guest to come back up.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host. |
| vm_name | yes | string | Name of the Linux guest VM. |

 
### Example Usage

```python
soft_reboot_and_wait(host, 'win7')
```

## `start_vm`
Tell BVT to start the specified guest VM on target host and switch focus to it.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host. |
| guest | yes | string | Name of the guest VM to start. |
| may_already_be_running | optional | Boolean | Extra flag to indicate target guest is already running. |
| timeout | optional | int | Duration to wait before throwing a timeout error. |
| check_method | optional | string | Default method for communicating inside the guest (ssh, exec_daemon) |

### Example Usage
```python
#Start a guest and verify that it is up and running.
start_vm(host, 'debian-guest', timeout=200, check_method='ssh')
```

## `start_vm_if_not_running`
Check first if the guest vm is running, then attempt to start it.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| dut | yes | string | IP address of the remote host. |
| guest | yes | string | Name of the guest VM to start. |
| timeout | optional | int | Duration to wait before throwing a timeout error. |

### Example Usage
```python
start_vm_if_not_running(host, 'debian-guest', timeout=300)
```

## `have_driver`
Checks for the named driver on the remote windows guest.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote guest. |
| section | yes | string | Argument to pass to the devcon utility. |
| name | yes | string | Name of driver to verify. |

### Example Usage
```python
have_driver(host, section, 'USB Controller')
```

## `guest_start`
Start the named guest on the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |
| wait | optional | boolean | Wait for the command to return (or not). |

### Example Usage
```python
guest_start(host, name, wait=False)
```

## `guest_shutdown`
Shutdown the named guest on the remote host through the toolstack.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |
| wait | optional | boolean | Wait for the command to return (or not). |

### Example Usage
```python
guest_shutdown(host, name, wait=True)
```

## `guest_destroy`
Destroy the named guest on the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |
| wait | optional | boolean | Wait for the command to return (or not). |

### Example Usage
```python
guest_destroy(host, name, wait=True)
```

## `guest_delete`
Delete the named guest from the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |

### Example Usage
```python
guest_delete(host, name)
```

## `guest_uuid`
Return the uuid of the named guest on the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |
| clean | optional | boolean | Convert '-' to '_' in the uuid name. Required for proper parsing in some cases. |

### Example Usage
```python
guest_uuid(host, name, clean=True)
```

## `guest_exists`
Determine whether the guest exists on the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |

### Example Usage
```python
guest_uuid(host, name)
```

## `guest_state`
Return the current state of the named guest on the remote host.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |

### Example Usage
```python
guest_state(host, name)
```

## `create_guest`
Create a guest on the remote host.  See the source for specific default values.  All defaults can be
overridden.

### Parameters
| Name | Required | Type | Description |
| ---- | -------- | ---- | ----------- |
| host | yes | string | IP address of the remote host. |
| name | yes | string | Name of guest. |
| desc | yes | string | Description of the guest. |
| memory | optional | string | Amount of memory to allocate to the guest, in MB. |
| vcpus | optional | string | Number of vcpus to allocate to the guest. |
| encrypt | optional | boolean | Encrypt the disk. |
| os | optional | string | Name of the operating system of the guest. |
| name | yes | string | Name of guest. |
| name | yes | string | Name of guest. |

### Example Usage
```python
guest_state(host, name)
```
