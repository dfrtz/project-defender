/**
 * @file A library consisting of functions to perform cryptographic operations such as hashing. This library should
 * provide a synchronous and asynchronous version for all CPU intensive processes.
 *
 * @summary Base library for cryptographic operations.
 *
 * @author David Fritz
 * @version 1.0.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
var Solari = (function (parent) {
    // Submodules
    var Crypto = parent.crypto = parent.crypto || {};

    // Shortcuts
    var Binary = Solari.binary;
    var bytesToWords = Binary.bytesToWords;
    var wordsToBytes = Binary.wordsToBytes;
    var bytesToHex = Binary.bytesToHex;
    var rotateLeft = Binary.rotateLeft;
    var endian32 = Binary.endian32;

    /**
     * Auxiliary function for MD5 round 1 that takes three 32-bit words and produces one 32-bit word output.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @returns {number} 32-bit word
     */
    function F(x, y, z) {
        return (x & y | ~x & z);
    }

    /**
     * Auxiliary function for MD5 round 2 that takes three 32-bit words and produces one 32-bit word output.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @returns {number} 32-bit word
     */
    function G(x, y, z) {
        return (x & z | y & ~z);
    }

    /**
     * Auxiliary function for MD5 round 3 that takes three 32-bit words and produces one 32-bit word output.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @returns {number} 32-bit word
     */
    function H(x, y, z) {
        return (x ^ y ^ z);
    }

    /**
     * Auxiliary function for MD5 round 4 that takes three 32-bit words and produces one 32-bit word output.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @returns {number} 32-bit word
     */
    function I(x, y, z) {
        return y ^ (x | ~z);
    }

    /**
     * Auxiliary function for MD5 round 1 that takes 8 32-bit words and produces one left shifted 32-bit word.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} a
     * @param {number} b
     * @param {number} c
     * @param {number} d
     * @param {number} x
     * @param {number} s
     * @param {number} ac
     * @returns {number} 32-bit word
     */
    function FF(a, b, c, d, x, s, ac) {
        var n = a + F(b, c, d) + (x >>> 0) + ac;
        return rotateLeft(n, s) + b;
    }

    /**
     * Auxiliary function for MD5 round 2 that takes 8 32-bit words and produces one left shifted 32-bit word.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} a
     * @param {number} b
     * @param {number} c
     * @param {number} d
     * @param {number} x
     * @param {number} s
     * @param {number} ac
     * @returns {number} 32-bit word
     */
    function GG(a, b, c, d, x, s, ac) {
        var n = a + G(b, c, d) + (x >>> 0) + ac;
        return rotateLeft(n, s) + b;
    }

    /**
     * Auxiliary function for MD5 round 3 that takes 8 32-bit words and produces one left shifted 32-bit word.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} a
     * @param {number} b
     * @param {number} c
     * @param {number} d
     * @param {number} x
     * @param {number} s
     * @param {number} ac
     * @returns {number} 32-bit word
     */
    function HH(a, b, c, d, x, s, ac) {
        var n = a + H(b, c, d) + (x >>> 0) + ac;
        return rotateLeft(n, s) + b;
    }

    /**
     * Auxiliary function for MD5 round 4 that takes 8 32-bit words and produces one left shifted 32-bit word.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {number} a
     * @param {number} b
     * @param {number} c
     * @param {number} d
     * @param {number} x
     * @param {number} s
     * @param {number} ac
     * @returns {number} 32-bit word
     */
    function II(a, b, c, d, x, s, ac) {
        var n = a + I(b, c, d) + (x >>> 0) + ac;
        return rotateLeft(n, s) + b;
    }

    /**
     * Processes a byte array through MD5 hashing algorithm.
     *
     * This method is a Javascript translation of the C language MD5 hashing specification provided by:
     * https://www.ietf.org/rfc/rfc1321.txt
     *
     * MD5 is no longer considered secure, and should only used for operations where security is not a requirement.
     *
     * Derived from the RSA Data Security, Inc. MD5 Message-Digest Algorithm.
     *
     * @param {Array} bytes Array of 8-bit values which can be processed by MD5 hashing.
     * @returns {string} Text representation of MD5 byte hash
     */
    function md5(bytes) {
        // Constants for MD5 transform routine
        var S11 = 7;
        var S12 = 12;
        var S13 = 17;
        var S14 = 22;
        var S21 = 5;
        var S22 = 9;
        var S23 = 14;
        var S24 = 20;
        var S31 = 4;
        var S32 = 11;
        var S33 = 16;
        var S34 = 23;
        var S41 = 6;
        var S42 = 10;
        var S43 = 15;
        var S44 = 21;

        var words = bytesToWords(bytes);
        var wordLen = words.length;
        var byteLen = bytes.length * 8;

        // Convert endian
        for (var i = 0; i < wordLen; i++) {
            words[i] = endian32(words[i]);
        }

        // Pad bytes to meet md5 requirements
        words[byteLen >>> 5] |= 0x80 << (byteLen % 32);
        words[(((byteLen + 64) >>> 9) << 4) + 14] = byteLen;

        var a = 0x67452301;
        var b = 0xefcdab89;
        var c = 0x98badcfe;
        var d = 0x10325476;

        for (i = 0; i < wordLen; i += 16) {
            var AA = a;
            var BB = b;
            var CC = c;
            var DD = d;

            // Round 1
            a = FF(a, b, c, d, words[i], S11, 0xd76aa478);
            d = FF(d, a, b, c, words[i + 1], S12, 0xe8c7b756);
            c = FF(c, d, a, b, words[i + 2], S13, 0x242070db);
            b = FF(b, c, d, a, words[i + 3], S14, 0xc1bdceee);
            a = FF(a, b, c, d, words[i + 4], S11, 0xf57c0faf);
            d = FF(d, a, b, c, words[i + 5], S12, 0x4787c62a);
            c = FF(c, d, a, b, words[i + 6], S13, 0xa8304613);
            b = FF(b, c, d, a, words[i + 7], S14, 0xfd469501);
            a = FF(a, b, c, d, words[i + 8], S11, 0x698098d8);
            d = FF(d, a, b, c, words[i + 9], S12, 0x8b44f7af);
            c = FF(c, d, a, b, words[i + 10], S13, 0xffff5bb1);
            b = FF(b, c, d, a, words[i + 11], S14, 0x895cd7be);
            a = FF(a, b, c, d, words[i + 12], S11, 0x6b901122);
            d = FF(d, a, b, c, words[i + 13], S12, 0xfd987193);
            c = FF(c, d, a, b, words[i + 14], S13, 0xa679438e);
            b = FF(b, c, d, a, words[i + 15], S14, 0x49b40821);

            // Round 2
            a = GG(a, b, c, d, words[i + 1], S21, 0xf61e2562);
            d = GG(d, a, b, c, words[i + 6], S22, 0xc040b340);
            c = GG(c, d, a, b, words[i + 11], S23, 0x265e5a51);
            b = GG(b, c, d, a, words[i], S24, 0xe9b6c7aa);
            a = GG(a, b, c, d, words[i + 5], S21, 0xd62f105d);
            d = GG(d, a, b, c, words[i + 10], S22, 0x02441453);
            c = GG(c, d, a, b, words[i + 15], S23, 0xd8a1e681);
            b = GG(b, c, d, a, words[i + 4], S24, 0xe7d3fbc8);
            a = GG(a, b, c, d, words[i + 9], S21, 0x21e1cde6);
            d = GG(d, a, b, c, words[i + 14], S22, 0xc33707d6);
            c = GG(c, d, a, b, words[i + 3], S23, 0xf4d50d87);
            b = GG(b, c, d, a, words[i + 8], S24, 0x455a14ed);
            a = GG(a, b, c, d, words[i + 13], S21, 0xa9e3e905);
            d = GG(d, a, b, c, words[i + 2], S22, 0xfcefa3f8);
            c = GG(c, d, a, b, words[i + 7], S23, 0x676f02d9);
            b = GG(b, c, d, a, words[i + 12], S24, 0x8d2a4c8a);

            // Round 3
            a = HH(a, b, c, d, words[i + 5], S31, 0xfffa3942);
            d = HH(d, a, b, c, words[i + 8], S32, 0x8771f681);
            c = HH(c, d, a, b, words[i + 11], S33, 0x6d9d6122);
            b = HH(b, c, d, a, words[i + 14], S34, 0xfde5380c);
            a = HH(a, b, c, d, words[i + 1], S31, 0xa4beea44);
            d = HH(d, a, b, c, words[i + 4], S32, 0x4bdecfa9);
            c = HH(c, d, a, b, words[i + 7], S33, 0xf6bb4b60);
            b = HH(b, c, d, a, words[i + 10], S34, 0xbebfbc70);
            a = HH(a, b, c, d, words[i + 13], S31, 0x289b7ec6);
            d = HH(d, a, b, c, words[i], S32, 0xeaa127fa);
            c = HH(c, d, a, b, words[i + 3], S33, 0xd4ef3085);
            b = HH(b, c, d, a, words[i + 6], S34, 0x04881d05);
            a = HH(a, b, c, d, words[i + 9], S31, 0xd9d4d039);
            d = HH(d, a, b, c, words[i + 12], S32, 0xe6db99e5);
            c = HH(c, d, a, b, words[i + 15], S33, 0x1fa27cf8);
            b = HH(b, c, d, a, words[i + 2], S34, 0xc4ac5665);

            // Round 4
            a = II(a, b, c, d, words[i], S41, 0xf4292244);
            d = II(d, a, b, c, words[i + 7], S42, 0x432aff97);
            c = II(c, d, a, b, words[i + 14], S43, 0xab9423a7);
            b = II(b, c, d, a, words[i + 5], S44, 0xfc93a039);
            a = II(a, b, c, d, words[i + 12], S41, 0x655b59c3);
            d = II(d, a, b, c, words[i + 3], S42, 0x8f0ccc92);
            c = II(c, d, a, b, words[i + 10], S43, 0xffeff47d);
            b = II(b, c, d, a, words[i + 1], S44, 0x85845dd1);
            a = II(a, b, c, d, words[i + 8], S41, 0x6fa87e4f);
            d = II(d, a, b, c, words[i + 15], S42, 0xfe2ce6e0);
            c = II(c, d, a, b, words[i + 6], S43, 0xa3014314);
            b = II(b, c, d, a, words[i + 13], S44, 0x4e0811a1);
            a = II(a, b, c, d, words[i + 4], S41, 0xf7537e82);
            d = II(d, a, b, c, words[i + 11], S42, 0xbd3af235);
            c = II(c, d, a, b, words[i + 2], S43, 0x2ad7d2bb);
            b = II(b, c, d, a, words[i + 9], S44, 0xeb86d391);

            a = (a + AA) >>> 0;
            b = (b + BB) >>> 0;
            c = (c + CC) >>> 0;
            d = (d + DD) >>> 0;
        }

        return bytesToHex(
            wordsToBytes([
                endian32(a),
                endian32(b),
                endian32(c),
                endian32(d)
            ])
        );
    }

    /**
     * MD5 hashes 8-bit data set asynchronously using Workers.
     *
     * Note: New worker option currently has no limit to amount of workers spawned. Future version will use a pool; use
     * with caution.
     *
     * @param {Array} data Array or buffer like object containing 8-bit values.
     * @param {function} onFinish Callback operation to return checksum.
     * @param {boolean|undefined} newWorker Spawn new worker for each request, or add to existing worker's queue.
     */
    function md5Async(data, onFinish, newWorker) {
        if (newWorker === null || newWorker === undefined || !newWorker) {
            // Use existing worker to process offscreen sequentially
            md5Worker.onmessage = onFinish;
            md5Worker.postMessage(data);
        } else {
            // Create new worker for each call, maximum parallelization
            Solari.utils.async(data, md5AsyncObjectUrl, onFinish);
        }
    }

    // Private variables
    var md5AsyncObjectUrl = URL.createObjectURL(Solari.utils.buildAsyncBlob(
        function (event) {
            var path = event.data.path || '';
            var data = event.data.data || event.data;

            // The 'self' reference is not expected to resolve during declaration. It will be used within a worker.
            self.postMessage({path: path, checksum: md5(data)});
        }, md5, bytesToWords, wordsToBytes, bytesToHex, rotateLeft, endian32, F, FF, G, GG, H, HH, I, II)
    );
    //TODO convert worker to WorkerPool
    var md5Worker = new Worker(md5AsyncObjectUrl);

    // Public functions
    Crypto.md5 = md5;
    Crypto.md5Async = md5Async;

    return parent;
}(Solari || {}));
