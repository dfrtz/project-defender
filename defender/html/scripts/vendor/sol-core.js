/**
 * @file A library consisting of functions which are called by users and submodules. Basic utilities and general
 * purpose processing should be declared here, and defined in HTML before any other submodules.
 *
 * @summary Base library containing generic and convenience methods.
 *
 * @author David Fritz
 * @version 1.0.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
var Solari = (function (parent) {
    var Utils = parent.utils = parent.utils || {};

    /**
     * Creates sequential integer array of specified size.
     *
     * @param {number} count The length of the array created.
     * @returns {number[]} Array of integer values starting with 0.
     */
    function range(count) {
        return Array.apply(null, Array(count)).map(function (current, index) {
            return index;
        })
    }

    /**
     * Sorts an array of objects by specified key.
     *
     * @param {Array} data Array of objects.
     * @param {string} keyValue The key from each object to sort by.
     * @returns {Array} Original Array sorted.
     */
    function sortArray(data, keyValue) {
        return data.sort(function (a, b) {
            var x = a[keyValue];
            var y = b[keyValue];
            return ((x < y) ? -1 : ((x > y) ? 1 : 0));
        });
    }

    /**
     * Truncates arguments from start to specified index.
     *
     * @param {number} start First index to save in new array.
     * @param {IArguments} oldArgs Array of argument objects.
     * @returns {Array} Array containing elements from start index to end of passed arguments.
     */
    function varArgs(start, oldArgs) {
        var args = [];

        for (var i = start; i < oldArgs.length; i++) {
            args.push(oldArgs[i]);
        }

        return args;
    }

    /**
     * Creates a string with leading zeros up to a specified length.
     *
     * @param {*} value An object which can be represented as a string.
     * @param {number} length Pad zeros up to this amount.
     * @returns {string} New string with leading zeros if smaller than length, or unmodified string if over length.
     */
    function padZeros(value, length) {
        var string = String(value);
        while (string.length < length) {
            string = "0" + string;
        }
        return string;
    }

    /**
     * Formats a string containing positional values with passed arguments.
     *
     * @param {string} string Format string with insertion placeholders as {} and optional indexes.
     * @param {IArguments} args Unlimited array of arguments to format into string placeholders.
     */
    function formatString(string, args) {
        var varargs = varArgs(1, arguments);

        return string.replace(/{(\d+)}/g, function (match, number) {
            return typeof varargs[number] !== "undefined" ? varargs[number] : match;
        });
    }

    /**
     * Creates an asynchronous worker which to run javascript against an object and send to callback method.
     *
     * @param {*} data Object to pass to Async Worker for processing.
     * @param {string} url Javascript URL run by Async Worker.
     * @param {function} onFinish Callback to pass returned data.
     */
    function runAsyncTask(data, url, onFinish) {
        var worker = new Worker(url);
        worker.onmessage = onFinish;
        worker.postMessage(data);
    }

    /**
     * Converts a set of javascript methods into a file-like object which can be referenced by async Workers.
     *
     * @param {function} onMessage Primary function which will be used by Web Worker to process messaging queue
     * @param {function[]} functions External functions to append as local functions in javascript Blob.
     * @returns {Blob} File-like javascript object containing all passed methods
     */
    function buildAsyncBlob(onMessage, functions) {
        functions = varArgs(1, arguments);

        var body = "onmessage = " + onMessage.toString() + ";\n";
        for (var i = 0; i < functions.length; i++) {
            var arg = functions[i];

            if (isString(arg)) {
                body += arg;
            } else if (arg !== undefined) {
                body += arg.toString() + ";\n";
            }
        }

        return new Blob([body], {type: "text/javascript"});
    }

    /**
     * Convenience method which checks if object is a string.
     *
     * @param {*} value Object to check type.
     * @returns {boolean} True if value is a string, False otherwise.
     */
    function isString(value) {
        return typeof value === "string";
    }

    /**
     * A Class to split work between group of Asynchronous Workers.
     *
     * A configuration should be passed to initialize the pool, however it is not required.
     *
     * @param {object} config Initialization options for workers.
     * @param {(number|undefined)} config.threads The number of maximum number of workers.
     * @param {(boolean|undefined)} config.useCache Enable workers to operate on static cache.
     * @param {(object|undefined)} config.cache Static cached data.
     * @param {(number|undefined)} config.initInterval How often to check if a worker is initializing before processing.
     * @param {(function[]|undefined)} config.scripts Array of methods available to workers.
     * @param {(function|undefined)} config.callback Method for workers to call with event data.
     * @class
     */
    function WorkerPool(config) {
        this.workers = [];
        this.lastWorker = 0;
        this.maxWorkers = config.threads || 2;
        this.workersInitializing = false;
        this.callback = config.callback || function () {
        };

        this.cacheEnabled = config.useCache || false;
        this.cacheData = config.cache || undefined;
        this.cacheInitializing = false;

        this.asyncObjectUrl = undefined;
        this.initInterval = config.initInterval || 100;

        if (config.scripts !== undefined && config.scripts.length > 0) {
            this.setScripts(config.scripts);
        }
    }

    /**
     * Adds scripts which will be available for access by all workers.
     *
     * @param {function[]} args External function to be translated for use by workers.
     */
    WorkerPool.prototype.setScripts = function (args) {
        var self = this;

        if (this.asyncObjectUrl !== null) {
            window.URL.revokeObjectURL(this.asyncObjectUrl);
        }
        var scripts = Array.from(arguments);

        var onmessage = function (event) {
            var cmd = event.data.cmd;
            if (cmd === "initCache") {
                self.initCache(event.data.cache);
            } else if (cmd === "user") {
                self.run(event.data.args);
            }
        };

        scripts.unshift(onmessage);

        this.asyncObjectUrl = window.URL.createObjectURL(Solari.utils.buildAsyncBlob.apply(null, scripts));
        this.initWorkers();
    };

    /**
     * Sets the method for workers to send event data.
     *
     * @param {function} callback Where to send events from workers.
     */
    WorkerPool.prototype.setCallback = function (callback) {
        var self = this;

        self.callback = function (event) {
            self.onCallback(event);

            if (event.data.cmdResult !== "initCache") {
                callback(event);
            }
        };

        for (var i = 0; i < self.workers.length; i++) {
            self.workers[i].onmessage = self.callback;
        }
    };

    /**
     * Fills worker pool with new Workers allowed to accept incoming tasks.
     */
    WorkerPool.prototype.initWorkers = function () {
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

    /**
     * Adds static cache to pool for new workers, and sends cache to all existing workers.
     *
     * @param {*} cache Data object to save in pool and pass to all workers.
     */
    WorkerPool.prototype.initCache = function (cache) {
        var self = this;

        if (self.cacheInitializing) {
            //TODO implement way for parent async tasks to be notified before starting work
        }

        self.cacheInitializing = true;
        self.cacheData = cache;
        for (var i = 0; i < self.maxWorkers; i++) {
            self.workers[i].postMessage({cmd: "initCache", cache: self.cacheData});
        }
        self.cacheInitializing = false;
    };

    /**
     * Process arguments on next available worker in pool.
     *
     * @param {IArguments} args Arguments to send to worker for processing.
     */
    WorkerPool.prototype.run = function (args) {
        var self = this;

        if (self.workers.length <= 0) {
            if (self.workersInitializing) {
                setTimeout(function () {
                    self.run(args);
                }, self.initInterval);
                return;
            }
            self.initWorkers();
        }

        if (self.cacheEnabled && self.cacheData === undefined) {
            if (self.cacheInitializing) {
                setTimeout(function () {
                    self.run(args);
                }, self.initInterval);
                return;
            }
            self.initCache();
        } else {
            var workerId = self.lastWorker;
            self.lastWorker++;
            self.lastWorker = self.lastWorker >= self.workers.length ? 0 : self.lastWorker;
            self.workers[workerId].postMessage({cmd: "user", args: args});
        }
    };

    /**
     * Processes worker events to track progress in Pool.
     *
     * @param {object} event Event data sent from Worker.
     */
    WorkerPool.prototype.onCallback = function (event) {
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
