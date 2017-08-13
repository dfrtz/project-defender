var Solari = (function(parent) {
    // Submodules
    var File = parent.file = parent.file || {};

    // Private variables
    var blobObjectURL = null;

    // Private functions
    function getName(filename) {
        return filename.substring(0, filename.lastIndexOf('.'));
    }

    function getExtension(filename) {
        return filename.split('.').pop();
    }

    function saveObjectURL(fileName, objectURL) {
        // Create new, temporary link
        var link = document.createElement('a');

        link.setAttribute('download', fileName);
        link.href = objectURL;

        // Add temporary link to body, simulate click, and remove link
        document.body.appendChild(link);
        window.requestAnimationFrame(function () {
            var event = new MouseEvent('click');
            link.dispatchEvent(event);
            document.body.removeChild(link);
        });
    }

    function saveBlob(fileName, data) {
        // Revoke any existing file/blob access to prevent leaks
        if (blobObjectURL !== null) {
          window.URL.revokeObjectURL(blobObjectURL);
        }
        blobObjectURL = window.URL.createObjectURL(data);

        saveObjectURL(fileName, blobObjectURL);
    }

    /*
    * Create reader for user file, and return Base64 data to be accessed by app
    * on load completion.
    */
    function readAs(type, file, callback) {
        if (typeof window.FileReader !== 'function') {
          console.log("File API is not supported on this browser. Please use a different browser.");
          return;
        }

        var reader = new FileReader();
        reader.onload = function() {
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

    /*
    * Helper function for readAs("dataurl", file, callback)
    */
    function readAsDataURL(file, callback) {
        readAs("dataurl", file, callback);
    }

    /*
    * Helper function for readAs("binarystring", file, callback)
    */
    function readAsBinaryString(file, callback) {
        readAs("binarystring", file, callback);
    }

    /*
    * Helper function for readAs("binarystring", file, callback)
    */
    function readAsArrayBuffer(file, callback) {
        readAs("arraybuffer", file, callback);
    }

    // Public functions
    File.getName = getName;
    File.getExtension = getExtension;
    File.saveObjectURL = saveObjectURL;
    File.saveBlob = saveBlob;
    File.readAs = readAs;
    File.readAsDataURL = readAsDataURL;
    File.readAsBinaryString = readAsBinaryString;
    File.readAsArrayBuffer = readAsArrayBuffer;

    return parent;
}(Solari || {}));
