var Solari = (function(parent) {
    // Submodules
    var Utils = parent.utils = parent.utils || {};

    // Private functions
    function range(n) {
        return new Array(n);
    }

    function sortArray(data, keyValue) {
        return data.sort(function (a, b) {
            var x = a[keyValue];
            var y = b[keyValue];
            return ((x < y) ? -1 : ((x > y) ? 1 : 0));
        });
    }

    function varArgs(start, oldArgs) {
      var args = [];

      for (var i = start; i < oldArgs.length; i++) {
          args.push(oldArgs[i]);
      }

      return args;
    }

    function padZeros(value, length) {
        var string = String(value);
        while (string.length < length) {
            string = "0" + string;
        }
        return string;
    }

    function formatString(string, varargs) {
        // Varargs is only included in declaration for readability
        varargs = varArgs(1, arguments);

        return string.replace(/{(\d+)}/g, function(match, number) {
            return typeof varargs[number] != 'undefined' ? varargs[number] : match;
        });
    }

    function runAsyncTask(data, objectUrl, onFinish) {
        var worker = new Worker(objectUrl);
        worker.onmessage = onFinish;
        worker.postMessage(data);
    }

    function buildAsyncBlob(onmessage, varargs) {
        // Varargs is only included in declaration for readability
        varargs = varArgs(1, arguments);

        var body = "onmessage = " + onmessage.toString() + ";\n";

        for (var i = 0; i < varargs.length; i++) {
            var arg = varargs[i];

            if (isString(arg)) {
                body += arg;
            } else if (arg !== undefined){
                body += arg.toString() + ";\n";
            }
        }

        return new Blob([body], {type: "text/javascript"});
    }

    function isString(value) {
        return typeof value === 'string';
    }

    function WorkerPool(config) {
        // Example config:
        /*{
            threads: 10,
            useCache: true,
            cache: "Random Data",
            initializationInterval: 100,
            scripts: [function(event) {self.postMessage(event.data);}]
        }*/

        this.workers = [];
        this.lastWorker = 0;
        this.maxWorkers = config.threads || 2;
        this.workersInitializing = false;
        this.callback = config.callback || function () {};

        this.cacheEnabled = config.useCache || false;
        this.cacheData = config.cache || undefined;
        this.cacheInitializing = false;

        this.asyncObjectUrl = undefined;
        this.initCheckInterval = config.initializationInterval || 100;

        if (config.scripts !== undefined && config.scripts.length > 0) {
            setScripts(config.scripts);
        }
    }

    WorkerPool.prototype.setScripts = function() {
        if (this.asyncObjectUrl !== null) {
            window.URL.revokeObjectURL(this.asyncObjectUrl);
        }
        var scripts = Array.from(arguments);

        var onmessage = function(event) {
            var cmd = event.data.cmd;
            if (cmd === "initCache") {
                initCache(event.data.cache);
                return;
            } else if (cmd === 'user') {
                run(event.data.args);
            }
        };

        scripts.unshift(onmessage);

        this.asyncObjectUrl = window.URL.createObjectURL(Solari.utils.buildAsyncBlob.apply(null, scripts));
        this.initWorkers();
    };

    WorkerPool.prototype.setCallback = function(callback) {
        var self = this;

        var callbackWrapper = function(event) {
            self.onCallback(event);

            if (event.data.cmdResult !== 'initCache') {
                callback(event);
            }
        };
        self.callback = callbackWrapper;

        for (var i = 0; i < self.workers.length; i++) {
            self.workers[i].onmessage = self.callback;
        }
    };

    WorkerPool.prototype.initWorkers = function() {
        var self = this;

        if (self.workersInitializing) {
            return;
        }

        self.workersInitializing = true;

        var workers = [];
        self.workers.length = 0;
        for (var i = 0; i < self.maxWorkers; i++) {
            var worker = new Worker(self.asyncObjectUrl);
            worker.onmessage = self.callback;
            workers.push(worker);
        }
        self.workers = workers;

        self.workersInitializing = false;
    };

    WorkerPool.prototype.initCache = function(cache) {
        var self = this;

        if (self.cacheInitializing) {
            //TODO implement way for parent async tasks to be notified before starting work
            //return;
        }

        if (cache !== undefined) {
            self.cacheData = cache;
        }

        self.cacheInitializing = true;
        for (var i = 0; i < self.maxWorkers; i++) {
            self.workers[i].postMessage({cmd: 'initCache', cache: self.cacheData});
        }
        self.cacheInitializing = false;
    };

    WorkerPool.prototype.run = function(args) {
        var self = this;

        if (self.workers.length <= 0) {
            if (self.workersInitializing) {
                setTimeout(function() {
                    self.run(args);
                }, self.initCheckInterval);
                return;
            }
            self.initWorkers();
        }

        if (self.cacheEnabled && self.cacheData === undefined) {
            if (self.cacheInitializing) {
                setTimeout(function() {
                    self.run(args);
                }, self.initCheckInterval);
                return;
            }
            self.initCache();
        } else {
            var workerId = self.lastWorker;
            self.lastWorker++;
            self.lastWorker = self.lastWorker >= self.workers.length ? 0 : self.lastWorker;
            self.workers[workerId].postMessage({cmd: 'user', args: args});
        }
    };

    WorkerPool.prototype.onCallback = function(event) {
        var cmd = event.data.cmdResult;

        //TODO track cache initialization counts
    };

    // Public functions
    Utils.range = range;
    Utils.sortArray = sortArray;
    Utils.buildAsyncBlob = buildAsyncBlob;
    Utils.async = runAsyncTask;
    Utils.padZeros = padZeros;
    Utils.format = formatString;
    Utils.WorkerPool = WorkerPool;

    return parent;
}(Solari || {}));
