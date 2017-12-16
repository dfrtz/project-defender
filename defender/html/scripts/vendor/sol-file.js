/**
 * @file A library containing functions to interact with user Files. Interaction may be during read, writes, or access
 * of files in memory
 *
 * @summary File interaction tools.
 *
 * @author David Fritz
 * @version 1.0.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
var Solari = (function (parent) {
    // Submodules
    var FileUtils = parent.file = parent.file || {};

    // Private variables
    var blobObjectURL = null;

    /**
     * Finds the name of the file without extension.
     *
     * @param {string} filename Name of file with or without extension
     * @returns {string} Name of file without extension.
     */
    function getName(filename) {
        return filename.substring(0, filename.lastIndexOf("."));
    }

    /**
     * Finds the extension of the file without name.
     *
     * @param {string} filename Name of file with or without extension
     * @returns {string} Extension of file without name.
     */
    function getExtension(filename) {
        return filename.split(".").pop();
    }

    /**
     * Saves an objectURL as a file to local storage.
     *
     * @param {string} fileName Name of file on local storage.
     * @param {string} objectURL Path of URL to save
     */
    function saveObjectURL(fileName, objectURL) {
        // Create new, temporary link
        var link = document.createElement("a");

        link.setAttribute("download", fileName);
        link.href = objectURL;

        // Add temporary link to body, simulate click, and remove link
        document.body.appendChild(link);
        window.requestAnimationFrame(function () {
            var event = new MouseEvent("click");
            link.dispatchEvent(event);
            document.body.removeChild(link);
        });
    }

    /**
     * Save binary data blob as file on local storage.
     *
     * @param {string} fileName Name of file on local storage.
     * @param {Blob} data File like object which can can be saved as file on local storage.
     */
    function saveBlob(fileName, data) {
        // Revoke any existing file/blob access to prevent leaks
        if (blobObjectURL !== null) {
            window.URL.revokeObjectURL(blobObjectURL);
        }
        blobObjectURL = window.URL.createObjectURL(data);

        saveObjectURL(fileName, blobObjectURL);
    }

    /**
     * Converts a file from local storage into specified data type.
     *
     * @param {string} type Format of data to return. Valid options: binarystring, dataurl, arraybuffer.
     * @param {File} file Bits representing File object from local storage.
     * @param {function} callback Where to send processed data after read.
     */
    function readAs(type, file, callback) {
        if (typeof window.FileReader !== "function") {
            console.log("File API is not supported on this browser. Please use a different browser.");
            return;
        }

        var reader = new FileReader();
        reader.onload = function () {
            callback(file, reader.result);
        };

        type = type.toLowerCase();
        if (type === "binarystring") {
            reader.readAsBinaryString(file);
        } else if (type === "dataurl") {
            reader.readAsDataURL(file);
        } else if (type === "arraybuffer") {
            reader.readAsArrayBuffer(file);
        }
    }

    /**
     * Converts file from local storage into dataurl format.
     *
     * @param {File} file Bits representing File object.
     * @param {function} callback Where to send processed data after read.
     */
    function readAsDataURL(file, callback) {
        readAs("dataurl", file, callback);
    }

    /**
     * Converts file from local storage into binarystring format.
     *
     * @param {File} file Bits representing File object.
     * @param {function} callback Where to send processed data after read.
     */
    function readAsBinaryString(file, callback) {
        readAs("binarystring", file, callback);
    }

    /**
     * Converts file from local storage into arraybuffer.
     *
     * @param {File} file Bits representing File object.
     * @param {function} callback Where to send processed data after read.
     */
    function readAsArrayBuffer(file, callback) {
        readAs("arraybuffer", file, callback);
    }

    // Public functions
    FileUtils.getName = getName;
    FileUtils.getExtension = getExtension;
    FileUtils.saveObjectURL = saveObjectURL;
    FileUtils.saveBlob = saveBlob;
    FileUtils.readAs = readAs;
    FileUtils.readAsDataURL = readAsDataURL;
    FileUtils.readAsBinaryString = readAsBinaryString;
    FileUtils.readAsArrayBuffer = readAsArrayBuffer;

    return parent;
}(Solari || {}));
