/**
 * @file A Project Defender - Manager app controller for sentry (motorized device) management. This controller requires
 * nesting under a PdmCtrl controller.
 *
 * @author David Fritz
 * @version 0.1.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
angular.module('projectDefenderManager').controller('PdmSentryCtrl', ['MainData', '$scope', '$http', '$timeout', '$q', '$mdColors', '$mdDialog', '$mdToast', PdmSentryCtrl]);

function PdmSentryCtrl(MainData, $scope, $http, $timeout, $q, $mdColors, $mdDialog, $mdToast) {
    var self = this;

    var TIMEOUT = 30 * 1000;

    self.activeCards = {
        main: true
    };
    self.sentryDataCurrent = {};
    self.loadingActivated = false;
    self.pendingLoad = null;
    self.sentries = [];
    self.selection = -1;

    var loadingCanceler = $q.defer();

    /**
     * Initializes controller by executing first run operations.
     *
     * Must be called at end of assignments.
     */
    function init() {
        self.sentries = [
            {name: "local", path: "video"}
        ];
        // Load saved devices
        $http({
            url: 'api/1.0/sentries',
            dataType: 'json',
            method: 'GET',
            data: '',
            headers: {
                "Content-Type": "application/json"
            }
        }).success(function (response) {
            self.sentries.concat(response.sentries || []);
        });

        self.onSentrySelect(0);
    }

    /**
     * Retrieves sentry name with optional formatted text.
     *
     * @param {number} index Position of Sentry in cache.
     *
     * @returns String representing card name.
     */
    self.getSentryName = function (index) {
        var name = self.sentries[index].name;

        if (!name) {
            name = "Sentry " + index;
        }

        return name;
    };

    /**
     * Updates internal tracking information based on actively selected Sentry.
     *
     * @param {number} index Position of Sentry in cache.
     */
    self.onSentrySelect = function (index) {
        if (index === self.selection) {
            return;
        }

        if (!self.sentries.length) {
            // No items remaining, clear form and hide
            self.selection = -1;
            self.sentryDataCurrent = {};
            return;
        }

        if (index === -1) {
            index = 0;
        }

        /*loadingCanceler.resolve();
        loadingCanceler = $q.defer();

        self.loadingActivated = true;
        self.loadingFailed = false;

        $timeout.cancel(self.pendingLoad);
        self.pendingLoad = $timeout(function () {
            if (self.loadingActivated) {
                loadingCanceler.resolve();
                self.loadingActivated = false;
                self.loadingFailed = true;
                $scope.simpleToast('Loading timeout: ' + self.sentries[index]);
            }
        }, TIMEOUT);

        $http({
            url: 'api/1.0/sentry/' + self.sentries[index],
            dataType: 'json',
            method: 'GET',
            data: '',
            headers: {
                "Content-Type": "application/json"
            },
            timeout: loadingCanceler.promise
        }).success(function (response) {
            $timeout.cancel(self.pendingLoad);
            self.loadingActivated = false;
            self.guestDataCurrent = response || {};

            if (JSON.stringify(self.sentryDataCurrent) === JSON.stringify({})) {
                self.loadingFailed = true;
                $scope.simpleToast('Loading failed: ' + self.sentries[index]);
            }
        });*/

        self.selection = index;
    };

    init();
}

