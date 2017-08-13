var Solari = (function(parent) {
    // Submodules
    var Json = parent.json = parent.json || {};

    // Private variables
    var objectURL = null;

    // Private functions
    function duplicate(object, reviver) {
        return JSON.parse(JSON.stringify(object), reviver);
    }

    /*
    * Create reader for user file, and return JSON data to be accessed by app
    * on load completion.
    */
    function readFile(file, callback, reviver) {
        if (typeof window.FileReader !== 'function') {
            console.log("File API is not supported on this browser. Please use a different browser.");
            return;
        }

        var reader = new FileReader();
        reader.onload = function() {
            callback(JSON.parse(reader.result), reviver);
        };
        reader.readAsText(file);
    }

    function readFileFromElement(element, callback, reviver) {
        // We can only access user selected file from web input
        var file = element.target.files[0];
        if (!file) {
            return;
        }

        readFile(file, callback, reviver);
    }

    function makeObjectURL(json) {
        // Conver JSON data into a blob to be downloaded
        var data = new Blob([JSON.stringify(json, undefined, 2)], {type: 'text/plain'});

        // Revoke any existing file/blob access to prevent leaks
        if (objectURL !== null) {
            window.URL.revokeObjectURL(objectURL);
        }
        objectURL = window.URL.createObjectURL(data);

        return objectURL;
    }

    function clean(json) {
        for (var key in json) {
            // Do not touch primitive values
            if (typeof json[key] === 'number' || typeof json[key] === 'boolean') {
                continue;
            }

            if (json[key] === undefined || json[key] === null ||
                (!Array.isArray(json[key]) && Object.keys(json[key]).length === 0)) {
                    // Object is null or empty, remove
                    delete json[key];
            } else if (Array.isArray(json[key])) {
                if (json[key].length !== 0) {
                    // Loop over array and clean objects
                    for (var item = json[key].length - 1; item >= 0; item--) {
                        // Do not touch primitive values
                        if (typeof json[key][item]=== 'number' || typeof json[key][item] === 'boolean') {
                            continue;
                        }

                        if (json[key][item] === undefined || json[key][item] === null) {
                            // Object is null or empty, remove from array
                            json[key].splice(item, 1);
                        } else {
                            // Recursively clean object
                            clean(json[key][item]);

                            // If object was emptied, remove
                            if (Object.keys(json[key][item]).length === 0) {
                                json[key].splice(item, 1);
                            }
                        }
                    }

                    if (json[key].length === 0) {
                        // If array emptied during clean operation, remove
                        delete json[key];
                    }
                } else {
                    // Empty array, remove
                    delete json[key];
                }
            } else if (typeof json[key] === 'object') {
                clean(json[key]);
            }
        }
    }

    function inject(json, targetKey, replacementK, replacementV) {
        if (Array.isArray(json)) {
            for (var aKey in json) {
                inject(json[aKey], targetKey, replacementK, replacementV);
            }
        } else {
            for (var key in json) {
                if (key === targetKey) {
                    delete json[key];
                    json[replacementK] = replacementV;
                    return;
                } else if (Array.isArray(json[key])) {
                    for (var item = json[key].length - 1; item >= 0; item--) {
                        inject(json[key], targetKey, replacementK, replacementV);
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
