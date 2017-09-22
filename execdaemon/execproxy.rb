require 'socket'
listener = TCPServer.new("0.0.0.0", 9903)
char = File.open("/dev/pts/2", "r+b")
while true
  $stderr.puts("accepting connection\n")
  s = listener.accept
  $stderr.puts("got connection\n")
  line = s.readline
  $stderr.puts("got line #{line} from TCP\n")
  char.write(line)
  $stderr.puts("reading from dev\n")
  resp = ''
  while true
    byte = char.read(1)
    resp += byte
    if resp.end_with?('$FISHSOUP$')
      resp = resp.gsub('$FISHSOUP$', '')
      break
    end
  end
  $stderr.puts("returning response to TCP socket\n")
  s.write(resp)
  $stderr.puts("closing TCP socket\n")
  s.close
end
