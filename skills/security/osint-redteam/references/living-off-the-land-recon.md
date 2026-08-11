# Living Off the Land Reconnaissance

Native-OS-tools reconnaissance for environments where deploying FOSS binaries is not possible or would trigger EDR/AV. Every technique uses only what ships with the OS.

## Windows Native Recon Techniques

### DNS Recon
| Technique | Command | Logs Generated | Stealth |
|-----------|---------|----------------|---------|
| nslookup interactive | `nslookup` then `set type=MX` `target.com` | 4688 (cmd.exe) | ★★★★★ |
| nslookup one-shot | `nslookup -type=TXT target.com` | 4688 (cmd.exe) | ★★★★★ |
| Resolve-DnsName (PS) | `Resolve-DnsName target.com -Type ANY` | 800 (ScriptBlock) | ★★★☆☆ |
| .NET DNS | `[System.Net.Dns]::GetHostEntry('target')` | 800 (ScriptBlock) | ★★★☆☆ |

### HTTP Probing
| Technique | Command | Logs Generated | Stealth |
|-----------|---------|----------------|---------|
| BITSAdmin | `bitsadmin /transfer job https://target/path %TEMP%\probe.tmp` | 59 (Bits-Client) | ★★★☆☆ |
| CertUtil | `certutil -urlcache -f https://target %TEMP%\probe.tmp` | 13 (Sysmon), file on disk | ★★☆☆☆ |
| PowerShell IWR | `Invoke-WebRequest -Uri https://target` | 800, 4103, 4104 | ★★☆☆☆ |
| .NET WebClient | `(New-Object Net.WebClient).DownloadString('https://target')` | 800 | ★★★☆☆ |
| WinHttp (COM) | `(New-Object -ComObject WinHttp.WinHttpRequest).Open('GET','https://target',false)` | Minimal (COM) | ★★★★☆ |

### Port Probing
| Technique | Command | Logs Generated | Stealth |
|-----------|---------|----------------|---------|
| .NET TcpClient | `(New-Object Net.Sockets.TcpClient).ConnectAsync('host',80)` | 800 (ScriptBlock) | ★★★★☆ |
| PowerShell Test-Connection | `Test-Connection -Count 1 -TargetName host` | 800 | ★★★☆☆ |
| cmd ping | `ping -n 1 host` | 4688 | ★★★★☆ |
| System.Net.Sockets raw | `$s=New-Object Net.Sockets.Socket; $s.Connect('host',80)` | 800 | ★★★★☆ |

### WHOIS via Raw Socket
```powershell
$tcp = New-Object System.Net.Sockets.TcpClient
$tcp.Connect('whois.verisign-grs.com', 43)
$stream = $tcp.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$writer.WriteLine('domain.com')
$writer.Flush()
$reader = New-Object System.IO.StreamReader($stream)
$reader.ReadToEnd()
```

### Certificate Transparency
```powershell
$req = [System.Net.HttpWebRequest]::Create('https://crt.sh/?q=%25.target.com&output=json')
$req.UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
$resp = $req.GetResponse()
$reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
$reader.ReadToEnd()
```

## Linux Native Recon Techniques

### DNS
| Technique | Command | Stealth |
|-----------|---------|---------|
| dig | `dig target.com MX` | ★★★★★ |
| host | `host -t MX target.com` | ★★★★★ |
| nslookup | `nslookup target.com` | ★★★★★ |
| getent | `getent hosts target.com` | ★★★★★ |

### HTTP
| Technique | Command | Stealth |
|-----------|---------|---------|
| /dev/tcp (bash) | `exec 3<>/dev/tcp/target/80; echo -e "GET / HTTP/1.1\r\nHost: target\r\n\r\n" >&3; cat <&3` | ★★★★☆ |
| openssl s_client | `echo | openssl s_client -connect target:443 -servername target 2>/dev/null` | ★★★★☆ |
| wget | `wget --no-verbose -O- https://target 2>&1` | ★★★☆☆ |
| curl | `curl -s -A 'Mozilla/5.0' https://target` | ★★★☆☆ |

### Port Testing
| Technique | Command | Stealth |
|-----------|---------|---------|
| /dev/tcp | `timeout 2 bash -c 'echo > /dev/tcp/host/port && echo open'` | ★★★★★ |
| nc (if installed) | `nc -zv -w2 host port` | ★★★★☆ |
| /proc/net/tcp | `cat /proc/net/tcp` (check existing conns) | ★★★★★ |

## Decision Guide

| Scenario | Best Technique | Why |
|----------|----------------|-----|
| "Just resolve DNS once" | nslookup / dig | No script host, no persistent component |
| "Need HTTP response headers" | .NET WebClient (Win) / openssl (Linux) | Minimal logs, in-memory |
| "Need to download a file" | BITSAdmin (Win) / wget (Linux) | BITSAdmin is legitimate Windows component; wget is standard |
| "Check if port is open" | .NET TcpClient (Win) / /dev/tcp (Linux) | TcpClient doesn't touch disk; /dev/tcp is shell built-in |
| "Need to fetch cert info" | crt.sh via .NET HttpWebRequest | No binary download, pure built-in .NET |
| "Full stealth required" | nslookup + .NET raw sockets | Minimal event log footprint |
| "Speed needed" | PowerShell IWR + Resolve-DnsName | More logs, fastest execution |
