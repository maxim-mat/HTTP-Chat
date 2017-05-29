## @package HTTP--Chat.constants Program constants.
## @file constants.py Implementation of @ref HTTP--Chat.constants
#

## Max block size to read.
BLOCK_SIZE = 8192

## Characters indicating new line.
CRLF = '\r\n'

## Binary new line.
CRLF_BIN = CRLF.encode('utf-8')

## Time in seconds until a user is defined as inactive in a room.
EXPIRED_PERIOD = 60 * 5

## Communication protocol
HTTP_SIGNATURE = 'HTTP/1.1'

## Maximum header length.
MAX_HEADER_LEN = 4096

## Maximum header amount.
MAX_HEADER_AMOUNT = 100

## Time in seconds to sleep until I/O
TIMEOUT_DEFAULT = 1000

## Maximum message storage length.
# upon reching this length old messages will be discarded when new ones arrive.
TOO_BIG = 100
