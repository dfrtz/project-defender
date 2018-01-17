/**
 * @file A Project Defender - Manager app controller for camera management. This controller requires nesting under a
 * PdmCtrl controller.
 *
 * @author David Fritz
 * @version 0.1.0
 *
 * @copyright 2015-2017 David Fritz
 * @license MIT
 */
angular.module('projectDefenderManager').controller('PdmCameraCtrl', ['MainData', '$scope', '$http', '$timeout', '$q', '$mdColors', '$mdDialog', '$mdToast', PdmCameraCtrl]);

function PdmCameraCtrl(MainData, $scope, $http, $timeout, $q, $mdColors, $mdDialog, $mdToast) {
    var self = this;

    var TIMEOUT = 30 * 1000;

    self.activeCards = {
        main: true
    };
    self.cameraDataCurrent = {};
    self.loadingActivated = false;
    self.pendingLoad = null;
    self.cameras = [];
    self.selection = -1;
    self.page = 0;

    var loadingCanceler = $q.defer();

    /**
     * Initializes controller by executing first run operations.
     *
     * Must be called at end of assignments.
     */
    function init() {
        self.cameras = [
            {name: "local", path: "video"}
        ];
        // Load saved devices
        $http({
            url: 'api/1.0/cameras',
            dataType: 'json',
            method: 'GET',
            data: '',
            headers: {
                "Content-Type": "application/json"
            }
        }).success(function (response) {
            self.cameras.concat(response.cameras || []);
        });

        self.onCameraSelect(0);
    }

    /**
     * Retrieves camera name with optional formatted text.
     *
     * @param {number} index Position of Camera in cache.
     *
     * @returns String representing card name.
     */
    self.getCameraName = function (index) {
        var name = self.cameras[index];

        if (!name) {
            name = "Camera " + index;
        }

        return name;
    };

    /**
     * Updates internal tracking information based on actively selected Camera.
     *
     * @param {number} index Position of Camera in cache.
     */
    self.onCameraSelect = function (index) {
        if (index === self.selection) {
            return;
        }

        if (!self.cameras.length) {
            // No items remaining, clear form and hide
            self.selection = -1;
            self.cameraDataCurrent = {};
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
                $scope.simpleToast('Loading timeout: ' + self.cameras[index].name);
            }
        }, TIMEOUT);

        $http({
            url: 'api/1.0/camera/' + self.cameras[index],
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
            self.cameraDataCurrent = response || {};

            if (JSON.stringify(self.sentryDataCurrent) === JSON.stringify({})) {
                self.loadingFailed = true;
                $scope.simpleToast('Loading failed: ' + self.cameras[index].name);
            }
        });*/

        self.selection = index;
    };

    init();
}
