angular.module('projectDefenderManager').controller('PdmCtrl', ['MainData', '$window', '$scope', '$mdColors', '$mdDialog', '$mdToast', '$mdSidenav', PdCtrl]);

function PdCtrl(MainData, $window, $scope, $mdColors, $mdDialog, $mdToast, $mdSidenav) {
    var self = this;

    this.selections = {
        page: 0
    };
    this.pages = [
        {title: "Cameras", icon: 'home'}
        //{title: "Sentries", icon: 'home'}
    ];

    /**
     * Initializes controller by executing first run operations.
     *
     * Must be called at end of assignments.
     */
    function init() {
    }

    /**
     * Toggles navigation drawer and calls listening functions.
     *
     * @param {string} side Directional representation of the Drawer that was toggled. Left or Right.
     */
    this.onToggleDrawer = function (side) {
        $mdSidenav(side)
            .toggle()
            .then(function () {
            });
    };

    /**
     * Closes the navigation drawer and selects corresponding tab from shortcut list.
     *
     * @param {number} page Index of the selected page from shortcut menu.
     */
    self.onLoadPage = function (page) {
        self.onToggleDrawer("left");
        $scope.onSelectTab(page);
    };

    /**
     * Updates the selected tab for user navigation feedback.
     *
     * @param {number} page Index of the page to mark as selected.
     */
    $scope.onSelectTab = function (page) {
        page = page < 0 ? 0 : page > self.pages.length - 1 ? self.pages.length - 1 : page;
        self.selections.page = page;
    };

    /**
     * Opens a link in a new window/tab.
     *
     * @param {string} href Hypertext reference to a new web page.
     */
    $scope.onLoadLink = function (href) {
        $window.open(href);
    };

    /**
     * Dumps schema form errors to console.
     *
     * @param {Array} errors Array of angular schema form errors.
     */
    $scope.listErrors = function (errors) {
        var messages = [];

        for (var key in errors) {
            for (var i = 0; i < errors[key].length; i++) {
                messages.push(errors[key][i].$name + ' is required.');
            }
        }

        console.log(errors);
        console.log(messages);
    };

    /**
     * Simulates a mouse click on an HTML element by id.
     *
     * @param {string} id Unique identifier of an HTML element.
     */
    $scope.onClick = function (id) {
        document.getElementById(id).dispatchEvent(new MouseEvent('click'));
    };

    /**
     * Displays a quick information popup message on bottom right of the screen.
     *
     * @param {string} message Text to display.
     */
    $scope.simpleToast = function (message) {
        var toast = $mdToast.simple()
            .textContent(message)
            .highlightAction(true)
            .highlightClass('md-accent')
            .position("bottom right")
            .hideDelay(3000);
        $mdToast.show(toast);
    };

    // Expose methods to DOM
    $scope.getThemeColor = $mdColors.getThemeColor;
    $scope.range = function (n) {
        return Utils.range(n);
    };

    init();
}