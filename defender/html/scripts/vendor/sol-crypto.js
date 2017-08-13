var Solari = (function(parent) {
    // Submodules
    var Crypto = parent.crypto = parent.crypto || {};

    // Shortcuts
    var Binary = Solari.binary;
    var arrayBufferToString = Binary.arrayBufferToString;
    var bytesToWords = Binary.bytesToWords;
    var wordsToBytes = Binary.wordsToBytes;
    var bytesToHex = Binary.bytesToHex;
    var rotateLeft = Binary.rotateLeft;
    var endian32 = Binary.endian32;

    // Private functions
    function md5(byteArray) {
        // https://www.ietf.org/rfc/rfc1321.txt

        var F = function(x, y, z) {
            return (x & y | ~x & z);
        };
        var G = function(x, y, z) {
            return (x & z | y & ~z);
        };
        var H = function(x, y, z) {
            return (x ^ y ^ z);
        };
        var I = function(x, y, z) {
            return y ^ (x | ~z);
        };

        var FF = function(a, b, c, d, x, s, ac) {
            var n = a + F(b, c, d) + (x >>> 0) + ac;
            return rotateLeft(n, s) + b;
        };
        var GG = function(a, b, c, d, x, s, ac) {
            var n = a + G (b, c, d) + (x >>> 0) + ac;
            return rotateLeft(n, s) + b;
        };
        var HH  = function(a, b, c, d, x, s, ac) {
            var n = a + H(b, c, d) + (x >>> 0) + ac;
            return rotateLeft(n, s) + b;
        };
        var II  = function(a, b, c, d, x, s, ac) {
            var n = a + I(b, c, d) + (x >>> 0) + ac;
            return rotateLeft(n, s) + b;
        };

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

    	var words = bytesToWords(byteArray);
        var wordLen = words.length;
    	var byteLen = byteArray.length * 8;

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

    		a = FF(a, b, c, d, words[i + 0], S11, 0xd76aa478);
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

    		a = GG(a, b, c, d, words[i + 1], S21, 0xf61e2562);
    		d = GG(d, a, b, c, words[i + 6], S22, 0xc040b340);
    		c = GG(c, d, a, b, words[i + 11], S23, 0x265e5a51);
    		b = GG(b, c, d, a, words[i + 0], S24, 0xe9b6c7aa);
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

    		a = HH(a, b, c, d, words[i + 5], S31, 0xfffa3942);
    		d = HH(d, a, b, c, words[i + 8], S32, 0x8771f681);
    		c = HH(c, d, a, b, words[i + 11], S33, 0x6d9d6122);
    		b = HH(b, c, d, a, words[i + 14], S34, 0xfde5380c);
    		a = HH(a, b, c, d, words[i + 1], S31, 0xa4beea44);
    		d = HH(d, a, b, c, words[i + 4], S32, 0x4bdecfa9);
    		c = HH(c, d, a, b, words[i + 7], S33, 0xf6bb4b60);
    		b = HH(b, c, d, a, words[i + 10], S34, 0xbebfbc70);
    		a = HH(a, b, c, d, words[i + 13], S31, 0x289b7ec6);
    		d = HH(d, a, b, c, words[i + 0], S32, 0xeaa127fa);
    		c = HH(c, d, a, b, words[i + 3], S33, 0xd4ef3085);
    		b = HH(b, c, d, a, words[i + 6], S34, 0x04881d05);
    		a = HH(a, b, c, d, words[i + 9], S31, 0xd9d4d039);
    		d = HH(d, a, b, c, words[i + 12], S32, 0xe6db99e5);
    		c = HH(c, d, a, b, words[i + 15], S33, 0x1fa27cf8);
    		b = HH(b, c, d, a, words[i + 2], S34, 0xc4ac5665);

    		a = II(a, b, c, d, words[i + 0], S41, 0xf4292244);
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
        function(event) {
            var path = event.data.path || '';
            var data = event.data.data || event.data;

            self.postMessage({path: path, checksum: md5(data)});
        }, md5, bytesToWords, wordsToBytes, bytesToHex, rotateLeft, endian32)
    );
    //TODO convert worker to WorkerPool
    var md5Worker = new Worker(md5AsyncObjectUrl);

    // Public functions
    Crypto.md5 = md5;
    Crypto.md5Async = md5Async;

    return parent;
}(Solari || {}));
