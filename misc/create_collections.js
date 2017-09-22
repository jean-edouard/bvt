db = db.getMongo().getDB("autotest");
db.test_cases.ensureIndex({_id:1})
db.duts.ensureIndex({_id:1})
db.builds.ensureIndex({_id:1})
db.coverage.ensureIndex({_id:1})
db.results.ensureIndex({end_time:1})
db.results.ensureIndex({start_time:1})
db.results.ensureIndex({build:1})
db.duts.ensureIndex({start_time:1})
db.builds.ensureIndex({build_time:1})
db.builds.ensureIndex({tag_time:1})

db.cloneDatabase('autotest-dev');

/* no capped collections */

// eval("use watcher"); /* unusued? */

db = db.getMongo().getDB("trackgit");
db.createCollection('updates', {capped:true, size:1000*1000*1000});
db.revisions.ensureIndex({_id:1});
db.revisions.ensureIndex({timestamp:-1});
db.revisions.ensureIndex({tag:1});
db.revisions.ensureIndex({repository:1, revision:1});
db.updates.ensureIndex({_id:1});
db.heads.ensureIndex({_id:1});
db.tags.ensureIndex({_id:1});
db.updates.ensureIndex({_id:1})

db.cloneDatabase('autotest-dev');

db = db.getMongo().getDB("logs");
db.createCollection('logs', {capped:true, size:1000*1000*1000*10});
db.logs.ensureIndex({result_id:1});
db.logs.ensureIndex({_id:1});
db.logs.ensureIndex({time:1})
db.cloneDatabase('autotest-dev');
