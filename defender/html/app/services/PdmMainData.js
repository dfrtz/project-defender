/**
 * @file Project Defender app factory containing shared objects between controllers.
 *
 * @author David Fritz
 * @version 1.0.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
angular.module("pdManager").factory("MainData", function () {
    /**
     * Initializes factory by executing first run operations.
     *
     * Must be called at end of assignments.
     */
    function init() {
        self.cpak.imageWorkerPool.cacheEnabled = true;
        self.xpak.imageWorkerPool.cacheEnabled = true;
    }

    init();

    return this;
});
