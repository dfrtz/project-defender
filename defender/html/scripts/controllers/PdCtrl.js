angular.module('pdManager').factory('MainData', function() {
    //TODO Getters/Setters to restrict access
    this.data = {
        "value": ""
    };

    return this;
});

angular.module('pdManager').controller('PdCtrl', ['MainData', '$window', '$scope', '$mdColors', '$mdDialog', '$mdToast', '$mdSidenav', PdCtrl]);

function PdCtrl(MainData, $window, $scope, $mdColors, $mdDialog, $mdToast, $mdSidenav) {
    $scope.decorator = 'bootstrap-decorator';

    this.selections = {
        page: 0
    };

    this.pages = [
        {title: "Sentries", icon: 'home'},
        {title: "Cameras", icon: 'home'}
    ];

    // Internal functions
    function init() {
        // Load Schemas
        /*$http({
            url: 'data/schema-model-guildball.json',
            dataType: 'json',
            method: 'GET',
            data: '',
            headers: {
                "Content-Type": "application/json"
            }
        }).success(function(response) {
            MainData.schemaDataModel = response || {};
        });*/
    }

    this.onToggleDrawer = function(side) {
        $mdSidenav(side)
          .toggle()
          .then(function () {
          });
    };

    this.onLoadPage = function(page) {
        this.selections.page = page;
        this.onToggleDrawer('left');
    };

    // External functions
    $scope.onLoadLink = function(href) {
        $window.open(href);
    };

    $scope.listErrors = function(errors) {
        var messages = [];

        for (var key in errors) {
            for (var i = 0; i < errors[key].length; i++) {
                messages.push(errors[key][i].$name + ' is required.');
            }
        }

        console.log(errors);
        console.log(messages);
    };

    $scope.onClick = function(id) {
        document.getElementById(id).dispatchEvent(new MouseEvent('click'));
    };

    $scope.simpleToast = function(message) {
        var toast = $mdToast.simple()
            .textContent(message)
            .highlightAction(true)
            .highlightClass('md-accent')
            .position("bottom right")
            .hideDelay(3000);
        $mdToast.show(toast);
    };

    // Wrapper functions for DOM access
    $scope.getThemeColor = $mdColors.getThemeColor;

    $scope.range = function(n) {
        return Utils.range(n);
    };

    // Add watchers to update UI

    // Add user event listeners

    // Action to perform on load
    init();
}

// Object Constructors
