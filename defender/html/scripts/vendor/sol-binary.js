var Solari = (function(parent) {
    // Submodules
    var Binary = parent.binary = parent.binary || {};

    // Private functions
    function arrayBufferToString(buffer) {
        var chunkSize = 32768;

        var array = new Uint8Array(buffer);

        //var charArray = [];
        var content = '';
        var len = array.byteLength;

        /*for (var i = 0; i < len; i++) {
            content += String.fromCharCode(array[i]);
        }*/

        for (var i = 0; i < len; i += chunkSize) {
            //charArray.push(String.fromCharCode.apply(null, array.subarray(i, i + chunkSize)));
            content += String.fromCharCode.apply(null, array.subarray(i, i + chunkSize));
        }

        //return charArray.join("");
        return content;
    }

    function bytesToWords(bytes) {
        var words = [];
        for (i = 0, b = 0; i < bytes.length; i++, b += 8) {
            words[b >>> 5] |= bytes[i] << (24 - b % 32);
        }
        return words;
    }

    function wordsToBytes(words) {
        var bytes = [];
        for (b = 0; b < words.length * 32; b += 8) {
            bytes.push((words[b >>> 5] >>> (24 - b % 32)) & 0xff);
        }
        return bytes;
    }

    function bytesToHex(bytes) {
        var hex = [];
        for (i = 0; i < bytes.length; i++) {
            var byte = bytes[i];
            hex.push((byte >>> 4).toString(16));
            hex.push((byte & 0xf).toString(16));
        }
        return hex.join("");
    }

    function rotateLeft(x, n) {
        return (x << n) | (x >>> (32 - n));
    }

    function endian32(value) {
        return rotateLeft(value, 8) & 0x00ff00ff
            | rotateLeft(value, 24) & 0xff00ff00;
    }

    // Public functions
    Binary.arrayBufferToString = arrayBufferToString;
    Binary.bytesToWords = bytesToWords;
    Binary.wordsToBytes = wordsToBytes;
    Binary.bytesToHex = bytesToHex;
    Binary.rotateLeft = rotateLeft;
    Binary.endian32 = endian32;

    return parent;
}(Solari || {}));
