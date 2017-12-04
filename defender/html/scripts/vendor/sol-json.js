/**
 * @file A library containing functions to interact with JSON formatted data. Performs conversion to, from, cleanup,
 * sorting, duplication, replacements, etc.
 *
 * @summary JSON interaction tools.
 *
 * @author David Fritz
 * @version 1.0.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
var Solari = (function (parent) {
    // Submodules
    var Json = parent.json = parent.json || {};

    // Private variables
    var objectURL = null;

    /**
     *  Attempts to duplicate an object through conversion to and from JSON text.
     *
     * @param {*} object Object that can be processed as JSON text.
     * @param {function} reviver Describes how objects are transformed before being returned.
     * @returns {*} New object
     */
    function duplicate(object, reviver) {
        return JSON.parse(JSON.stringify(object), reviver);
    }

    /**
     * Reads JSON formatted file.
     *
     * @param {File} file Bits representing File object from local storage.
     * @param {function} callback Where to send processed data.
     * @param {function} reviver Describes how objects are transformed before being returned.
     */
    function readFile(file, callback, reviver) {
        if (typeof window.FileReader !== 'function') {
            console.log("File API is not supported on this browser. Please use a different browser.");
            return;
        }

        var reader = new FileReader();
        reader.onload = function () {
            callback(JSON.parse(reader.result), reviver);
        };
        reader.readAsText(file);
    }

    /**
     * Read JSON formatted local file from user input.
     *
     * @param {element} element HTML element where user provided file input.
     * @param {function} callback Where to send processed data.
     * @param {function} reviver Describes how objects are transformed before being returned
     */
    function readFileFromElement(element, callback, reviver) {
        var file = element.target.files[0];
        if (!file) {
            return;
        }

        readFile(file, callback, reviver);
    }

    /**
     * Converts object into JSON formatted Object URL.
     * @param {*} object Data which can be converted into JSON formatted text.
     * @returns {object} Object URL.
     */
    function makeObjectURL(object) {
        var data = new Blob([JSON.stringify(object, undefined, 2)], {type: 'text/plain'});

        // Revoke any existing file/blob access to prevent leaks
        if (objectURL !== null) {
            window.URL.revokeObjectURL(objectURL);
        }
        objectURL = window.URL.createObjectURL(data);

        return objectURL;
    }

    /**
     * Removes empty, null, and undefined values from an object.
     *
     * @param {*} object Data to scan for blank values.
     */
    function clean(object) {
        for (var keyValue in object) {
            // Do not touch primitive values

            if (typeof object[keyValue] === 'number' || typeof object[keyValue] === 'boolean') {
                continue;
            }

            if (object[keyValue] === undefined || object[keyValue] === null ||
                (!Array.isArray(object[keyValue]) && Object.keys(object[keyValue]).length === 0)) {
                // Object is null or empty, remove
                delete object[keyValue];
            } else if (Array.isArray(object[keyValue])) {
                if (object[keyValue].length !== 0) {
                    // Loop over array and clean objects
                    for (var item = object[keyValue].length - 1; item >= 0; item--) {
                        // Do not touch primitive values
                        if (typeof object[keyValue][item] === 'number' || typeof object[keyValue][item] === 'boolean') {
                            continue;
                        }

                        if (object[keyValue][item] === undefined || object[keyValue][item] === null) {
                            // Object is null or empty, remove from array
                            object[keyValue].splice(item, 1);
                        } else {
                            // Recursively clean object
                            clean(object[keyValue][item]);

                            // If object was emptied, remove
                            if (Object.keys(object[keyValue][item]).length === 0) {
                                object[keyValue].splice(item, 1);
                            }
                        }
                    }

                    if (object[keyValue].length === 0) {
                        // If array emptied during clean operation, remove
                        delete object[keyValue];
                    }
                } else {
                    // Empty array, remove
                    delete object[keyValue];
                }
            } else if (typeof object[keyValue] === 'object') {
                clean(object[keyValue]);
            }
        }
    }

    /**
     * Replaces a key:value pair in an object with new key:value pair
     *
     * @param {*} object Original object to scan for replacements.
     * @param {*} targetKey Key of the value set to be removed from object.
     * @param {*} replacementK Key to be inserted into object.
     * @param {*} replacementV Value to be inserted with key into object.
     */
    function inject(object, targetKey, replacementK, replacementV) {
        if (Array.isArray(object)) {
            for (var aKey in object) {
                inject(object[aKey], targetKey, replacementK, replacementV);
            }
        } else {
            for (var key in object) {
                if (key === targetKey) {
                    delete object[key];
                    object[replacementK] = replacementV;
                    return;
                } else if (Array.isArray(object[key])) {
                    for (var item = object[key].length - 1; item >= 0; item--) {
                        inject(object[key], targetKey, replacementK, replacementV);
                    }
                }
            }
        }
    }

    // Public functions
    Json.duplicate = duplicate;
    Json.readFile = readFile;
    Json.readFileFromElement = readFileFromElement;
    Json.makeObjectURL = makeObjectURL;
    Json.clean = clean;
    Json.inject = inject;

    return parent;
}(Solari || {}));
