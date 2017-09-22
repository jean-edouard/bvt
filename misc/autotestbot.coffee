IRC = require 'irc-js'
fs = require 'fs'
config_file = '/etc/tracker.json'
mongodb = require 'mongodb'
replSet = new mongodb.ReplSetServers( [
    (new mongodb.Server "autotest-mongo1.cam.xci-test.com", 27017, {}),
    (new mongodb.Server "autotest-mongo2.cam.xci-test.com", 27017, {}),
    (new mongodb.Server "autotest-mongo3.cam.xci-test.com", 27017, {})],
    {rs_name:'autotestset'})

irc_options =
  server: 'SETME' # IRC server name
  pass: 'SETME' # IRC server password
  nick: 'autotestbot'
  flood_protection: true
exports.timeout = 3600

setupTimeout = ->
  clearTimeout exports.timeoutId if exports.timeoutId?
  exports.timeoutId = setTimeout ( ->
    console.log "no updates for #{exports.timeout}s"
    exports.say "(no updates for #{exports.timeout}s so exiting)" if exports.say?
    process.exit 5), exports.timeout*1000

setupTimeout()

db = new mongodb.Db('logs', replSet, {})
db.on "close", (err) ->
  exports.say "(lost database connection)"
  setTimeout (-> process.exit 5), 2000

db.open (err, client) ->
  throw err if err
  client.collection 'logs', (err, logs) ->
    irc = new IRC irc_options
    irc.on 'error:network', -> process.exit 1
    irc.on 'disconnected', -> process.exit 2
    irc.on 'error', -> process.exit 3
    irc.connect ->
      say = (message) -> irc.privmsg "#autotest", message
      exports.say = say
      irc.join '#autotest'
      db.on "close", (err) ->
        say "(lost database connection)"
        console.log "lost database connection"
        setTimeout (-> process.exit 4), 2000
      say "(hello)"
      fs.readFile config_file, (err, config) ->
        if err
          exports.say "(unable to read #{config_file} for op password #{err})"
          return
        confd = JSON.parse config
        if confd.oper_password? and confd.oper_user?
          irc.oper confd.oper_user, confd.oper_password
          say '(asked to be operator)'
        else
          say '(no operator password)'

      logs.find({}, {limit:1, sort: {time:-1}}).nextObject (err, doc1) ->
        throw err if err
        early = new Date(doc1.time * 1000)
        say "(will show log entries after #{early})"
        logs.find({time:{$gt:doc1.time}}, {tailable:true}).each (err, item) ->
          throw err if err
          if item
            ts = new Date (item.time * 1000)
            if item.kind in ['HEADLINE', 'RESULT']
              console.log "#{ts} #{item.kind} #{item.message}"
              kindstr = if item.kind == 'HEADLINE' then '' else 'RESULT '
              smess = item.message.replace(' on '+item.dut_name, '')
              say "#{item.dut_name}: #{kindstr} #{smess}" if ts >= early
            setupTimeout()
