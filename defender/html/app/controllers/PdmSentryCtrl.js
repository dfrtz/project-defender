angular.module('projectDefenderManager').controller('PdmSentryCtrl', ['MainData', '$scope', '$http', '$timeout', '$q', '$mdColors', '$mdDialog', '$mdToast', PdSentryCtrl]);

function PdSentryCtrl(MainData, $scope, $http, $timeout, $q, $mdColors, $mdDialog, $mdToast) {
    var self = this;

    var TIMEOUT = 30 * 1000;

    self.activeCards = {
        main: true
    };

    self.sentryDataCurrent = {};

    var loadingCanceler = $q.defer();
    self.loadingActivated = false;
    self.pendingLoad = null;

    self.sentries = [];

    self.selection = -1;

    // Internal functions
    function init() {
        // Load Schemas
        $http({
            url: 'api/1.0/sentries',
            dataType: 'json',
            method: 'GET',
            data: '',
            headers: {
                "Content-Type": "application/json"
            }
        }).success(function(response) {
            self.sentries = response.sentries || [];
        });
    }

    self.getSentryName = function(index) {
        var sentry = self.sentries[index];
        var name = sentry;

        if (!name) {
            name = "Sentry " + index;
        }

        return name;
    };

    self.onSentrySelect = function(index) {
        if (!self.sentries.length) {
            // No items remaining, clear form and hide
            self.selection = -1;
            self.sentryDataCurrent = {};
            return;
        }

        if (index == -1) {
            index = 0;
        }

        loadingCanceler.resolve();
        loadingCanceler = $q.defer();

        self.loadingActivated = true;
        self.loadingFailed = false;

        $timeout.cancel(self.pendingLoad);
        self.pendingLoad = $timeout(function() {
            if (self.loadingActivated) {
                loadingCanceler.resolve();
                self.loadingActivated = false;
                self.loadingFailed = true;
                $scope.simpleToast('Loading timeout: ' + self.guests[index]);
            }
        }, TIMEOUT);

        $http({
            url: 'api/1.0/sentry/' + self.guests[index],
            dataType: 'json',
            method: 'GET',
            data: '',
            headers: {
                "Content-Type": "application/json"
            },
            timeout: loadingCanceler.promise
        }).success(function(response) {
            $timeout.cancel(self.pendingLoad);
            self.loadingActivated = false;
            self.guestDataCurrent = response || {};

            if (JSON.stringify(self.sentryDataCurrent) === JSON.stringify({})) {
                self.loadingFailed = true;
                $scope.simpleToast('Loading failed: ' + self.sentries[index]);
            }
        });

        self.selection = index;
    };

    // Add watchers to update UI

    // Add user event listeners

    // Action to perform on load
    init();
}

// Object Constructors
