/**
 * @file A library consisting of functions to perform low level data operations. Utilities which rely on converting low
 * level data types such as buffers, byte arrays, and words should be defined here.
 *
 * @summary Base library for low level binary and byte operations.
 *
 * @author David Fritz
 * @version 1.0.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
var Solari = (function (parent) {
    var Binary = parent.binary = parent.binary || {};

    /**
     * Converts a buffer of unsigned 8-bit integers into a string.
     *
     * @param {Array} buffer Array of unsigned 8-bit integers.
     * @returns {string} Text representation of unsigned 8-bit integers converted to character codes.
     */
    function arrayBufferToString(buffer) {
        var chunkSize = 32768;
        var array = new Uint8Array(buffer);
        var content = '';
        var len = array.byteLength;

        for (var i = 0; i < len; i += chunkSize) {
            content += String.fromCharCode.apply(null, array.subarray(i, i + chunkSize));
        }

        return content;
    }

    /**
     *  Converts 8-bit integers into 32-bit words.
     *
     * @param {Array} bytes Array of 8-bit integers.
     * @returns {Array} Array of 32-bit words.
     */
    function bytesToWords(bytes) {
        var words = [];
        for (var i = 0, b = 0; i < bytes.length; i++, b += 8) {
            words[b >>> 5] |= bytes[i] << (24 - b % 32);
        }
        return words;
    }

    /**
     * Converts 32-bit words into 8-bit integers.
     *
     * @param {Array}words Array of 32-bit words.
     * @returns {Array} Array of 8-bit integers.
     */
    function wordsToBytes(words) {
        var bytes = [];
        for (var b = 0; b < words.length * 32; b += 8) {
            bytes.push((words[b >>> 5] >>> (24 - b % 32)) & 0xff);
        }
        return bytes;
    }

    /**
     * Converts array of 8-bit values into 16-bit hexadecimal text.
     *
     * @param {Array} bytes Array of 8-bit integers.
     * @returns {string} Text representation of 16-bit values.
     */
    function bytesToHex(bytes) {
        var hex = [];
        for (var i = 0; i < bytes.length; i++) {
            var byte = bytes[i];
            hex.push((byte >>> 4).toString(16));
            hex.push((byte & 0xf).toString(16));
        }
        return hex.join("");
    }

    /**
     * Shifts binary representation of 32-bit value to the left.
     *
     * @param {number} value 32-bit value to perform bitwise operations on.
     * @param {number} amount How far to shift bits to the left.
     * @returns {number} Left shifted 32-bit integer
     */
    function rotateLeft(value, amount) {
        return (value << amount) | (value >>> (32 - amount));
    }

    /**
     * Swaps byte order of 32-bit value between little endian and big endian.
     *
     * @param {number} value 32-bit value to swap bit order
     * @returns {number} Value representing reversed bit order
     */
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
